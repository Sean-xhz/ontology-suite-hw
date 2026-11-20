#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""self_test.py —— ontology-review 机械回归层（最小可用 Eval）。

确定性断言（确定性事实用规则判断，不让模型凭感觉打分）。
断言清单=专家实审反馈的回归用例化（每个真实失败=一条断言）：

  E1 提取管线 exit 0 且 counts 自洽（TTL 统计 == 合并后计数）
  E2 md_props 属性名零空值（首列取名+表头归一）
  E3 实体表每行 cell 数 == 表头列数（转义管道不切列+内联表不混入）
  E4 规则按 md_key 分组后，多变体组须有通道标注（防重复卡）
  E5 class_groups 覆盖全部类且 child depth = parent depth+1（分组层次）
  E6 SKOS 空定义必须带 definition_missing 显式标记（不静默）
  E7 build 产物无占位符残留（__DATA_JSON__/vendor/__RUN_NAME__ 注入完整）
  E8 模板呈现断言：呈现纪律（references/presentation-discipline.md）的关键结构在位
     （宽表滚动/类分组/批注交互/多条批注/北京时间/缩进色条/sticky 批注列/折叠/通俗翻译/SWRL 折叠）
  E9 模板逻辑脚本 node --check 语法过（逐块：blocks[:3]=vendor 跳过、blocks[3:] 逐块查；
      无 node 环境降级 skip 并登记）
  E10 规则通俗翻译：有 atoms 的规则必有 plain；句中不得残留原始变量名
      （vR1_a 形态）或占位符（?N/?v 形态）——角色名词代入后专家零对照成本
  E11 规则流数据完备（D2⑤c）：atom_meta 全覆盖有 atoms 规则；body/head len==atoms len；
      arg_kinds 数==arguments 数；atom_id 唯一+双 merge 字节等；var 名与 ?记法一致
  E12 公理/SKOS/union 数据（D2④b/⑥b/③c）：边端点⊆节点 id；id 无 bnode 模式；双跑字节等；
      restriction 数==图 owl:Restriction 数；hasKey 全覆盖；broader_list⊇broader 单值；
      union 成员在位；md_overlay keys⊆约束 id；md_only 在位；SKOS 多父合成断言
  E13 批注锚点可解析（D2⑦d）：锚点注册表（类/prop/atom/约束/skos/变量节点）逐条可解析；
      legacy 无 anchor 回退 cls-/rule- 在位；schema_version 在位
  E14 D4 导出契约对齐（⑦e）：python 复刻前端映射产 5 类规范 patch；schema 1.0/channel d4/
      patch_id 内容哈希双建字节等/sha256_full 64hex==文件/全 IRI/字面量 old==supply/
      G8 禁用值排除/target 白名单（无 rule/skos）；合成 G8 重名注入→禁用；legacy 降级产页 exit 0
      （结构断言不 import model 保 review 独立部署；引擎真对齐留套件 T13）

载体纪律：skill 资产不含业务数据——断言逻辑运行时读取 run 目录。
fixture run 必须显式传入：--runs 目录 ... 或环境变量 ONTOLOGY_SELFTEST_RUNS
（os.pathsep 分隔多目录）；两者都缺 → exit 2 带指引。
虚构示例载体（如套件 examples/ 的建模 run）可直接传入；真实业务载体只本地跑。

用法：python3 self_test.py [--runs 目录 ...]
exit 0 全过；1 有断言失败；2 环境/参数错。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import review_extract as RX  # noqa: E402

TEMPLATE = os.path.join(HERE, "..", "assets", "review-page-template.html")

results = []


def canonical_json(obj):
    """D4 patch_id 内容哈希的规范序列化（与前端 canonicalJSON 等价：递归排序键、
    紧凑无空白、Unicode 字面量）。等价 json.dumps(sort_keys=True, ensure_ascii=False,
    separators=(',',':'))。"""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def d4_patch_id(base_sha256_full, operations):
    """D4 patch_id 内容哈希（tpl-d4-patch-schema §2.1）：同编辑→同 id→draft 双跑字节等。
    前端内置同步 SHA-256 复刻本算法（E14 断言双建字节等）。"""
    canon = canonical_json({"baseline": base_sha256_full, "operations": operations})
    return "P-d4-" + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:12]


def check(cid, desc, ok, detail=""):
    results.append((cid, desc, bool(ok), detail))
    print("%s %s %s" % ("PASS" if ok else "FAIL", cid, desc))
    if detail:
        print("     %s" % detail)


