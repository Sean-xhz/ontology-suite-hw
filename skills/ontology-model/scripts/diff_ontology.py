#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diff_ontology.py — 本体版本机械 diff（IT-07，套件打磨档一）。

两版本 TTL → 三元组级 added/removed/changed 对照（rdflib.compare.graph_diff，
bnode 规范化安全），按构件四面（类/属性/规则/Concept）归类，产 JSON + md 修订对照表草稿
（人工只裁定不比对）。纯 rdflib（model 不反向 import review/simulate 纪律）；三元组级
内容比对非仅 key 集合级（WebProtégé T11 教训：骨架在≠内容在）；计数单一事实源（机械实测）。

用法:
  python3 diff_ontology.py OLD.ttl NEW.ttl [--json-output diff.json] [--md-output 对照表.md]
exit 0 正常 / 2 输入错（缺文件/解析失败）。零回写（只读两版本，输出落指定路径）。
"""
import argparse
import json
import os
import sys
from rdflib import Graph, Namespace, RDF, OWL, URIRef
from rdflib.compare import graph_diff

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


def local(x):
    s = str(x)
    return s.split("#")[-1].split("/")[-1]


def kind_of(g, subj):
    types = set(g.objects(subj, RDF.type))
    if OWL.Class in types:
        return "class"
    if OWL.ObjectProperty in types or OWL.DatatypeProperty in types:
        return "property"
    if SWRL.Imp in types:
        return "rule"
    if SKOS.Concept in types:
        return "concept"
    return "other"


def by_subject(g):
    d = {}
    for s, p, o in g:
        d.setdefault(s, set()).add((p, o))
    return d


def fmt_po(p, o):
    return "%s %s" % (local(p), local(o) if isinstance(o, URIRef) else str(o))


def diff(old_path, new_path):
    g_old, g_new = Graph(), Graph()
    g_old.parse(old_path, format="turtle")
    g_new.parse(new_path, format="turtle")
    both, only_old, only_new = graph_diff(g_old, g_new)
    # 规范化并集：graph_diff 三结果图共享 bnode 规范标签——用并集重建两版本图，
    # 避免原图随机 bnode 标签跨解析不一致致假构件增删（相同版本须 0 增删）。
    g_old_c, g_new_c = Graph(), Graph()
    for t in both:
        g_old_c.add(t)
        g_new_c.add(t)
    for t in only_old:
        g_old_c.add(t)
    for t in only_new:
        g_new_c.add(t)
    rem = by_subject(only_old)   # 仅在旧版（removed 三元组）
    add = by_subject(only_new)   # 仅在新版（added 三元组）
    # 构件级聚焦具名构件（URIRef）；匿名 bnode 公理单列计数（规范化启发式可能有噪声）
    old_named = {s for s in by_subject(g_old_c) if isinstance(s, URIRef)}
    new_named = {s for s in by_subject(g_new_c) if isinstance(s, URIRef)}
    added_subj = sorted(new_named - old_named, key=lambda s: (local(s), str(s)))
    removed_subj = sorted(old_named - new_named, key=lambda s: (local(s), str(s)))
    changed_subj = sorted((old_named & new_named) & (set(rem) | set(add)), key=lambda s: (local(s), str(s)))
    bnode_changed = sum(1 for s in (set(rem) | set(add)) if not isinstance(s, URIRef))

    def entry(subj, g_ctx):
        return {
            "id": local(subj),
            "kind": kind_of(g_ctx, subj),
            "removed": sorted(fmt_po(p, o) for p, o in rem.get(subj, set())),
            "added": sorted(fmt_po(p, o) for p, o in add.get(subj, set())),
        }

    detail = {
        "added_subjects": [entry(s, g_new_c) for s in added_subj],
        "removed_subjects": [entry(s, g_old_c) for s in removed_subj],
        "changed_subjects": [entry(s, g_new_c) for s in changed_subj],
    }
    kinds = ("class", "property", "rule", "concept", "other")
    kind_count = {k: {"added": 0, "removed": 0, "changed": 0} for k in kinds}
    for cat, key in (("added_subjects", "added"), ("removed_subjects", "removed"),
                     ("changed_subjects", "changed")):
        for e in detail[cat]:
            kind_count[e["kind"]][key] += 1
    return {
        "meta": {"old": os.path.basename(old_path), "new": os.path.basename(new_path),
                 "tool": "diff_ontology.py v1.0",
                 "bnode_note": "构件级以具名构件（URIRef）为准；匿名 bnode 公理单列计数，"
                               "graph_diff 规范化启发式对复杂匿名公理可能有噪声"},
        "counts": {
            "added_triples": len(only_new), "removed_triples": len(only_old),
            "common_triples": len(both),
            "added_subjects": len(added_subj), "removed_subjects": len(removed_subj),
            "changed_subjects": len(changed_subj),
            "bnode_subjects_changed": bnode_changed,
        },
        "kind_count": kind_count,
        "detail": detail,
    }


def to_md(d):
    c = d["counts"]
    lines = ["# 本体版本修订对照表（机械 diff 草稿）", "",
             "> %s → %s ｜ 三元组级（rdflib.compare.graph_diff，bnode 安全）"
             % (d["meta"]["old"], d["meta"]["new"]),
             "> 人工只裁定不比对；计数为机械实测（单一事实源）。", "",
             "## 计数概览", "",
             "| 项 | 数 |", "|---|---|",
             "| 新增三元组 | %d |" % c["added_triples"],
             "| 删除三元组 | %d |" % c["removed_triples"],
             "| 共有三元组 | %d |" % c["common_triples"],
             "| 新增构件 | %d |" % c["added_subjects"],
             "| 删除构件 | %d |" % c["removed_subjects"],
             "| 变更构件 | %d |" % c["changed_subjects"], "",
             "## 四面分布", "",
             "| 面 | 新增 | 删除 | 变更 |", "|---|---|---|---|"]
    for k in ("class", "property", "rule", "concept", "other"):
        kc = d["kind_count"][k]
        lines.append("| %s | %d | %d | %d |" % (k, kc["added"], kc["removed"], kc["changed"]))
    for cat, title in (("added_subjects", "新增构件"), ("removed_subjects", "删除构件"),
                       ("changed_subjects", "变更构件")):
        items = d["detail"][cat]
        lines += ["", "## %s（%d）" % (title, len(items)), ""]
        if not items:
            lines.append("（无）")
            continue
        lines += ["| 构件 | 面 | 删除三元组 | 新增三元组 |", "|---|---|---|---|"]
        for e in items:
            lines.append("| %s | %s | %s | %s |" % (
                e["id"], e["kind"],
                "<br>".join(e["removed"]) or "—",
                "<br>".join(e["added"]) or "—"))
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--json-output", default=None)
    ap.add_argument("--md-output", default=None)
    args = ap.parse_args()
    for p in (args.old, args.new):
        if not os.path.exists(p):
            sys.stderr.write("exit 2: 文件不存在 %s" % p + "\n"); sys.exit(2)
    try:
        d = diff(args.old, args.new)
    except Exception as exc:
        sys.stderr.write("exit 2: TTL 解析失败 %s" % exc + "\n"); sys.exit(2)
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
    if args.md_output:
        with open(args.md_output, "w", encoding="utf-8") as fh:
            fh.write(to_md(d))
    print(json.dumps(d["counts"], ensure_ascii=False))
    if not args.json_output and not args.md_output:
        print(to_md(d))


if __name__ == "__main__":
    main()
