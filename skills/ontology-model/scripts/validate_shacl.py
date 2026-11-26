#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_shacl.py —— R4 SHACL 实例级数据完整性校验器（pyshacl 引擎）。

定位
----
data.ttl（实例数据）+ shapes.ttl（derive_shacl 派生的验证契约）→ 违规看板。
SHACL（封闭世界数据完整性）补 OWL（开放世界逻辑一致性）盲区：承接限制⑩下 Pellet
剥离 facet 后推理器侧永不校验的实例级 facet/基数/唯一性。与 check_instance 正交互补
（check_instance=签名词汇表封闭防臆造/越权/类型错；本脚本=数据完整性 facet/基数/键）。
纯 Python 无 Java（skip-java 环境也可跑）。是 R6 实例化管道前置地基。

T3 组合（编排器职责，非本脚本内）：
  check_instance（JSON 零臆造闸门）→ compile_instance_ttl → validate_shacl（数据完整性
  闸门）→ simulate_reason（物化推理）。三闸正交，缺一不可。

纪律
----
- 每次从文件 fresh parse data/shapes（pyshacl.validate 会篡改 shapes 图注入 owl 公理，
  复用已消费图破坏确定性——实证 2026-11-17；本脚本天然每调用 fresh parse）。
- advanced=True 显式（不依赖 0.29.1 的 advanced=False 行为）；inference=None（输入侧
  断言数据口径，owlrl/rdfs 备选登记不启用——R-c 子类闭包已在派生侧机械展开）。
- 零回写：只读 data/shapes，输出落 --json-output 指定路径（默认不落盘）。
- 确定性：results 排序 (focus,path,component,message)；report 无时间戳。
- 纯 rdflib+pyshacl：顶层 import pyshacl（try/except ImportError→exit 2 pip 指引）；
  不 import simulate_reason（顶层 owlready2）；local_name 只读复用 validate_ontology。

退出码：0=无 error（非 strict 下 warning/info 放行）/ 1=有 error（strict 下 warning 也
  致 1）/ 2=输入错（文件缺失/TTL 解析失败/pyshacl 缺失）。

用法：
  python3 validate_shacl.py <data.ttl> <shapes.ttl> [--json-output FILE]
      [--derivation-report FILE] [--strict] [--focus IRI]