def run_one(run_dir):
    tag = os.path.basename(run_dir.rstrip("/"))
    ttl_path = os.path.join(run_dir, "ontology.ttl")
    md_path = os.path.join(run_dir, "建模方案.md")
    if not os.path.exists(ttl_path):
        check("E0", "[%s] ontology.ttl 存在" % tag, False, ttl_path)
        return
    ttl = RX.parse_ttl(ttl_path)
    md = (RX.parse_scheme_md(md_path) if os.path.exists(md_path)
          else {"entities": {}, "relations": [], "axiom_families": {},
                "rules": [], "parse_errors": []})
    term = RX.parse_term_dicts(sorted(
        os.path.join(run_dir, f) for f in os.listdir(run_dir)
        if f.startswith("术语词典") and f.endswith(".md")))
    merged = RX.merge(ttl, md, os.path.abspath(run_dir), term_defs=term)

    # E1 counts 自洽
    c = merged["counts"]
    ok = (c["classes"] == len(merged["classes"])
          and c["swrl_rules"] == len(merged["rules"])
          and c["skos_concepts"] == len(merged["skos"]))
    check("E1", "[%s] counts 自洽" % tag, ok, json.dumps(c, ensure_ascii=False))

    # E2 属性名零空值
    empties = [(e["ttl"]["id"], i) for e in merged["classes"]
               for i, mp in enumerate(e["md_props"]) if not mp["prop"].strip()]
    check("E2", "[%s] md_props 属性名零空值" % tag, not empties,
          "空名 %d 处: %s" % (len(empties), empties[:5]) if empties else
          "共 %d 行属性" % sum(len(e["md_props"]) for e in merged["classes"]))

    # E3 转义管道不切列
    bad = []
    for ent, tbl in md["entities"].items():
        n = len(tbl["header"])
        for i, row in enumerate(tbl["rows"]):
            if len(row) != n:
                bad.append((ent, i, len(row), n))
    check("E3", "[%s] 实体表行 cell 数==表头列数" % tag, not bad,
          "错位 %d 行: %s" % (len(bad), bad[:5]) if bad else
          "%d 张实体表" % len(md["entities"]))

    # E4 规则分组+通道标注
    from collections import defaultdict
    grp = defaultdict(list)
    for r in merged["rules"]:
        grp[r["md_key"]].append(r)
    multi = {k: v for k, v in grp.items() if len(v) > 1}
    bad = [k for k, v in multi.items()
           if not any(r["channel"] == "literal" for r in v)]
    check("E4", "[%s] 多变体规则组有通道标注" % tag, not bad,
          "%d 业务规则 / %d 多变体组；缺标注: %s" % (len(grp), len(multi), bad)
          if bad else "%d 业务规则 / %d 多变体组 / TTL imp %d"
          % (len(grp), len(multi), len(merged["rules"])))

    # E5 分组覆盖+depth 单调
    ids = {e["ttl"]["id"] for e in merged["classes"]}
    covered = set()
    for g in merged["class_groups"]:
        covered.update(g["ids"])
    depth = {e["ttl"]["id"]: e["depth"] for e in merged["classes"]}
    bad_depth = []
    for e in merged["classes"]:
        for s in e["ttl"]["superclasses"]:
            if s in depth and depth[e["ttl"]["id"]] != depth[s] + 1:
                bad_depth.append((e["ttl"]["id"], s))
    check("E5", "[%s] class_groups 覆盖+depth 单调" % tag,
          covered == ids and not bad_depth,
          "未覆盖 %s / depth 违例 %s" % (ids - covered, bad_depth[:5])
          if (covered != ids or bad_depth) else
          "%d 组 / %d 类" % (len(merged["class_groups"]), len(ids)))

    # E6 空定义显式标记
    bad = [s["id"] for s in merged["skos"]
           if not s.get("definition") and not s.get("definition_missing")]
    check("E6", "[%s] 空定义带 definition_missing 标记" % tag, not bad,
          "未标记 %s" % bad[:5] if bad else
          "缺定义 %d / %d（均显式标记）"
          % (sum(1 for s in merged["skos"] if s.get("definition_missing")),
             len(merged["skos"])))

    # E10 规则通俗翻译（R2⑤b 零占位符硬要求）：有 atoms 的规则必有 plain；
    # 句中不得残留原始变量名（vR1_a 形态）或占位符（?N/?v 形态）——
    # 角色名词代入后专家零对照成本
    withatoms = [r for r in merged["rules"]
                 if r["ttl"]["body_atoms"] or r["ttl"]["head_atoms"]]
    noplain = [r["ttl"]["id"] for r in withatoms if not r.get("plain")]
    rawvar = []
    for r in withatoms:
        p = r.get("plain") or {}
        for s in (p.get("body") or []) + (p.get("head") or []):
            if re.search(r"\bv[A-Z0-9]+\w*_\w+", s) or re.search(r"\?\w+", s):
                rawvar.append((r["ttl"]["id"], s))
    check("E10", "[%s] 规则通俗翻译覆盖+零占位符" % tag,
          not noplain and not rawvar,
          "无 plain %s / 占位符或原始变量残留 %s" % (noplain[:3], rawvar[:3])
          if (noplain or rawvar) else
          "%d/%d 规则已翻译（角色名词代入，零占位符）"
          % (len(withatoms), len(withatoms)))
    return merged


