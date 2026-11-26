#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ingest_opinions.py —— 页面导出的审阅意见.json → 审阅意见单.md（人读消费格式）。

忠实转录纪律（tpl-opinion-schema §四）：不改写、不概括、不合并。
severity → 回流通道映射（严重/重要→入口 (c) 候选；建议→下轮 G1/S2）。

用法：python3 ingest_opinions.py <审阅意见.json> [--output 审阅意见单.md]
exit 0 成功；1 无意见/格式错；2 参数错。
"""
import argparse
import json
import os
import sys

SEV_ORDER = ["严重", "重要", "建议"]
CHANNEL = {
    "严重": "入口 (c)（本轮重编译：generator 修订→机械校验→审计）",
    "重要": "入口 (c) 或下轮 G1/S2（按修订成本裁量）",
    "建议": "下轮 G1/S2 消费（下次 run 修订）",
}
KIND_CN = {
    "class": "类", "object_property": "对象属性", "data_property": "数据属性",
    "axiom": "公理", "rule": "推导规则", "skos": "术语",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("opinions_json")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    if not os.path.exists(args.opinions_json):
        sys.stderr.write("exit 2: 意见 JSON 不存在" + "\n"); sys.exit(2)

    with open(args.opinions_json, encoding="utf-8") as fh:
        data = json.load(fh)
    opinions = data.get("opinions", [])
    if not isinstance(opinions, list) or not opinions:
        sys.stderr.write("exit 1: 无意见条目（opinions 为空）" + "\n"); sys.exit(1)

    baseline = data.get("baseline", {})
    ttl_sha = (baseline.get("ttl") or {}).get("sha", "未知")
    export_date = (data.get("export_date", "") or "")[:19].replace("T", " ")

    lines = []
    lines.append("# 审阅意见单")
    lines.append("")
    lines.append("> 生成：ingest_opinions.py（忠实转录，无改写）")
    lines.append("> 导出时间：%s ｜ 本体基线：ontology.ttl sha=%s" % (export_date, ttl_sha))
    lines.append("> 意见条数：%d（严重 %d / 重要 %d / 建议 %d）" % (
        len(opinions),
        sum(1 for o in opinions if o.get("severity") == "严重"),
        sum(1 for o in opinions if o.get("severity") == "重要"),
        sum(1 for o in opinions if o.get("severity") == "建议")))
    lines.append("> 消费契约：`assets/tpl-opinion-schema.md`（通道映射 §二）")
    lines.append("")

    for sev in SEV_ORDER:
        group = [o for o in opinions if o.get("severity") == sev]
        if not group:
            continue
        lines.append("## %s（%d 条）——建议通道：%s" % (sev, len(group), CHANNEL[sev]))
        lines.append("")
        for o in group:
            kind = KIND_CN.get(o.get("kind"), o.get("kind", "?"))
            locate = o.get("locate") or ""
            lines.append("### [%s] %s（%s%s）" % (
                kind, o.get("label") or o.get("id"), o.get("id", ""),
                " · " + locate if locate else ""))
            lines.append("")
            lines.append("**意见**：%s" % o.get("opinion", ""))
            if o.get("suggest"):
                lines.append("")
                lines.append("**建议修改**：%s" % o["suggest"])
            ts = (o.get("ts") or "")[:19].replace("T", " ")
            if ts:
                lines.append("")
                lines.append("<small>提交：%s</small>" % ts)
            lines.append("")

    lines.append("## 意见 JSON（机械消费源，防转录漂移）")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(opinions, ensure_ascii=False, indent=1))
    lines.append("```")

    out = args.output or os.path.join(
        os.path.dirname(os.path.abspath(args.opinions_json)), "审阅意见单.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("审阅意见单 →", out)
    print("条数：", len(opinions))


if __name__ == "__main__":
    main()
