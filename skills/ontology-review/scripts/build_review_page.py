#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_review_page.py —— review.json → 单文件审阅页 HTML（离线可用）。

注入：数据 JSON + cytoscape/dagre/cytoscape-dagre 三个 vendor 库（全部内嵌）。
产物：run 目录下 `审阅页.html`（专家浏览器直接打开，零网络依赖）。

用法：python3 build_review_page.py <review.json> [--run-name 名] [--output 路径]
exit 0 成功；1 失败；2 参数错。
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
TEMPLATE = os.path.join(ASSETS, "review-page-template.html")
VENDORS = {
    "__CYTOSCAPE_JS__": "vendor-cytoscape.min.js",
    "__DAGRE_JS__": "vendor-dagre.min.js",
    "__CYTOSCAPE_DAGRE_JS__": "vendor-cytoscape-dagre.js",
}


def read(path, binary=False):
    with open(path, "rb" if binary else "r", encoding=None if binary else "utf-8") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("review_json")
    ap.add_argument("--run-name", default=None)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    if not os.path.exists(args.review_json):
        sys.stderr.write("exit 2: review.json 不存在" + "\n"); sys.exit(2)
    data = json.loads(read(args.review_json))

    run_name = args.run_name
    if not run_name:
        run_dir = data.get("meta", {}).get("run_dir", "")
        run_name = os.path.basename(run_dir.rstrip("/")) or "本体审阅"

    html = read(TEMPLATE)
    # 数据先注入（</script> 破坏防护：`</` → `<\/`，JS 字符串语义不变）
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace("__DATA_JSON__", data_json)
    # vendor 注入
    for token, fname in VENDORS.items():
        vpath = os.path.join(ASSETS, fname)
        if not os.path.exists(vpath):
            sys.stderr.write("exit 1: vendor 缺失 %s" % vpath + "\n"); sys.exit(1)
        html = html.replace(token, read(vpath))
    html = html.replace("__RUN_NAME__", run_name.replace("<", "&lt;"))

    out = args.output or os.path.join(
        os.path.dirname(os.path.abspath(args.review_json)), "审阅页.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("审阅页 →", out, "（%.1f MB）" % (os.path.getsize(out) / 1048576))


if __name__ == "__main__":
    main()
