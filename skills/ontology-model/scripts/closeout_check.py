#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""closeout_check.py — ontology-model skill 收卷自查脚本

一命令出收卷自查报告：齐套核对 + 敏感模式扫描 + 计数一致性 + 净化清单。

用法:
  python3 closeout_check.py RUN_DIR [--patterns FILE] [--report FILE] [--json-output FILE]

检查项:
  1. 齐套核对   8 件套=交付物/ 下 7 件（文件名前缀模糊匹配，容忍版本后缀如
                「测试报告_v1.5.md」）+ 根级 run-manifest.md；缺件=FAIL。
                交付物/ 不存在时回退扫根级平铺（旧 run 布局兼容）并 WARN。
  2. 敏感扫描   扫描面=对外消费面（交付物/ 全部 + 根级 md/ttl/txt/json +
                过程/02 闸门/）。内置泛化模式（手机号/18 位证件号）零命中；
                真实机构名/人名等词表**外置**经 --patterns 传入——词表本身
                不入 skill 资产（sensitivity-rules 敏感纪律）。
                命中只报 文件+行号+模式名，不回显命中原文（防报告二次泄露）。
  3. 计数一致   rdflib 实测 ontology.ttl 构件计数（唯一机械权威）vs
                测试报告/manifest 中「N 类/N 规则…」提取值——不一致 WARN
                （可能是历史版本计数，需人工判别是否手抄漂移）。
                rdflib 不可用→本项降级跳过（WARN，不阻塞）。
  4. 净化清单   根级散落文件（manifest 之外）/ 交付物区混入实验副本
                （*exp* / *_v<X.Y>* 命名）→ 列出建议归置动作（WARN 清单，
                收卷三步之「净化」的机械底稿）。

外置词表格式（--patterns FILE，TAB 分隔，# 注释与空行忽略）:
  ban<TAB>regex            命中即 FAIL（零命中型）
  limit<TAB>regex<TAB>N    命中行数 > N 才 FAIL（计数基线型，只减不增口径）

