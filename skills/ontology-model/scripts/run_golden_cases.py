#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6 黄金用例执行器（用例外置 JSON，schema 1.0）。

机制：基底本体（模式层，individuals=0）+ 每用例追加虚构个体断言（用例外置 JSON）
→ 合并 Turtle → rdflib 转 RDF/XML → owlready2 加载 → Pellet realize（全量档，
含 SWRL）→ 按断言表判定 → JSON 结果。

**实例级推理执行纪律（限制⑩，内置默认开启）**：用例个体断言字面量后，facet 类
具名 datatype（onDatatype+withRestrictions）触发 Pellet 值空间判空 → 假不一致；
加载前剥离具名 datatype 声明与 range 引用（内联匿名 oneOf 保留——实例层有真
强制力）。--no-strip 仅调试用。

**用例外置接口（专家黄金集输入形式化）**：用例不再内嵌脚本，而为 JSON 文件
（schema_version 1.0）：meta（scenario/source/notes）+ cases[]（id/kind/seed/
gen/desc/ttl/expect，exempt 条目登记不执行）。kind 枚举：expert_seed（专家
种子，首选路径——业务专家直接提供三元组）/ ai_edge / ai_negative / ai_stress。
用例 ttl 片段复用本体文件的 prefix 声明（以 : 前缀书写个体断言）。
expect 断言类型枚举：
  ["consistent"] / ["inconsistent"]
  ["in_class", ind, cls] / ["not_in_class", ind, cls]
  ["prop_value", s, prop, o] / ["no_prop_value", s, prop, o]

环境路径复用 check_consistency.py 已验证做法（reasoner-limits §一/§二）：
owlready2.JAVA_EXE 显式设置；rdflib 中转（owlready2 原生不认 Turtle）；
OwlReadyInconsistentOntologyError 三用途分派（空消息/含 "Ontology is
inconsistent" = 阳性检出；其他 Java error = 运行失败）。

用法：
  python3 run_golden_cases.py ONTOLOGY.ttl CASES.json [--only ID ...]
                              [--json-output FILE] [--check] [--no-strip]
  --check：仅 schema 校验（不跑 reasoner），exit 0/1——可入单测
