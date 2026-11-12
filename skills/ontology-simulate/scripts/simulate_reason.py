#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""simulate_reason.py —— what-if 物化推理执行器（ontology-simulate 的执行内核）。

技术路线（实测定案，验证明细见本 skill CHANGELOG.md A 节）：
  双快照 diff   ：load(base+case) 断言快照 → Pellet sync → 全量快照 → 差集=推断层
  逐规则启停归因：drop_rule 删一条 swrl:Imp → 再物化 → diff 消失的行=该规则贡献
  TBox 边界    ：类级推断回收不完整（实测结论），实例级可靠——本工具消费
                  面为实例级 what-if，类级语义由 TTL 断言直读承接（设计边界非缺陷）

沙箱纪律：模拟实例只进内存临时文件，物化结果写独立输出——**零回写**本体/黄金集。

输入实例 JSON 契约（编译 agent 产出，check_instance 先行机械校验）：
  {"scenario", "individuals":[{name, classes[], facts{}}], "relations":[{prop,from,to}], "query"}

用法：
  python3 simulate_reason.py --instance demo1-instance.json \
      --ttl ontology.ttl [--signature signature.json] \
      [--attribution rules|none] [--json-output result.json] [--cache-dir DIR] \
      [--render-md result.md]

--render-md：把物化结果经 label_map 确定性渲染为业务语言 md（不过 LLM）——
  A/B 本体臂注入材料的可读层（应答契约 v1.1），亦可供业务专家直读；
  深度解读仍走 interpreter agent。