exit: 0=通过（允许 WARN）/ 1=存在 FAIL / 2=参数或环境错误
"""

import argparse
import json
import os
import re
import sys
from datetime import date

# ---------- 常量 ----------

# (文件名前缀, 扩展名, 标准名) —— 8 件套中落交付物/ 的 7 件
DELIVERABLES = [
    ("ontology", ".ttl", "ontology.ttl"),
    ("建模方案", ".md", "建模方案.md"),
    ("29句话", ".md", "29句话描述集.md"),
    ("术语词典", ".md", "术语词典.md"),
    ("缺陷报告", ".md", "缺陷报告.md"),
    ("黄金用例", ".md", "黄金用例集.md"),
    ("测试报告", ".md", "测试报告.md"),
]
MANIFEST_NAME = "run-manifest.md"

# 内置泛化敏感模式（不含任何真实业务词表——真实名单走 --patterns 外置）
BUILTIN_PATTERNS = [
    ("手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("证件号18位", re.compile(
        r"(?<!\d)\d{6}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])"
        r"(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")),
]

SCAN_EXT = {".md", ".ttl", ".txt", ".json"}

# 实验/历史副本命名特征（净化清单判据）
EXP_NAME_RE = re.compile(r"(exp|实验|_v\d|削减)", re.IGNORECASE)

# 计数词 → 实测键 映射（计数一致性提取用）
COUNT_TERMS = {
    "类": "classes",
    "对象属性": "object_properties",
    "数据属性": "datatype_properties",
    "swrl:Imp": "rules",
    "Imp": "rules",
    "规则": "rules",
    "Concept": "concepts",
    "概念": "concepts",
}
COUNT_EXTRACT_RE = re.compile(
    r"(\d{1,6})\s*(?:个|条|张)?\s*(swrl:Imp|Imp|对象属性|数据属性|类|规则|Concept|概念)"
)


# ---------- 结果收集 ----------

class Results(object):
    def __init__(self):
        self.fail = []
        self.warn = []
        self.info = []

    def add_fail(self, check, detail):
        self.fail.append({"check": check, "detail": detail})

    def add_warn(self, check, detail):
        self.warn.append({"check": check, "detail": detail})

    def add_info(self, check, detail):
        self.info.append({"check": check, "detail": detail})


# ---------- 工具 ----------

def is_scanable(name):
    return os.path.splitext(name)[1].lower() in SCAN_EXT


def is_deliverable_candidate(name, prefix, ext):
    """模糊匹配交付物文件名，排除实验/历史副本命名。"""
    if not (name.startswith(prefix) and name.lower().endswith(ext)):
        return False
    return not EXP_NAME_RE.search(name)


def load_patterns(path, results):
    """解析外置敏感词表；格式错行→收集为环境错误（调用方据此 exit 2）。"""
    rules = []
    errors = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (IOError, OSError) as e:
        return None, ["词表文件不可读: %s" % e]
    for ln, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        mode = parts[0].strip()
        if mode == "ban" and len(parts) >= 2:
            try:
                rules.append(("ban", re.compile(parts[1]), None))
            except re.error as e:
                errors.append("词表 L%d regex 非法: %s" % (ln, e))
        elif mode == "limit" and len(parts) >= 3:
            try:
                rules.append(("limit", re.compile(parts[1]), int(parts[2])))
            except (re.error, ValueError) as e:
                errors.append("词表 L%d 非法: %s" % (ln, e))
        else:
            errors.append("词表 L%d 格式错（须 TAB 分隔 ban/limit 规则）" % ln)
    return rules, errors


# ---------- 检查 1：齐套核对 ----------

def check_completeness(run_dir, results):
    """返回 (交付物目录或 None, 找到的交付物文件列表)。"""
    deliv_dir = os.path.join(run_dir, "交付物")
    flat_mode = False
    if os.path.isdir(deliv_dir):
        files = [f for f in os.listdir(deliv_dir) if os.path.isfile(os.path.join(deliv_dir, f))]
    else:
        flat_mode = True
        deliv_dir = run_dir
        files = [f for f in os.listdir(run_dir) if os.path.isfile(os.path.join(run_dir, f))]
        results.add_warn("齐套核对",
                         "未检测到 交付物/ 目录——回退根级平铺扫描（旧 run 布局）；"
                         "收卷前应按 SKILL.md S0 三区结构归置")

    # manifest：根级优先，平铺模式容忍同名
    manifest_ok = os.path.isfile(os.path.join(run_dir, MANIFEST_NAME))
    if not manifest_ok:
        results.add_fail("齐套核对", "缺 run-manifest.md（根级）")
    else:
        results.add_info("齐套核对", "run-manifest.md ✓")

    found = []
    for prefix, ext, std in DELIVERABLES:
        cand = [f for f in files if is_deliverable_candidate(f, prefix, ext)]
        if cand:
            found.append((std, cand[0]))
            results.add_info("齐套核对", "%s ✓（%s）" % (std, cand[0]))
        else:
            results.add_fail("齐套核对", "缺交付物：%s（前缀「%s」%s 未命中）" % (std, prefix, ext))
    return deliv_dir, found, flat_mode


# ---------- 检查 2：敏感模式扫描 ----------

def collect_scan_files(run_dir, deliv_dir, flat_mode):
    targets = []
    if not flat_mode:
        for root, _dirs, fnames in os.walk(deliv_dir):
            for f in fnames:
                if is_scanable(f):
                    targets.append(os.path.join(root, f))
        gate_dir = os.path.join(run_dir, "过程", "02 闸门")
        if os.path.isdir(gate_dir):
            for root, _dirs, fnames in os.walk(gate_dir):
                for f in fnames:
                    if is_scanable(f):
                        targets.append(os.path.join(root, f))
    # 根级文件（含平铺模式全部可扫文件）
    for f in os.listdir(run_dir):
        p = os.path.join(run_dir, f)
        if os.path.isfile(p) and is_scanable(f):
            targets.append(p)
    # 去重保持顺序
    seen, out = set(), []
    for p in targets:
        rp = os.path.realpath(p)
        if rp not in seen:
            seen.add(rp)
            out.append(p)
    return out


def check_sensitive(scan_files, ext_rules, results):
    hits = 0
    for path in scan_files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except (IOError, OSError):
            results.add_warn("敏感扫描", "文件不可读，跳过：%s" % path)
            continue
        limit_counts = {}  # (pattern_str) -> [count, baseline]
        for ln, line in enumerate(lines, 1):
            for name, rx in BUILTIN_PATTERNS:
                if rx.search(line):
                    hits += 1
                    results.add_fail("敏感扫描",
                                     "内置模式「%s」命中：%s L%d（原文不回显，就地脱敏后复扫）"
                                     % (name, path, ln))
            for mode, rx, baseline in (ext_rules or []):
                if rx.search(line):
                    if mode == "ban":
                        hits += 1
                        results.add_fail("敏感扫描",
                                         "外置 ban 模式命中：%s L%d（就地脱敏后复扫）" % (path, ln))
                    else:
                        key = rx.pattern
                        if key not in limit_counts:
                            limit_counts[key] = [0, baseline, path]
                        limit_counts[key][0] += 1
        for key, (cnt, baseline, path) in limit_counts.items():
            if cnt > baseline:
                hits += 1
                results.add_fail("敏感扫描",
                                 "外置 limit 模式超基线：%s 命中 %d 行 > 基线 %d（只减不增口径）"
                                 % (path, cnt, baseline))
            else:
                results.add_info("敏感扫描",
                                 "limit 模式达标：%s 命中 %d 行 ≤ 基线 %d" % (path, cnt, baseline))
    if hits == 0:
        results.add_info("敏感扫描", "扫描 %d 个文件，零 FAIL 命中" % len(scan_files))
    return hits


# ---------- 检查 3：计数一致性 ----------

def measure_ttl(ttl_path):
    from rdflib import Graph, URIRef
    from rdflib.namespace import OWL, RDF, SKOS
    g = Graph()
    g.parse(ttl_path, format="turtle")
    swrl_imp = URIRef("http://www.w3.org/2003/11/swrl#Imp")

    def named(pred_type, obj):
        return len(set(s for s in g.subjects(pred_type, obj) if isinstance(s, URIRef)))

    return {
        "classes": named(RDF.type, OWL.Class),
        "object_properties": named(RDF.type, OWL.ObjectProperty),
        "datatype_properties": named(RDF.type, OWL.DatatypeProperty),
        "rules": named(RDF.type, swrl_imp),
        "concepts": named(RDF.type, SKOS.Concept),
        "triples": len(g),
    }


def check_counts(run_dir, found, results):
    ttl = None
    for std, fname in found:
        if std == "ontology.ttl":
            ttl = os.path.join(run_dir, "交付物", fname)
            if not os.path.isfile(ttl):
                ttl = os.path.join(run_dir, fname)
            break
    if ttl is None:
        results.add_warn("计数一致", "交付物中无 ontology.ttl，跳过计数核对")
        return None
    try:
        measured = measure_ttl(ttl)
    except ImportError:
        results.add_warn("计数一致", "rdflib 不可用——计数核对降级跳过（不阻塞收卷）")
        return None
    except Exception as e:  # 解析失败本身是 L1 职责，这里只登记
        results.add_warn("计数一致", "TTL 解析失败，跳过计数核对：%s" % e)
        return None

    results.add_info("计数一致",
                     "机械实测（唯一权威）：类 %d / 对象属性 %d / 数据属性 %d / 规则 %d / "
                     "Concept %d / 三元组 %d"
                     % (measured["classes"], measured["object_properties"],
                        measured["datatype_properties"], measured["rules"],
                        measured["concepts"], measured["triples"]))

    # 提取比对：测试报告 + manifest（单一事实源纪律的机械兜底）
    docs = []
    for std, fname in found:
        if std in ("测试报告.md",):
            for cand in (os.path.join(run_dir, "交付物", fname), os.path.join(run_dir, fname)):
                if os.path.isfile(cand):
                    docs.append(cand)
                    break
    manifest = os.path.join(run_dir, MANIFEST_NAME)
    if os.path.isfile(manifest):
        docs.append(manifest)

    mismatch = 0
    for doc in docs:
        with open(doc, "r", encoding="utf-8", errors="ignore") as f:
            for ln, line in enumerate(f.readlines(), 1):
                for num_s, term in COUNT_EXTRACT_RE.findall(line):
                    key = COUNT_TERMS.get(term)
                    if key is None:
                        continue
                    val = int(num_s)
                    if val != measured[key] and val > 0:
                        mismatch += 1
                        results.add_warn(
                            "计数一致",
                            "%s L%d 出现「%s %s」≠ 机械实测 %d——人工判别：历史版本计数可豁免，"
                            "手抄漂移须改为引用建模方案计数登记节"
                            % (os.path.basename(doc), ln, num_s, term, measured[key]))
    if mismatch == 0:
        results.add_info("计数一致", "文档提取值与机械实测无冲突（或无提取命中）")
    return measured


# ---------- 检查 4：净化清单 ----------

def check_purge(run_dir, deliv_dir, flat_mode, results):
    purge = []
    # 根级散落（manifest 之外）
    for f in sorted(os.listdir(run_dir)):
        p = os.path.join(run_dir, f)
        if not os.path.isfile(p) or f == MANIFEST_NAME:
            continue
        if EXP_NAME_RE.search(f):
            purge.append((p, "实验/", "实验/调试产物，移入 实验/（登记可再生性）"))
        elif is_scanable(f) or f.lower().endswith((".json", ".txt")):
            purge.append((p, "过程/", "根级散落过程文件，按内容归入 过程/01-05 对应子目录"))
    # 交付物区混入实验/历史副本
    if not flat_mode and os.path.isdir(deliv_dir):
        for root, _dirs, fnames in os.walk(deliv_dir):
            for f in sorted(fnames):
                if EXP_NAME_RE.search(f):
                    purge.append((os.path.join(root, f), "实验/ 或 archive/",
                                  "交付物区禁入实验/版本副本——移入 实验/ 或 archive/"))
    for p, dest, why in purge:
        results.add_warn("净化清单", "%s → %s（%s）" % (os.path.relpath(p, run_dir), dest, why))
    if not purge:
        results.add_info("净化清单", "无待净化项")
    return [{"file": os.path.relpath(p, run_dir), "dest": d, "reason": w} for p, d, w in purge]


# ---------- 报告 ----------

def render_report(run_dir, results, measured, purge, exit_code):
    lines = [
        "# 收卷自查报告（closeout_check.py）",
        "",
        "> run 目录：`%s`" % run_dir,
        "> 日期：%s ｜ 结论：**%s**（FAIL %d / WARN %d）"
        % (date.today().isoformat(),
           "✅ 通过" if exit_code == 0 else "❌ 存在 FAIL",
           len(results.fail), len(results.warn)),
        "",
    ]
    for title, items in (("FAIL（须处置后复扫）", results.fail),
                         ("WARN（登记/人工复核）", results.warn),
                         ("INFO", results.info)):
        lines.append("## %s — %d 项" % (title, len(items)))
        if not items:
            lines.append("（无）")
        for it in items:
            lines.append("- **[%s]** %s" % (it["check"], it["detail"]))
        lines.append("")
    if measured:
        lines.append("## 构件计数（机械实测=唯一权威）")
        lines.append("")
        lines.append("| 构件 | 计数 |")
        lines.append("|---|---|")
        label = {"classes": "类", "object_properties": "对象属性",
                 "datatype_properties": "数据属性", "rules": "规则(swrl:Imp)",
                 "concepts": "Concept", "triples": "三元组"}
        for k in ("classes", "object_properties", "datatype_properties",
                  "rules", "concepts", "triples"):
            lines.append("| %s | %d |" % (label[k], measured[k]))
        lines.append("")
        lines.append("> 建模方案计数登记节须与本表一致；其余文档引用不手抄（单一事实源纪律）。")
        lines.append("")
    lines.append("## 净化清单（收卷三步之①的机械底稿）")
    lines.append("")
    if purge:
        lines.append("| 文件 | 建议去向 | 理由 |")
        lines.append("|---|---|---|")
        for it in purge:
            lines.append("| `%s` | %s | %s |" % (it["file"], it["dest"], it["reason"]))
    else:
        lines.append("（无待净化项）")
    lines.append("")
    return "\n".join(lines)


# ---------- 主流程 ----------

def main(argv=None):
    ap = argparse.ArgumentParser(description="ontology-model 收卷自查（M1）")
    ap.add_argument("run_dir", help="run 目录路径")
    ap.add_argument("--patterns", help="外置敏感词表文件（TAB 分隔 ban/limit 规则）")
    ap.add_argument("--report", help="报告输出路径（默认 RUN_DIR/closeout_report.md）")
    ap.add_argument("--json-output", help="JSON 结果输出路径（可选）")
    args = ap.parse_args(argv)

    run_dir = args.run_dir.rstrip("/")
    if not os.path.isdir(run_dir):
        sys.stderr.write("[closeout] run 目录不存在: %s\n" % run_dir)
        return 2

    results = Results()
    ext_rules = []
    if args.patterns:
        ext_rules, errors = load_patterns(args.patterns, results)
        if errors:
            for e in errors:
                sys.stderr.write("[closeout] %s\n" % e)
            return 2

    deliv_dir, found, flat_mode = check_completeness(run_dir, results)
    scan_files = collect_scan_files(run_dir, deliv_dir, flat_mode)
    check_sensitive(scan_files, ext_rules, results)
    measured = check_counts(run_dir, found, results)
    purge = check_purge(run_dir, deliv_dir, flat_mode, results)

    exit_code = 1 if results.fail else 0
    report_path = args.report or os.path.join(run_dir, "closeout_report.md")
    report = render_report(run_dir, results, measured, purge, exit_code)
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
    except (IOError, OSError) as e:
        sys.stderr.write("[closeout] 报告写入失败: %s\n" % e)
        return 2

    if args.json_output:
        payload = {
            "run_dir": run_dir, "date": date.today().isoformat(),
            "exit_code": exit_code, "fail": results.fail,
            "warn": results.warn, "info": results.info,
            "counts": measured, "purge_list": purge,
            "report": report_path,
        }
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    sys.stdout.write(report)
    sys.stdout.write("\n[closeout] exit=%d（0=通过 1=FAIL 2=环境错）\n" % exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