"""
import argparse
import hashlib
import json
import os
import sys

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

try:
    import pyshacl
except ImportError:
    sys.stderr.write(
        "exit 2: 缺少 pyshacl（R4 SHACL 校验核心依赖）。安装：pip install pyshacl==0.29.1\n")
    sys.exit(2)

from validate_ontology import local_name
from _common import file_sha256

SH = pyshacl.consts.SH
REPORT_SCHEMA_VERSION = "1.0"


def load_graph(path, label):
    if not os.path.exists(path):
        sys.stderr.write("exit 2: %s 文件不存在：%s\n" % (label, path))
        sys.exit(2)
    g = Graph()
    try:
        g.parse(path, format="turtle")
    except Exception as exc:
        sys.stderr.write("exit 2: %s TTL 解析失败（%s）：%s\n" % (label, path, exc))
        sys.exit(2)
    return g


def run_validation(data, shapes, strict, focus):
    """pyshacl 校验。allow_warnings=not strict（非 strict 放行 warning）；allow_infos=True
    （info 永不致失败）；advanced=True/inference=None/inplace=False 显式。"""
    conforms, rg, _text = pyshacl.validate(
        data,
        shacl_graph=shapes,
        advanced=True,
        inference=None,
        inplace=False,
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=not strict,
        focus_nodes=[focus] if focus else None,
    )
    return bool(conforms), rg


def parse_results(rg):
    """遍历 sh:ValidationResult → 结构化违规条目，确定性排序。"""
    out = []
    for res in rg.subjects(RDF.type, SH.ValidationResult):
        focus = rg.value(res, SH.focusNode)
        path = rg.value(res, SH.resultPath)
        shape = rg.value(res, SH.sourceShape)
        comp = rg.value(res, SH.sourceConstraintComponent)
        value = rg.value(res, SH.value)
        msg = rg.value(res, SH.resultMessage)
        sev = rg.value(res, SH.resultSeverity)
        sev_str = str(sev) if sev is not None else str(SH.Violation)
        if sev_str == str(SH.Warning):
            severity = "warning"
        elif sev_str == str(SH.Info):
            severity = "info"
        else:
            severity = "error"
        out.append({
            "focus_node": str(focus) if focus is not None else None,
            "result_path": str(path) if path is not None else None,
            "source_shape": str(shape) if shape is not None else None,
            "constraint_component": local_name(comp) if comp is not None else None,
            "value": str(value) if value is not None else None,
            "message": str(msg) if msg is not None else None,
            "severity": severity,
        })
    out.sort(key=lambda r: (r["focus_node"] or "", r["result_path"] or "",
                            r["constraint_component"] or "", r["message"] or ""))
    return out


def join_provenance(results, derivation_report):
    """可选溯源：sourceShape → derivation-report.mapped → 源句编号。
    best-effort：sh:sparql/qualifiedValueShape 的 sourceShape 为 bnode 时可能 miss
    （mapped 以具名 shape IRI 为键），不阻断校验。"""
    shape_map = {}
    for m in derivation_report.get("mapped", []):
        shape_map.setdefault(m["shape"], set()).update(m.get("provenance", []))
    for r in results:
        ss = r.get("source_shape")
        if ss and ss in shape_map:
            r["source_sentences"] = sorted(shape_map[ss])
    return results


def build_report(data_path, shapes_path, shapes_sha, conforms, results, strict):
    counts = {"error": 0, "warning": 0, "info": 0, "total": len(results)}
    for r in results:
        counts[r["severity"]] += 1
    passed = bool(conforms) if strict else (counts["error"] == 0)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "data": os.path.basename(data_path),
        "shapes": os.path.basename(shapes_path),
        "shapes_sha256": shapes_sha,
        "conforms": bool(conforms),
        "pass": passed,
        "strict": bool(strict),
        "results": results,
        "counts": counts,
    }


def main():
    ap = argparse.ArgumentParser(description="R4 SHACL 实例级数据完整性校验器（pyshacl）")
    ap.add_argument("data", help="实例数据 TTL")
    ap.add_argument("shapes", help="SHACL shapes TTL（derive_shacl 派生）")
    ap.add_argument("--json-output", default=None, help="violations-report.json 输出路径")
    ap.add_argument("--derivation-report", default=None,
                    help="derive_shacl 的 derivation-report.json（可选溯源挂源句）")
    ap.add_argument("--strict", action="store_true", help="warning 也致 exit 1")
    ap.add_argument("--focus", default=None, help="只校验指定 focus node IRI")
    args = ap.parse_args()

    data = load_graph(args.data, "data")
    shapes = load_graph(args.shapes, "shapes")
    shapes_sha = file_sha256(args.shapes)

    conforms, rg = run_validation(data, shapes, args.strict, args.focus)
    results = parse_results(rg)

    if args.derivation_report:
        if not os.path.exists(args.derivation_report):
            sys.stderr.write("exit 2: derivation-report 不存在：%s\n" % args.derivation_report)
            sys.exit(2)
        with open(args.derivation_report, encoding="utf-8") as fh:
            try:
                dreport = json.load(fh)
            except Exception as exc:
                sys.stderr.write("exit 2: derivation-report JSON 解析失败：%s\n" % exc)
                sys.exit(2)
        results = join_provenance(results, dreport)

    report = build_report(args.data, args.shapes, shapes_sha, conforms, results, args.strict)

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")

    c = report["counts"]
    print("校验结果：%s（error %d / warning %d / info %d / 违规 %d）" % (
        "通过" if report["pass"] else "不通过",
        c["error"], c["warning"], c["info"], c["total"]))
    for r in results:
        tag = {"error": "error", "warning": "warn ", "info": "info "}[r["severity"]]
        line = "  [%s %s] %s" % (tag, r["constraint_component"], r["message"])
        if r.get("source_sentences"):
            line += "（源句 %s）" % ",".join(r["source_sentences"])
        print(line)

    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