exit 0 一致且推理完成；exit 1 校验/推理失败；exit 2 参数错。
"""
import argparse
import json
import os
import sys
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(_HERE, "../../ontology-model/scripts"),
           os.path.join(_HERE, "../../ontology-review/scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from rdflib import RDF, BNode  # noqa: E402
from rdflib.namespace import Namespace  # noqa: E402
import owlready2  # noqa: E402

from run_golden_cases import (  # noqa: E402
    canonicalize_base, _prefix_header, find_java)
from review_extract import file_sha  # noqa: E402
from check_instance import check_instance  # noqa: E402

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")

# 归因自动降级阈值：规则数超过即默认关逐规则归因（N+1 次 Pellet 成本）
ATTRIBUTION_RULE_LIMIT = 12

# 字面量类型 → turtle 语法（具名 datatype 一律 plain string：facet 由 L2 承接，限制⑩对偶）
LITERAL_FORMS = {
    "integer": lambda v: str(int(v)),
    "decimal": lambda v: '"%s"^^<http://www.w3.org/2001/XMLSchema#decimal>' % v,
    "double": lambda v: '"%s"^^<http://www.w3.org/2001/XMLSchema#double>' % v,
    "boolean": lambda v: "true" if v else "false",
    "date": lambda v: '"%s"^^<http://www.w3.org/2001/XMLSchema#date>' % v,
    "dateTime": lambda v: '"%s"^^<http://www.w3.org/2001/XMLSchema#dateTime>' % v,
    "string": lambda v: json.dumps(str(v), ensure_ascii=False),
}


# ---------------------------------------------------------------- 实例编译

def compile_instance_ttl(inst, sig, prefix_header_text):
    """实例 JSON → Turtle 片段（机械映射：name→:name，facts/relations 逐条）。"""
    base_iri = None
    for c in sig["classes"]:
        iri, cid = c.get("iri", ""), c.get("id", "")
        if iri and cid and cid in iri and iri.endswith(cid):
            base_iri = iri[: -len(cid)]
            break
    if not base_iri:
        # 回退：从 prefix 头解析 @prefix : <iri>
        for line in prefix_header_text.splitlines():
            if line.startswith("@prefix :"):
                base_iri = line.split("<")[1].split(">")[0]
                break
    if not base_iri:
        raise ValueError("无法确定 base namespace（TTL 无 @prefix : 声明）")

    dp_by_id = {p["id"]: p for p in sig["data_properties"]}

    lines = ["# ==== what-if 模拟实例（虚构画像，编译自 instance JSON） ===="]
    for ind in inst.get("individuals", []):
        name = ind["name"]
        parts = []
        for cid in ind.get("classes", []):
            parts.append("a <%s%s>" % (base_iri, cid))
        for key, val in (ind.get("facts") or {}).items():
            rng = (dp_by_id.get(key) or {}).get("range") or "string"
            if isinstance(val, bool):
                lit = "true" if val else "false"
            elif isinstance(val, (int, float)):
                # 数值编码为数值字面量（swrlb 数值比较可用；具名 datatype
                # 的 facet 约束本就由 L2 承接——限制⑩对偶，模拟侧不做）。
                # float 必须用引号词法形态 "0.7"^^xsd:decimal——数值短记法
                # 带 ^^ 非法 Turtle（2026-11-09 真实载体 A/B run 首现修复；
                # 引号形态与短记法 RDF term 等价）
                lit = str(val) if isinstance(val, int) else (
                    '"%s"^^<http://www.w3.org/2001/XMLSchema#decimal>' % val)
            else:
                lit = LITERAL_FORMS.get(rng, LITERAL_FORMS["string"])(val)
            parts.append("<%s%s> %s" % (base_iri, key, lit))
        lines.append(":%s %s ." % (name, " ;\n    ".join(parts)) if parts
                     else ":%s a <%sThing> ." % (name, base_iri))
    for rel in inst.get("relations", []):
        lines.append(":%s <%s%s> :%s ." % (
            rel["from"], base_iri, rel["prop"], rel["to"]))
    return "\n".join(lines) + "\n"


def nt_lines(g):
    return set(l for l in g.serialize(format="nt").splitlines() if l.strip())


def world_graph_snapshot(world):
    return nt_lines(world.as_rdflib_graph())


def load_world(base_nt, case_nt):
    fd, tmp = tempfile.mkstemp(suffix=".nt")
    os.close(fd)
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(base_nt)
        fh.write(case_nt)
    world = owlready2.World()
    world.get_ontology(tmp).load()
    return world, tmp


def sync_pellet(world, java):
    """Pellet 物化；不一致时抛异常（调用方捕获转报告）。"""
    owlready2.JAVA_EXE = java
    onto = list(world.ontologies.values())[0]
    with onto:
        owlready2.sync_reasoner_pellet(
            world, infer_property_values=True, infer_data_property_values=True)
    return onto


def materialize(base_nt, case_nt, java, tag):
    """双快照 diff（实测定案的技术路线）。不一致时返回 inconsistent 标记。"""
    t0 = time.time()
    world, tmp = load_world(base_nt, case_nt)
    snap_assert = world_graph_snapshot(world)
    t_load = time.time() - t0
    inconsistent = None
    t1 = time.time()
    try:
        sync_pellet(world, java)
    except Exception as exc:  # OwlReadyInconsistentOntologyError 等
        inconsistent = str(exc)[:500]
    t_sync = time.time() - t1
    snap_after = world_graph_snapshot(world)
    os.unlink(tmp)
    diff = sorted(snap_after - snap_assert)
    retract = sorted(snap_assert - snap_after)
    return {
        "tag": tag,
        "asserted": len(snap_assert),
        "after": len(snap_after),
        "diff_inferred": len(diff),
        "retracted": len(retract),
        "bnode_subject": sum(1 for l in diff if l.startswith("_:")),
        "inconsistent": inconsistent,
        "t_load": round(t_load, 1),
        "t_sync": round(t_sync, 1),
        "_diff_set": diff,
    }


def _destroy_list(g, node):
    """递归销毁 rdf:List 节点链（含 first 指向的 bnode atom 本体三元组）。"""
    while node is not None and isinstance(node, BNode):
        first = g.value(node, RDF.first)
        rest = g.value(node, RDF.rest)
        if first is not None and isinstance(first, BNode):
            for t in list(g.triples((first, None, None))):
                g.remove(t)
            for t in list(g.triples((None, None, first))):
                g.remove(t)
        for t in list(g.triples((node, None, None))):
            g.remove(t)
        node = rest if isinstance(rest, BNode) else None


def drop_rule(nt_text, rule_local):
    """删除一条 swrl:Imp（具名实体+body/head bnode 链级联+孤儿变量）——实测定案。"""
    import rdflib
    g = rdflib.Graph()
    g.parse(data=nt_text, format="nt")
    for imp in list(g.subjects(RDF.type, SWRL.Imp)):
        if rule_local not in str(imp):
            continue
        for pred in (SWRL.body, SWRL.head):
            lst = g.value(imp, pred)
            if lst is not None:
                _destroy_list(g, lst)
                g.remove((imp, pred, lst))
        for t in list(g.triples((imp, None, None))):
            g.remove(t)
    for var in list(g.subjects(RDF.type, SWRL.Variable)):
        if sum(1 for _ in g.triples((None, None, var))) == 0:
            for t in list(g.triples((var, None, None))):
                g.remove(t)
    return g.serialize(format="nt")


def list_rules(nt_text):
    """NT 文本中的 swrl:Imp localname 列表。"""
    import rdflib
    g = rdflib.Graph()
    g.parse(data=nt_text, format="nt")

    def local(n):
        s = str(n)
        for sep in ("#", "/"):
            if sep in s:
                s = s.rsplit(sep, 1)[1]
        return s
    return sorted(local(imp) for imp in g.subjects(RDF.type, SWRL.Imp))


def canonical_with_cache(ttl_path, cache_dir):
    """canonicalize_base 带缓存（大规模本体 ~60s 的一次性成本摊销）。键=TTL sha12。"""
    sha = file_sha(ttl_path)
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "%s.nt" % sha)
    if os.path.exists(cache_file):
        with open(cache_file, encoding="utf-8") as fh:
            return fh.read(), sha, True
    with open(ttl_path, encoding="utf-8") as fh:
        text = fh.read()
    nt, _ = canonicalize_base(text)
    with open(cache_file, "w", encoding="utf-8") as fh:
        fh.write(nt)
    return nt, sha, False


def localname(term):
    """NT 项（<IRI> / _:b / 字面量）→ localname（剥尖括号后按 #/ 切）。"""
    s = str(term).strip().strip("<>")
    for sep in ("#", "/"):
        if sep in s:
            s = s.rsplit(sep, 1)[1]
    return s