"""
import argparse
import json
import os
import re
import sys
import tempfile

SCHEMA_VERSION = "1.0"
ASSERT_ARITY = {
    "consistent": 1, "inconsistent": 1,
    "in_class": 3, "not_in_class": 3,
    "prop_value": 4, "no_prop_value": 4,
}
KIND_ENUM = ("expert_seed", "ai_edge", "ai_negative", "ai_stress")

# ---------------------------------------------------------------- find_java
def find_java():
    candidates = [os.environ.get("OWL_JAVA_EXE")]
    home = os.path.expanduser("~")
    jvm_dir = os.path.join(home, "Library/Java/JavaVirtualMachines")
    if os.path.isdir(jvm_dir):
        vers = []
        for name in os.listdir(jvm_dir):
            m = re.match(r"jdk-(\d+)", name)
            if m:
                vers.append((int(m.group(1)), name))
        for _, name in sorted(vers, reverse=True):
            candidates.append(os.path.join(
                jvm_dir, name, "Contents/Home/bin/java"))
    candidates += ["/usr/bin/java", "java"]
    for c in candidates:
        if c and (os.path.sep not in c or os.path.exists(c)):
            return c
    return None

# ---------------------------------------------------------------- schema 校验
def validate_schema(data):
    """返回错误列表（空=通过）。--check 模式与加载时共用。"""
    errs = []
    if not isinstance(data, dict):
        return ["顶层须为 JSON object"]
    meta = data.get("meta")
    if not isinstance(meta, dict):
        errs.append("meta 缺失或非 object")
    else:
        if meta.get("schema_version") != SCHEMA_VERSION:
            errs.append("meta.schema_version 须为 %s（实际 %r）"
                        % (SCHEMA_VERSION, meta.get("schema_version")))
        for k in ("scenario", "source"):
            if not meta.get(k):
                errs.append("meta.%s 缺失" % k)
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        return errs + ["cases 缺失或非非空列表"]
    seen = set()
    for i, c in enumerate(cases):
        loc = "cases[%d]" % i
        if not isinstance(c, dict):
            errs.append("%s 非 object" % loc)
            continue
        cid = c.get("id")
        if not cid or not isinstance(cid, str):
            errs.append("%s.id 缺失" % loc)
            cid = loc
        if cid in seen:
            errs.append("%s id 重复" % cid)
        seen.add(cid)
        if c.get("kind") not in KIND_ENUM:
            errs.append("%s.kind 须为 %s 之一（实际 %r）"
                        % (cid, "/".join(KIND_ENUM), c.get("kind")))
        if not c.get("desc"):
            errs.append("%s.desc 缺失" % cid)
        if c.get("exempt"):
            continue  # 豁免条目登记不执行，ttl/expect 可空
        if not isinstance(c.get("ttl"), str) or not c["ttl"].strip():
            errs.append("%s.ttl 缺失或非非空字符串" % cid)
        exp = c.get("expect")
        if not isinstance(exp, list) or not exp:
            errs.append("%s.expect 缺失或非非空列表" % cid)
            continue
        for j, e in enumerate(exp):
            if not isinstance(e, list) or not e:
                errs.append("%s.expect[%d] 须为非空列表" % (cid, j))
                continue
            kind = e[0]
            if kind not in ASSERT_ARITY:
                errs.append("%s.expect[%d] 未知断言类型 %r" % (cid, j, kind))
            elif len(e) != ASSERT_ARITY[kind]:
                errs.append("%s.expect[%d] %s 须 %d 元（实际 %d）"
                            % (cid, j, kind, ASSERT_ARITY[kind], len(e)))
    return errs

# ---------------------------------------------------------------- 执行引擎
def strip_named_datatypes(g):
    """S6 实例级推理降级（2026-10-26 实测定案，限制⑩）：Pellet 2.3.1 对
    facet 类具名 datatype（onDatatype+withRestrictions）加载时忽略 pattern/
    minExclusive 三元组，但个体断言字面量后值空间判空 → range 违反 → 假不一致
    （模式层 individuals=0 不暴露）。剥离具名 datatype 声明与 range 引用；
    内联匿名 oneOf 枚举保留（实例层可强制执行）。facet 校验职责转 L2 脚本 +
    数据管线。"""
    import rdflib
    removed = 0
    for dt in list(g.subjects(rdflib.RDF.type, rdflib.RDFS.Datatype)):
        if not isinstance(dt, rdflib.term.URIRef):
            continue  # 内联匿名 bnode 保留
        for t in list(g.triples((dt, None, None))):
            g.remove(t); removed += 1
        for t in list(g.triples((None, None, dt))):
            g.remove(t); removed += 1
    return removed


def _prefix_header(base_text):
    """提取基底本体的 @prefix/@base 声明头（用例 ttl 依赖同一前缀语境）。"""
    return "".join(l + "\n" for l in base_text.splitlines()
                   if l.startswith("@prefix") or l.startswith("@base"))


def canonicalize_base(base_text, do_strip=True):
    """限制⑭确定性修复（2026-11-02 实测定案）：rdflib parse 对 SWRL RDF-list 的
    bnode 生成随机 uuid 标签，序列化输出跨进程漂移（同进程两次 parse→serialize
    md5 均不同，实证）→ owlready2 实体 id 依加载顺序分配 → Pellet 规则处理顺序
    漂移 → builtin 数值规则（swrlb:greaterThan 拒因通道）物化随机翻转（同一输入
    GC-040/042/EXP-A 跨进程 PASS/FAIL 漂移实证；PYTHONHASHSEED 固定不消除——
    bnode uuid 不受 hash seed 控制）。处置=RDF Dataset Canonicalization
    （rdflib.compare.to_canonical_graph）确定性重标 bnode → NT 文本缓存，
    序列化侧非确定性根除。一次性成本 ~60s（5308 三元组/1138 bnodes 实测）。
    本体文件与用例语义均不因此改动（bnode 标签不承载语义）。"""
    import rdflib
    from rdflib.compare import to_canonical_graph
    g = rdflib.Graph()
    g.parse(data=base_text, format="turtle")
    n_stripped = strip_named_datatypes(g) if do_strip else 0
    gc = to_canonical_graph(g)
    nt = gc.serialize(format="nt")
    # GC_CANON_ORDER=实验档开关：asc/desc 三元组排序已实测
    # 证伪（镜像翻转，不可用作规避），raw=canonical 原生序为定版默认——仅调试
    # 复现时使用，生产验收勿设
    order = os.environ.get("GC_CANON_ORDER", "raw")
    if order == "asc":
        nt = "".join(sorted(nt.splitlines(keepends=True)))
    elif order == "desc":
        nt = "".join(sorted(nt.splitlines(keepends=True), reverse=True))
    return nt, n_stripped


def run_one(case, base_nt, java, base_prefixes="", do_strip=True, engine="pellet"):
    import rdflib
    import owlready2
    owlready2.JAVA_EXE = java

    # 限制⑭：用例小图独立 parse（个体全具名，无 bnode）→ NT 拼接基底 canonical
    # 缓存文本——旧路径（combined turtle parse→XML serialize）已实证为漂移注入点
    cg = rdflib.Graph()
    cg.parse(data=base_prefixes + "\n# ==== 用例 %s 个体（虚构） ====\n" % case["id"]
             + case["ttl"], format="turtle")
    if do_strip:
        strip_named_datatypes(cg)  # 用例侧通常 noop（具名 datatype 声明在基底，已剥）
    case_nt = cg.serialize(format="nt")
    fd, tmp = tempfile.mkstemp(suffix=".nt")
    os.close(fd)
    result = {"id": case["id"], "kind": case.get("kind"), "desc": case["desc"],
              "asserts": [], "error": None, "engine": engine,
              "notes": ["基底 canonical NT 缓存 + 限制⑩剥离见启动日志（限制⑭确定性修复）"]
                       if do_strip else ["--no-strip：未执行限制⑩降级（调试档）"]}
    if engine != "pellet":
        result["notes"].append("推理引擎=%s（对照档：HermiT 不执行 SWRL，规则系断言 FAIL 属引擎能力边界）" % engine)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(base_nt)
            fh.write(case_nt)
        world = owlready2.World()
        onto = world.get_ontology(tmp).load()
        inconsistent = False
        inc_classes = []
        try:
            with onto:
                # --engine hermit（DL 对照档）：owlready2 的 HermiT
                # 通道不执行 SWRL 规则（仅 DL 推理）——规则系断言在 HermiT 下
                # 预期 FAIL，属引擎能力边界而非本体缺陷；用于对照 Pellet 限制⑪⑫
                # 是否 Pellet 特有
                if engine == "hermit":
                    # HermiT 通道无 infer_data_property_values 参数；datatype 限制
                    # 须传 ignore_unsupported_datatypes（owlready2 实测，限制⑤⑥⑬）
                    owlready2.sync_reasoner_hermit(
                        onto.world, infer_property_values=True,
                        ignore_unsupported_datatypes=True)
                else:
                    owlready2.sync_reasoner_pellet(
                        onto.world, infer_property_values=True,
                        infer_data_property_values=True)
            inc_classes = [c.name for c in onto.inconsistent_classes()]
            inconsistent = bool(inc_classes)
        except owlready2.base.OwlReadyInconsistentOntologyError as e:
            msg = str(e)
            if (not msg.strip()) or ("Ontology is inconsistent" in msg):
                inconsistent = True
            else:
                result["error"] = "%s 运行失败: %s" % (engine.capitalize(), msg[:300])
                return result
        for exp in case["expect"]:
            kind = exp[0]
            if kind == "consistent":
                ok = not inconsistent
                detail = "consistent=%s%s" % (not inconsistent,
                                              ("（inconsistent_classes=%s）" % inc_classes) if inc_classes else "")
            elif kind == "inconsistent":
                ok = inconsistent
                detail = "检出=%s%s" % (inconsistent,
                                        ("（%s）" % inc_classes) if inc_classes else "")
            else:
                if inconsistent:
                    ok, detail = False, "本体已不一致，类型/属性断言不可判"
                else:
                    ind_name, rest = exp[1], exp[2:]
                    ind = getattr(onto, ind_name, None)
                    if ind is None:
                        ok, detail = False, "个体 %s 未找到" % ind_name
                    elif kind in ("in_class", "not_in_class"):
                        has = any(getattr(c, "name", None) == rest[0]
                                  for c in ind.is_a)
                        ok = has if kind == "in_class" else not has
                        detail = "%s.is_a 含 %s = %s" % (ind_name, rest[0], has)
                    elif kind in ("prop_value", "no_prop_value"):
                        prop, obj_name = rest
                        vals = getattr(ind, prop, [])
                        if not isinstance(vals, list):
                            vals = [vals]
                        has = any(getattr(v, "name", None) == obj_name for v in vals)
                        ok = has if kind == "prop_value" else not has
                        detail = "%s.%s 含 %s = %s（值=%s）" % (
                            ind_name, prop, obj_name, has,
                            [getattr(v, "name", str(v)) for v in vals])
                    else:
                        ok, detail = False, "未知断言类型 %s" % kind
            result["asserts"].append(
                {"expect": list(exp), "ok": ok, "detail": detail})
        result["pass"] = (result["error"] is None
                          and all(a["ok"] for a in result["asserts"]))
        result["inconsistent_detected"] = inconsistent
    except Exception as e:
        result["error"] = "%s: %s" % (e.__class__.__name__, str(e)[:300])
        result["pass"] = False
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return result


def main():
    ap = argparse.ArgumentParser(description="S6 黄金用例执行器（泛化版）")
    ap.add_argument("ontology", nargs="?", help="基底本体 Turtle 路径")
    ap.add_argument("cases", nargs="?", help="用例外置 JSON 路径（schema 1.0）")
    ap.add_argument("--only", nargs="*", help="仅跑指定用例 id")
    ap.add_argument("--json-output", help="结果 JSON 落盘路径")
    ap.add_argument("--check", action="store_true",
                    help="仅 schema 校验（不跑 reasoner）")
    ap.add_argument("--no-strip", action="store_true",
                    help="调试档：不执行限制⑩具名 datatype 剥离")
    ap.add_argument("--engine", choices=["pellet", "hermit"], default="pellet",
                    help="推理引擎（默认 pellet；hermit=DL 对照档，不执行 SWRL 规则）")
    args = ap.parse_args()

    if args.check and args.cases is None and args.ontology:
        args.cases, args.ontology = args.ontology, None  # --check 单位置参数=用例文件
    if not args.cases:
        ap.error("缺少用例文件参数")
    if not os.path.exists(args.cases):
        print("用例文件不存在: %s" % args.cases); sys.exit(2)
    with open(args.cases, encoding="utf-8") as fh:
        data = json.load(fh)
    errs = validate_schema(data)
    if args.check:
        if errs:
            print("schema 校验失败（%d 项）:" % len(errs))
            for e in errs:
                print("  - %s" % e)
            sys.exit(1)
        print("schema 校验通过（schema_version=%s，cases=%d，其中 exempt=%d）"
              % (SCHEMA_VERSION, len(data["cases"]),
                 sum(1 for c in data["cases"] if c.get("exempt"))))
        sys.exit(0)
    if errs:
        print("用例文件 schema 校验失败（%d 项），先修正再执行:" % len(errs))
        for e in errs:
            print("  - %s" % e)
        sys.exit(2)
    if not args.ontology or not os.path.exists(args.ontology):
        print("本体文件不存在: %s" % args.ontology); sys.exit(2)

    java = find_java()
    if not java:
        print("未找到 Java，退出"); sys.exit(2)
    base_text = open(args.ontology, encoding="utf-8").read()
    import time as _time
    _t0 = _time.time()
    base_nt, n_stripped = canonicalize_base(base_text, do_strip=not args.no_strip)
    print("基底 canonicalization（限制⑭确定性修复）：%.1fs｜限制⑩剥离具名 datatype %d 条%s"
          % (_time.time() - _t0, n_stripped,
             "" if not args.no_strip else "（--no-strip 未执行）"))
    base_prefixes = _prefix_header(base_text)

    results = []
    n_exempt = 0
    for c in data["cases"]:
        if args.only and c["id"] not in args.only:
            continue
        if c.get("exempt"):
            n_exempt += 1
            print("EXEMPT [%s] %s" % (c["id"], c["desc"][:60]))
            continue
        r = run_one(c, base_nt, java, base_prefixes=base_prefixes,
                    do_strip=not args.no_strip, engine=args.engine)
        mark = "PASS" if r["pass"] else ("ERROR" if r["error"] else "FAIL")
        print("%s [%s] %s" % (mark, r["id"], r["desc"][:60]))
        if r["error"]:
            print("    error: %s" % r["error"])
        for a in r["asserts"]:
            print("    %s %s | %s" % ("✓" if a["ok"] else "✗", a["expect"], a["detail"]))
        results.append(r)

    n_pass = sum(1 for r in results if r["pass"])
    summary = {"total": len(results), "pass": n_pass,
               "fail": len(results) - n_pass, "exempt": n_exempt,
               "pass_rate": round(n_pass / len(results) * 100, 1) if results else 0}
    print("=" * 60)
    print("汇总: %s" % summary)
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as fh:
            json.dump({"summary": summary, "results": results},
                      fh, ensure_ascii=False, indent=2)
        print("JSON 已写入: %s" % args.json_output)
    sys.exit(0 if summary["fail"] == 0 else 1)


if __name__ == "__main__":
    main()
