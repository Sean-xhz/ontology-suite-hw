#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""self_test.py —— ontology-review 机械回归层（最小可用 Eval）。

确定性断言（确定性事实用规则判断，不让模型凭感觉打分）。
断言清单=专家实审反馈的回归用例化（每个真实失败=一条断言；
反馈轮次↔断言映射见本 skill CHANGELOG.md 实证证据登记）：

  E1 提取管线 exit 0 且 counts 自洽（TTL 统计 == 合并后计数）
  E2 md_props 属性名零空值（首列取名+表头归一）
  E3 实体表每行 cell 数 == 表头列数（转义管道不切列+内联表不混入）
  E4 规则按 md_key 分组后，多变体组须有通道标注（防重复卡）
  E5 class_groups 覆盖全部类且 child depth = parent depth+1（分组层次）
  E6 SKOS 空定义必须带 definition_missing 显式标记（不静默）
  E7 build 产物无占位符残留（__DATA_JSON__/vendor/__RUN_NAME__ 注入完整）
  E8 模板呈现断言：呈现纪律（references/presentation-discipline.md）的关键结构在位
     （宽表滚动/类分组/批注交互/多条批注/北京时间/缩进色条/sticky 批注列/折叠/通俗翻译/SWRL 折叠）
  E9 模板逻辑脚本 node --check 语法过（无 node 环境降级 skip 并登记）
  E10 规则通俗翻译：有 atoms 的规则必有 plain；句中不得残留原始变量名
      （vR1_a 形态）或占位符（?N/?v 形态）——角色名词代入后专家零对照成本

载体纪律：skill 资产不含业务数据——断言逻辑运行时读取 run 目录。
fixture run 必须显式传入：--runs 目录 ... 或环境变量 ONTOLOGY_SELFTEST_RUNS
（os.pathsep 分隔多目录）；两者都缺 → exit 2 带指引。
虚构示例载体（如套件 examples/ 的建模 run）可直接传入；真实业务载体只本地跑。

用法：python3 self_test.py [--runs 目录 ...]
exit 0 全过；1 有断言失败；2 环境/参数错。
"""
import argparse
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
                (".rulecard.depth-2", "类层级缩进色条·带提权选择器（R2②b，防 .rulecard margin 覆盖回归）")]
        miss = [d for tok, d in need if tok not in tpl]
        check("E8", "[%s] 模板呈现结构在位" % tag, not miss,
              "缺失 %s" % miss if miss else "%d 项结构断言全在" % len(need))

        # E9 node --check
        blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
        node = shutil.which("node")
        if not node or not blocks:
            check("E9", "[%s] 模板 JS 语法（node 缺失，skip）" % tag, True, "skip 登记")
        else:
            js = os.path.join(td, "logic.js")
            with open(js, "w", encoding="utf-8") as fh:
                fh.write(blocks[-1])
            q = subprocess.run([node, "--check", js], capture_output=True, text=True)
            check("E9", "[%s] 模板 JS 语法 node --check" % tag, q.returncode == 0,
                  q.stderr[:200] if q.returncode else "")


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
    fails = [r for r in results if not r[2]]
    print("-" * 60)
    print("断言 %d 条：PASS %d / FAIL %d" % (len(results),
          len(results) - len(fails), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