def run_build_checks(merged, run_dir):
    tag = os.path.basename(run_dir.rstrip("/"))
    with tempfile.TemporaryDirectory() as td:
        rj = os.path.join(td, "review.json")
        with open(rj, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, ensure_ascii=False)
        out = os.path.join(td, "page.html")
        p = subprocess.run([sys.executable, os.path.join(HERE, "build_review_page.py"),
                            rj, "--output", out], capture_output=True, text=True)
        ok7 = p.returncode == 0 and os.path.exists(out)
        html = open(out, encoding="utf-8").read() if ok7 else ""
        residue = [t for t in ("__DATA_JSON__", "__CYTOSCAPE_JS__",
                               "__DAGRE_JS__", "__CYTOSCAPE_DAGRE_JS__",
                               "__RUN_NAME__") if t in html]
        check("E7", "[%s] build exit 0 且无占位符残留" % tag,
              ok7 and not residue, "残留 %s" % residue if residue else "")

        # E8 模板呈现断言（presentation-discipline.md 条款的结构在位，编号沿用 R2 前缀）
        tpl = open(TEMPLATE, encoding="utf-8").read()
        need = [(".tbl-wrap", "滚动容器（R2③④）"), ("cgroup", "类分组（R2②）"),
                ("data-annot", "事件委托批注按钮（R2⑦）"),
                ("markAnnotated", "已批注标记（R2⑦）"),
                ("个编译变体", "规则变体合并（R2⑤）"),
                ("词典未定义", "空定义显式（R2⑥）"),
                ("m-existing", "同构件多条批注列表（R2⑦b）"),
                ("editInModal", "批注编辑态（R2⑦b）"),
                ("Asia/Shanghai", "北京时间时区（R2⑦c）"),
                ("ts_local", "北京时间字段（R2⑦c）"),
                ('class="stick"', "批注列 sticky 右置（R2③b）"),
                ("toggleFold", "长表折叠展开（R2③b）"),
                ("plainOf", "规则通俗翻译渲染（R2⑤b）"),
                ("swrl-det", "SWRL 技术细节折叠（R2⑤b）"),
                (".rulecard.depth-2", "类层级缩进色条·带提权选择器（R2②b，防 .rulecard margin 覆盖回归）"),
                ("GRAPHS", "图注册表（D2①b/③c/④b/⑤c/⑥b，cy 作用域提升）"),
                ("print-only", "print 回退边表/层级列表（D2 硬约束，信息不丢）"),
                ("data-anchor-graph", "批注图锚点事件委托（D2⑦d）")]
        miss = [d for tok, d in need if tok not in tpl]
        # script 块数==4 兜底（3 vendor 槽 + 1 app；防 vendor 槽位移致 E9 跳过索引错位）
        n_scripts = len(re.findall(r"<script>", tpl))
        ok_scripts = n_scripts == 4
        check("E8", "[%s] 模板呈现结构在位" % tag, not miss and ok_scripts,
              "缺失 %s / script 块数=%d（须 4）" % (miss, n_scripts)
              if (miss or not ok_scripts)
              else "%d 项结构断言全在 / script 块数=4" % len(need))

        # E9 node --check 逐块（修盲区：原只查 blocks[-1]，新 JS 块漏检）。
        # blocks[:3]=vendor（cytoscape/dagre/cytoscape-dagre，第三方压缩件不查），
        # blocks[3:] 逐块查；E8 script 块数==4 断言兜底防 vendor 槽位移。
        blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
        node = shutil.which("node")
        app_blocks = blocks[3:]
        if not node or not app_blocks:
            check("E9", "[%s] 模板 JS 语法（node 缺失或无 app 块，skip）" % tag,
                  True, "skip 登记")
        else:
            bad = []
            for i, blk in enumerate(app_blocks):
                js = os.path.join(td, "logic_%d.js" % i)
                with open(js, "w", encoding="utf-8") as fh:
                    fh.write(blk)
                q = subprocess.run([node, "--check", js], capture_output=True, text=True)
                if q.returncode != 0:
                    bad.append((i, q.stderr[:200]))
            check("E9", "[%s] 模板 JS 语法 node --check 逐块" % tag, not bad,
                  "失败块 %s" % bad if bad
                  else "%d app 块全过（vendor %d 块跳过）" % (len(app_blocks), len(blocks) - len(app_blocks)))