def humanize_diff(diff_lines, individual_names):
    """NT 行 → {triple, instance_level, attribution} 骨架（attribution 后填）。"""
    out = []
    for line in diff_lines:
        s, p, o = line.rstrip(" .\n").split(" ", 2)
        subj, pred, obj = localname(s), localname(p), localname(o)
        inst_level = subj in individual_names or obj in individual_names
        out.append({
            "subject": subj,
            "predicate": pred,
            "object": localname(o) if o.strip().startswith("<")
                      else o.strip().split("^^")[0].rsplit('"@', 1)[0].strip('"'),
            # 字面量词法提取：先切 ^^datatype 再切 " @lang 尾，最后去引号
            # （2026-11-09 A/B run 修复：原顺序 strip('"') 在 split 前，
            # 带 datatype 的字面量尾引号剥不掉——"不可准入"^^… → 不可准入"）
            "raw": line.strip()[:200],
            "instance_level": inst_level,
            "attribution": [],
        })
    return out


def render_md(result):
    """sim-result → 业务语言 md（确定性模板渲染，不过 LLM）。

    设计（A/B 报告 §4 改进项）：本体臂材料注入原始 JSON 会暴露规则 ID/物化
    记法，损伤应答可读性——本渲染层把推断三元组翻成 label 语言，结构记法
    只保留在「依据」括注里，供应答者引用溯源。
    """
    lm = result.get("label_map") or {}

    def name(key):
        """localname → 业务名（label 优先，缺失保留原名）。"""
        return lm.get(key) or key

    lines = [
        "# what-if 物化结果（业务语言版）",
        "",
        "> 本页由 simulate_reason.py `--render-md` 确定性渲染（label_map 模板，非 LLM 生成）。",
        "> 开放世界语义提示：**未推出 ≠ 否定**——未出现在下表的判定为「未判定」，不得解读为不成立。",
        "",
    ]
    if result.get("scenario"):
        lines.append("- 场景：%s" % result["scenario"])
    if result.get("query"):
        lines.append("- 业务问题：%s" % result["query"])
    lines.append("- 一致性：%s" % ("一致" if result["consistency"] == "consistent"
                                  else "**不一致**（%s）" % (result.get("inconsistency_detail") or "见 JSON")))
    mat = result.get("materialize") or {}
    lines.append("- 推断新增 %s 条（回撤 %s 条，预期 0）；归因模式：%s"
                 % (mat.get("diff_inferred", "?"), mat.get("retracted", "?"),
                    result.get("attribution_mode", "?")))
    lines += ["", "## 系统判定与推断事实", ""]
    inferred = result.get("inferred") or []
    if not inferred:
        lines.append("（本次物化无新增推断——所有问题相关判定均为「未判定」，开放世界口径。）")
    else:
        lines.append("| # | 主体 | 判定/关系 | 取值/客体 | 依据 | 层级 |")
        lines.append("|---|---|---|---|---|---|")
        for i, h in enumerate(inferred, 1):
            subj = name(h["subject"])
            pred, obj = h["predicate"], h["object"]
            if pred == "type":
                rel, val = "被判定为", name(obj)
            elif pred in lm or obj in lm:
                rel, val = "『%s』" % name(pred), name(obj)
            else:
                rel, val = "『%s』" % name(pred), "「%s」" % obj
            attr = h.get("attribution") or []
            basis = "、".join("%s（%s）" % (name(a), a) if a in lm and lm[a]
                              else a for a in attr) or "—"
            level = "实例级" if h.get("instance_level") else "类级/schema"
            lines.append("| %d | %s | %s | %s | %s | %s |"
                         % (i, subj, rel, val, basis, level))
    lines += ["", "## 依据规则对照", ""]
    rules = [r for r in (result.get("attribution_summary") or {})]
    if rules:
        for r in sorted(rules):
            lines.append("- %s：%s（贡献推断 %d 条）"
                         % (name(r), r, result["attribution_summary"][r]))
    else:
        lines.append("- 逐规则归因未开启（%s）——依据溯源见 JSON `attribution` 字段。"
                    % result.get("attribution_mode", "none"))
    lines += ["", "> 深度业务解读（推理链叙述/存疑项处置建议）由 ontology-whatif-interpreter 承接；本页仅为机械渲染层。", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--ttl", required=True)
    ap.add_argument("--signature", default=None)
    ap.add_argument("--attribution", choices=["rules", "none"], default="rules")
    ap.add_argument("--json-output", default=None)
    ap.add_argument("--render-md", default=None,
                    help="业务语言 md 渲染输出（确定性模板，A/B 本体臂材料可读层）")
    ap.add_argument("--cache-dir", default=None)
    args = ap.parse_args()

    for path, code in ((args.instance, "--instance"), (args.ttl, "--ttl")):
        if not os.path.exists(path):
            sys.exit("exit 2: %s 不存在：%s" % (code, path))
    with open(args.instance, encoding="utf-8") as fh:
        inst = json.load(fh)

    # ---- signature（缺则现场提取）
    if args.signature and os.path.exists(args.signature):
        with open(args.signature, encoding="utf-8") as fh:
            sig = json.load(fh)
    else:
        from extract_signature import build_signature
        sig = build_signature(args.ttl)
        if sig is None:
            sys.exit("exit 1: TTL 无法提取签名")

    # ---- 机械校验（SG1 机器侧：拦臆造）
    errors, warnings = check_instance(inst, sig)
    if errors:
        print("实例校验不通过（error %d）——先修编译产出：" % len(errors))
        for v in errors:
            print("  [error %s] %s" % (v["code"], v["message"]))
        sys.exit(1)

    java = find_java()
    notes = list(warnings)

    # ---- canonical（缓存）
    cache_dir = args.cache_dir or os.path.join(
        os.path.dirname(os.path.abspath(args.instance)), ".sim-cache")
    t0 = time.time()
    base_nt, sha, cached = canonical_with_cache(args.ttl, cache_dir)
    t_canon = round(time.time() - t0, 1)
    rules = list_rules(base_nt)
    if cached:
        notes.append("canonicalize 缓存命中（sha=%s）" % sha)

    # ---- 归因自动降级（大本体）
    do_attr = args.attribution == "rules"
    if do_attr and len(rules) > ATTRIBUTION_RULE_LIMIT:
        do_attr = False
        notes.append("规则数 %d > %d，逐规则归因自动降级（--attribution rules 可强制）"
                     % (len(rules), ATTRIBUTION_RULE_LIMIT))

    # ---- 实例编译 + 全量物化
    with open(args.ttl, encoding="utf-8") as fh:
        base_text = fh.read()
    case_ttl = compile_instance_ttl(inst, sig, _prefix_header(base_text))
    # Turtle → NT（probe case_nt_of 同款：rdflib 解析再序列化，owlready2 只吃 NT）
    import rdflib
    cg = rdflib.Graph()
    cg.parse(data=_prefix_header(base_text) + "\n" + case_ttl, format="turtle")
    case_nt = cg.serialize(format="nt")
    full = materialize(base_nt, case_nt, java, "full")
    if full["inconsistent"]:
        print("⚠ 本体+实例不一致（矛盾画像被推理器检出）：%s" % full["inconsistent"])

    # ---- 归因（逐规则启停；line→贡献规则映射 + 汇总）
    attr_summary, line_attr = {}, {}
    if do_attr and full["diff_inferred"]:
        # 无规则基线（schema 传播层）
        norules_nt = base_nt
        for r in rules:
            norules_nt = drop_rule(norules_nt, r)
        e_norules = materialize(norules_nt, case_nt, java, "norules")
        norules_diff = set(e_norules["_diff_set"])

        per_rule_gain = {}
        for r in rules:
            e_r = materialize(drop_rule(base_nt, r), case_nt, java, "no_" + r)
            per_rule_gain[r] = set(full["_diff_set"]) - set(e_r["_diff_set"])
            e_r.pop("_diff_set")

        for line in full["_diff_set"]:
            if line in norules_diff:
                line_attr[line] = ["schema_propagation"]
            else:
                contributors = [r for r in rules if line in per_rule_gain[r]]
                line_attr[line] = contributors or ["multi_rule_joint"]
            for r in line_attr[line]:
                attr_summary[r] = attr_summary.get(r, 0) + 1

    # ---- label 映射（interpreter 消费）
    label_map = {c["id"]: c.get("label", "") for c in sig["classes"]}
    label_map.update({p["id"]: p.get("label", "") for p in sig["object_properties"]})
    label_map.update({p["id"]: p.get("label", "") for p in sig["data_properties"]})
    for r in sig["rules"]:
        label_map[r["id"]] = r.get("label", "")

    # ---- 结果
    full_set_lines = full.pop("_diff_set")
    result = {
        "instance": os.path.basename(args.instance),
        "scenario": inst.get("scenario", ""),
        "query": inst.get("query", ""),
        "ontology": {"ttl": args.ttl, "sha": sha},
        "consistency": "inconsistent" if full["inconsistent"] else "consistent",
        "inconsistency_detail": full["inconsistent"],
        "materialize": full,
        "inferred": [
            dict(h, attribution=line_attr.get(line, []))
            for line, h in zip(full_set_lines, humanize_diff(
                full_set_lines, {i["name"] for i in inst.get("individuals", [])}))
        ],
        "attribution_summary": attr_summary if do_attr else None,
        "attribution_mode": "rules" if do_attr else ("auto-degraded" if
                             args.attribution == "rules" and not do_attr else "none"),
        "rules_total": len(rules),
        "label_map": label_map,
        "notes": notes,
        "cache": {"dir": cache_dir, "hit": cached, "t_canonical": t_canon},
    }

    out = args.json_output or os.path.join(
        os.path.dirname(os.path.abspath(args.instance)), "sim-result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    if args.render_md:
        with open(args.render_md, "w", encoding="utf-8") as fh:
            fh.write(render_md(result))

    print("=" * 60)
    print("what-if 物化完成 →", out)
    if args.render_md:
        print("业务语言渲染 →", args.render_md)
    print("一致性：%s ｜ 推断 %d 条（其中实例级 %d）｜ 回撤 %d（预期 0）" % (
        result["consistency"], full["diff_inferred"],
        sum(1 for h in result["inferred"] if h["instance_level"]),
        full["retracted"]))
    if do_attr:
        print("归因分布：", json.dumps(attr_summary, ensure_ascii=False))
    for h in result["inferred"]:
        if h["instance_level"]:
            print("  ▸ %s --%s--> %s %s" % (
                h["subject"], h["predicate"], h["object"],
                ("〔%s〕" % "+".join(h["attribution"])) if h["attribution"] else ""))
    sys.exit(0 if result["consistency"] == "consistent" else 1)


if __name__ == "__main__":
    main()