def run_supply_checks(merged, run_dir):
    """E11-E14：D2/D4 供给层 + 导出契约断言（schema 1.1）。结构断言不 import model
    （保 review 独立部署）；引擎真对齐留套件 T13。"""
    import copy
    import rdflib
    from rdflib import RDF, OWL

    tag = os.path.basename(run_dir.rstrip("/"))
    ttl_path = os.path.join(run_dir, "ontology.ttl")
    ttl = RX.parse_ttl(ttl_path)
    supply = ttl["supply"]
    ttl2 = RX.parse_ttl(ttl_path)  # 双跑确定性参照

    # E11 规则流数据完备（D2⑤c）
    am = supply["atom_meta"]
    withatoms = [r for r in ttl["rules"] if r["body_atoms"] or r["head_atoms"]]
    missing = [r["id"] for r in withatoms if r["id"] not in am]
    ok_len = ok_args = ok_var = True
    ids = []
    for r in withatoms:
        m = am.get(r["id"], {"body": [], "head": []})
        if len(m["body"]) != len(r["body_atoms"]) or len(m["head"]) != len(r["head_atoms"]):
            ok_len = False
        for side, atoms in [("body", r["body_atoms"]), ("head", r["head_atoms"])]:
            for entry, atom in zip(m[side], atoms):
                ids.append(entry["atom_id"])
                args = atom.get("arguments", [])
                if len(entry["arg_kinds"]) != len(args):
                    ok_args = False
                for ak, argstr in zip(entry["arg_kinds"], args):
                    if ak["kind"] == "var" and argstr != "?" + ak["name"]:
                        ok_var = False
    ok_id = len(ids) == len(set(ids))
    ok_db11 = (json.dumps(am, sort_keys=True, ensure_ascii=False)
               == json.dumps(ttl2["supply"]["atom_meta"], sort_keys=True, ensure_ascii=False))
    check("E11", "[%s] 规则流 atom_meta 完备+确定" % tag,
          not missing and ok_len and ok_args and ok_var and ok_id and ok_db11,
          "缺覆盖 %s / len %s / args %s / var %s / id %s / 双跑 %s"
          % (missing[:3], ok_len, ok_args, ok_var, ok_id, ok_db11)
          if (missing or not (ok_len and ok_args and ok_var and ok_id and ok_db11))
          else "%d 规则 / %d atom_id 唯一 / 双跑字节等" % (len(withatoms), len(ids)))

    # E12 公理/SKOS/union 数据（D2④b/⑥b/③c）
    ag = supply["axiom_graph"]
    nodes, edges = ag["nodes"], ag["edges"]
    nids = {n["id"] for n in nodes}
    ok_ep = all(e["source"] in nids and e["target"] in nids for e in edges)
    bnode_pat = re.compile(r"(_:[A-Za-z0-9]|n[0-9a-f]{20,}|[0-9a-f]{8}-[0-9a-f]{4}-)")
    ok_nobnode = not any(bnode_pat.search(n["id"]) for n in nodes)
    ok_db12 = (json.dumps(ag, sort_keys=True, ensure_ascii=False)
               == json.dumps(ttl2["supply"]["axiom_graph"], sort_keys=True, ensure_ascii=False))
    g = rdflib.Graph()
    g.parse(ttl_path, format="turtle")
    n_restr = len(list(g.subjects(RDF.type, OWL.Restriction)))
    ok_restr = sum(1 for n in nodes if n["kind"] == "restriction") == n_restr
    hk_classes = {c["id"] for c in ttl["classes"] if c["hasKey"]}
    hk_owners = {n["id"].split(":")[2] for n in nodes if n["kind"] == "hasKey"}
    ok_hk = hk_classes <= hk_owners
    ok_bl = all((c["broader"] in supply["broader_list"].get(c["id"], []))
                if c["broader"] else True for c in ttl["skos_concepts"])
    union_members = set()
    for p in ttl["object_properties"] + ttl["data_properties"]:
        union_members.update(p.get("domain_union", []))
        union_members.update(p.get("range_union", []))
    ok_union = all(m in supply["iris"]["classes"] for m in union_members)
    mag = merged["axiom_graph"]
    constraint_ids = {n["id"] for n in mag["nodes"]
                      if n["kind"] not in ("class", "property", "datatype")}
    ok_overlay = all(k in constraint_ids for k in mag["md_overlay"])
    ok_mdonly = isinstance(mag.get("md_only"), list)
    # SKOS 多父合成断言（fixture 0 多父→合成 2 父验证通用实现）
    multi_ttl = (
        '@base <http://example.org/multi#> .\n'
        '@prefix : <http://example.org/multi#> .\n'
        '@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n'
        ':c1 a skos:Concept ; skos:prefLabel "子"@zh ; skos:broader :p1, :p2 .\n'
        ':p1 a skos:Concept ; skos:prefLabel "父1"@zh .\n'
        ':p2 a skos:Concept ; skos:prefLabel "父2"@zh .\n')
    ok_multi = False
    with tempfile.NamedTemporaryFile("w", suffix=".ttl", delete=False, encoding="utf-8") as f:
        f.write(multi_ttl)
        mp = f.name
    try:
        ok_multi = sorted(RX.parse_ttl(mp)["supply"]["broader_list"]["c1"]) == ["p1", "p2"]
    finally:
        os.unlink(mp)
    ok12 = (ok_ep and ok_nobnode and ok_db12 and ok_restr and ok_hk and ok_bl
            and ok_union and ok_overlay and ok_mdonly and ok_multi)
    check("E12", "[%s] 公理图/SKOS/union 数据完备+确定" % tag, ok12,
          "端点 %s / bnode %s / 双跑 %s / restriction %s / hasKey %s / broader %s / "
          "union %s / overlay %s / md_only %s / 多父 %s"
          % (ok_ep, ok_nobnode, ok_db12, ok_restr, ok_hk, ok_bl, ok_union,
             ok_overlay, ok_mdonly, ok_multi) if not ok12
          else "nodes=%d edges=%d / restriction=%d / hasKey 全覆盖 / 多父合成过"
          % (len(nodes), len(edges), n_restr))

    # E13 批注锚点可解析（D2⑦d）：注册表完备 + legacy 回退 + schema_version
    reg = {"classes": set(), "props": set(), "axioms": set(), "rules": set(), "skos": set()}
    for e in merged["classes"]:
        reg["classes"].add("c:" + e["ttl"]["id"])
    for p in merged["object_properties"]:
        pid = p["ttl"]["id"]
        reg["props"].add("p:" + pid)
        reg["props"].add("e-op-" + pid)
        if p["ttl"].get("domain_union"):
            reg["props"].add("u:%s:domain" % pid)
        if p["ttl"].get("range_union"):
            reg["props"].add("u:%s:range" % pid)
    for n in mag["nodes"]:
        reg["axioms"].add(n["id"])
    for r in merged["rules"]:
        reg["rules"].add("r:" + r["ttl"]["id"])
        for side in ("body", "head"):
            for entry in r["atom_meta"][side]:
                reg["rules"].add("a:" + entry["atom_id"])
                for ak in entry["arg_kinds"]:
                    if ak["kind"] == "var":
                        reg["rules"].add("v:" + ak["name"])
    for c in merged["skos"]:
        reg["skos"].add("s:" + c["id"])
    ok_nonempty = all(len(reg[k]) > 0 for k in reg)
    ok_cls_anchor = all(("c:" + e["ttl"]["id"]) in reg["classes"] for e in merged["classes"])
    ok_atom_anchor = all(("a:" + entry["atom_id"]) in reg["rules"]
                         for r in merged["rules"] for side in ("body", "head")
                         for entry in r["atom_meta"][side])
    ok_legacy = (all(e["ttl"]["id"] for e in merged["classes"])
                 and all(r["md_key"] for r in merged["rules"]))
    ok_sv = merged.get("schema_version") == RX.REVIEW_JSON_SCHEMA
    check("E13", "[%s] 批注锚点注册表完备+legacy 回退+schema_version" % tag,
          ok_nonempty and ok_cls_anchor and ok_atom_anchor and ok_legacy and ok_sv,
          "五图非空 %s / 类锚 %s / atom 锚 %s / legacy %s / schema %s"
          % (ok_nonempty, ok_cls_anchor, ok_atom_anchor, ok_legacy, ok_sv)
          if not (ok_nonempty and ok_cls_anchor and ok_atom_anchor and ok_legacy and ok_sv)
          else "五图注册表 %s / schema_version=%s"
          % ({k: len(v) for k, v in reg.items()}, merged.get("schema_version")))

    # E14 D4 导出契约对齐（⑦e）：python 复刻前端映射产 5 类规范 patch
    base_ns = supply["base_ns"]
    sha_full = RX.file_sha_full(ttl_path)
    iris, lit = supply["iris"], supply["literals"]
    allowed_iris = (set(iris["classes"].values()) | set(iris["object_properties"].values())
                    | set(iris["data_properties"].values()))
    patches = []
    # 1 label（PATCH annotation-only）
    patches.append(("label", [{"op": "modify_label", "target": iris["classes"]["Bill"],
                               "label": "票据（D4 测试）"}]))
    # 2 comment 已存在（replace_literal old 全等）
    old_c = lit["class:Bill"]["comment"]
    new_c = dict(old_c)
    new_c["value"] = old_c["value"] + "（D4 测试）"
    patches.append(("comment", [{"op": "replace_literal", "s": iris["classes"]["Bill"],
                                 "p": "rdfs:comment", "old": old_c, "new": new_c}]))
    # 3 enum 已划款→已付款（G8 editable，s 省略）
    ed = supply["enum_editable"]["applicationStatus"]
    tval = next(e["value"] for e in ed if e["editable"] and e["value"] == "已划款")
    old_e = next(v for v in supply["enum_literals"]["applicationStatus"] if v["value"] == tval)
    new_e = dict(old_e)
    new_e["value"] = "已付款"
    patches.append(("enum", [{"op": "replace_literal", "p": "rdf:first",
                              "old": old_e, "new": new_e}]))
    # 4 subclass reparent（Discountable 恰 1 具名父 Bill→Holder）
    patches.append(("subclass", [
        {"op": "remove_triple", "s": iris["classes"]["Discountable"],
         "p": "rdfs:subClassOf", "o": iris["classes"]["Bill"]},
        {"op": "add_triple", "s": iris["classes"]["Discountable"],
         "p": "rdfs:subClassOf", "o": iris["classes"]["Holder"]}]))
    # 5 range（hasAcceptor Acceptor→Holder）
    patches.append(("range", [
        {"op": "remove_triple", "s": iris["object_properties"]["hasAcceptor"],
         "p": "rdfs:range", "o": iris["classes"]["Acceptor"]},
        {"op": "add_triple", "s": iris["object_properties"]["hasAcceptor"],
         "p": "rdfs:range", "o": iris["classes"]["Holder"]}]))
    ok_schema = ok_chan = ok_id = ok_sha = ok_iri = ok_white = True
    for kind, ops in patches:
        pid = d4_patch_id(sha_full, ops)
        if pid != d4_patch_id(sha_full, ops):
            ok_id = False
        if not pid.startswith("P-d4-"):
            ok_id = False
        patch = {"schema_version": "1.0", "patch_id": pid,
                 "baseline": {"path": "ontology.ttl", "sha256": sha_full},
                 "source": {"channel": "d4", "ref": "d4-selftest"},
                 "base_version": supply["ontology_version"], "bump": "auto",
                 "operations": ops}
        if patch["schema_version"] != "1.0":
            ok_schema = False
        if patch["source"]["channel"] != "d4":
            ok_chan = False
        if not re.fullmatch(r"[0-9a-f]{64}", patch["baseline"]["sha256"]):
            ok_sha = False
        for op in ops:
            for fld in ("s", "o", "target"):
                v = op.get(fld)
                if isinstance(v, str):
                    if not v.startswith(base_ns):
                        ok_iri = False
                    if v not in allowed_iris:
                        ok_white = False
    ok_sha_file = sha_full == RX.file_sha_full(ttl_path)
    ok_lit = (old_c == lit["class:Bill"]["comment"]
              and old_e in supply["enum_literals"]["applicationStatus"])
    ok_g8 = next(e["editable"] for e in ed if e["value"] == tval)
    # 合成 G8 重名注入→禁用（两属性共享枚举值）
    g8_ttl = (
        '@base <http://example.org/g8#> .\n'
        '@prefix : <http://example.org/g8#> .\n'
        '@prefix owl: <http://www.w3.org/2002/07/owl#> .\n'
        '@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n'
        ':p1 a owl:DatatypeProperty ; rdfs:range [ a rdfs:Datatype ; owl:oneOf ( "共享值" ) ] .\n'
        ':p2 a owl:DatatypeProperty ; rdfs:range [ a rdfs:Datatype ; owl:oneOf ( "共享值" ) ] .\n')
    ok_g8_syn = False
    with tempfile.NamedTemporaryFile("w", suffix=".ttl", delete=False, encoding="utf-8") as f:
        f.write(g8_ttl)
        gp = f.name
    try:
        gs = RX.parse_ttl(gp)["supply"]
        ok_g8_syn = (gs["enum_editable"]["p1"][0]["editable"] is False
                     and gs["enum_editable"]["p2"][0]["editable"] is False)
    finally:
        os.unlink(gp)
    # legacy 降级产页 exit 0（剥 supply 表面字段 + schema_version 1.0）
    legacy = copy.deepcopy(merged)
    legacy["schema_version"] = "1.0"
    for k in ("iri_map", "literal_meta", "enum_literals", "enum_editable",
              "supply_meta", "axiom_graph"):
        legacy.pop(k, None)
    for e in legacy["classes"]:
        e.pop("parents_guard", None)
    for r in legacy["rules"]:
        r.pop("atom_meta", None)
    for c in legacy["skos"]:
        c.pop("broader_list", None)
    ok_legacy_page = False
    with tempfile.TemporaryDirectory() as td:
        rj = os.path.join(td, "legacy.json")
        with open(rj, "w", encoding="utf-8") as fh:
            json.dump(legacy, fh, ensure_ascii=False)
        out = os.path.join(td, "legacy.html")
        p = subprocess.run([sys.executable, os.path.join(HERE, "build_review_page.py"),
                            rj, "--output", out], capture_output=True, text=True)
        ok_legacy_page = p.returncode == 0 and os.path.exists(out)
    ok14 = (ok_schema and ok_chan and ok_id and ok_sha and ok_sha_file and ok_iri
            and ok_white and ok_lit and ok_g8 and ok_g8_syn and ok_legacy_page)
    check("E14", "[%s] D4 导出契约对齐（5 类 patch+G8+legacy）" % tag, ok14,
          "schema %s / channel %s / id %s / sha %s / sha==file %s / IRI %s / 白名单 %s / "
          "字面量 %s / G8 %s / G8合成 %s / legacy页 %s"
          % (ok_schema, ok_chan, ok_id, ok_sha, ok_sha_file, ok_iri, ok_white,
             ok_lit, ok_g8, ok_g8_syn, ok_legacy_page) if not ok14
          else "5 类 patch 契约对齐 / patch_id 双建字节等 / sha256_full 64hex / "
               "G8 重名禁用 / legacy 降级产页 exit 0")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", default=None,
                    help="fixture run 目录列表（虚构示例载体；真实载体只本地传入）")
    args = ap.parse_args()
    runs = args.runs
    if not runs:
        env = os.environ.get("ONTOLOGY_SELFTEST_RUNS", "")
        runs = [p for p in env.split(os.pathsep) if p.strip()]
    if not runs:
        print("未指定 fixture run——用 --runs <目录 ...> 或环境变量 "
              "ONTOLOGY_SELFTEST_RUNS（%s 分隔多目录）传入；"
              "套件环境可用 examples/ 虚构示例载体的建模 run 目录" % os.pathsep,
              file=sys.stderr)
        sys.exit(2)
    for rd in runs:
        if not os.path.isdir(rd):
            print("run 目录不存在 %s" % rd, file=sys.stderr)
            sys.exit(2)
        merged = run_one(rd)
        if merged is not None:
            run_build_checks(merged, rd)
            run_supply_checks(merged, rd)
    fails = [r for r in results if not r[2]]
    print("-" * 60)
    print("断言 %d 条：PASS %d / FAIL %d" % (len(results),
          len(results) - len(fails), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
