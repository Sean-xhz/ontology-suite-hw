#!/usr/bin/env python3
"""ontology-suite 统一 CLI 入口 —— 四件套机械能力的薄分发门面。

定位
----
本 CLI 是**机械 backbone 的统一命令面**，把四件套（ontology-ingest / ontology-model /
ontology-review / ontology-simulate）的确定性机械脚本聚合为一个 cohesive 入口。LLM 编排层
（I0-I3 / S0-S6 管线、IG1 / G1-G3 / SG1-SG2 / AG1-AG2 人工闸门、双模型生成-审计、vision 识图）
**不在本 CLI 内**——它由外部编排器承担（Claude Code skills 或其他平台），本 CLI 只暴露可独立
运行的机械能力。

设计纪律
--------
- **薄分发，零行为改变**：每个子命令把剩余参数原样转发给底层脚本（subprocess），
  保留各脚本自身的 argparse / 输出 / 退出码。脚本仍可独立运行，本 CLI 只是便利门面。
- **部署形态**：本文件随套件分发（`scripts/ontology_cli.py`），按套件布局
  （`skills/<skill>/scripts/`）解析底层脚本；脚本路径相对套件根（__file__ 自动定位），
  与调用时 cwd 无关。跨 skill import 由各脚本自身的相对 sys.path 垫片承接（四 skill 同级）。
- **只读自检**：`suite doctor` 只读探测环境，不安装不写盘。

用法
----
  python3 scripts/ontology_cli.py <group> <action> [args...]
  python3 scripts/ontology_cli.py --help            # 能力地图
  python3 scripts/ontology_cli.py model validate --help   # 转发到底层脚本的 --help
  python3 scripts/ontology_cli.py suite doctor      # 环境自检
  python3 scripts/ontology_cli.py suite test --skip-java  # 统一验收电池

group ∈ {ingest, model, review, simulate, suite}；各 action 见 --help 能力地图。
退出码：底层脚本退出码原样透传；未知 group/action 或脚本缺失 = 2。
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

__version__ = "1.5.0"

# 套件根 = 本文件所在 scripts/ 的上一级（__file__ 绝对定位，与 cwd 无关）
SUITE_ROOT = Path(__file__).resolve().parent.parent

# (group, action) -> (相对套件根的脚本路径, 一句话用途)
# 顺序即 --help 能力地图的呈现顺序。
DISPATCH = {
    ("ingest", "parse"): (
        "skills/ontology-ingest/scripts/parse_documents.py",
        "I1 机械层→准备态萃取原料包（渲染+inventory+substrate，无 LLM；I2 整页转录由 vision agent 外接），exit 0/1/2"),
    ("ingest", "assemble"): (
        "skills/ontology-ingest/scripts/assemble_pack.py",
        "I3 机械组装（每源件单一合并 md，按序/不丢弃/图嵌守恒 + 自校验门禁），exit 0/1/2"),
    ("model", "validate"): (
        "skills/ontology-model/scripts/validate_ontology.py",
        "L1+L2 机械校验（语法结构 + 语义启发式），exit 0/1/2"),
    ("model", "consistency"): (
        "skills/ontology-model/scripts/check_consistency.py",
        "L3 推理机一致性（Pellet/HermiT 三级降级链），exit 0/1/2"),
    ("model", "topology"): (
        "skills/ontology-model/scripts/report_topology.py",
        "S5 文本拓扑报告（类层级/属性/规则路径，可降级审图）"),
    ("model", "golden"): (
        "skills/ontology-model/scripts/run_golden_cases.py",
        "S6 黄金用例执行（实例级推理 + 失败归因），--check 仅 schema 校验"),
    ("model", "patch"): (
        "skills/ontology-model/scripts/incremental_patch.py",
        "R2 增量 patch（编辑操作→draft+L1/L2+回归守护+版本 diff，不覆盖权威），exit 0/1/2"),
    ("model", "shapes"): (
        "skills/ontology-model/scripts/derive_shacl.py",
        "R4 TTL→SHACL shapes 派生（TTL-direct，纯 rdflib），exit 0/1/2"),
    ("model", "shacl"): (
        "skills/ontology-model/scripts/validate_shacl.py",
        "R4 SHACL 实例级数据完整性校验（pyshacl，facet/基数/唯一性），exit 0/1/2"),
    ("model", "queries"): (
        "skills/ontology-model/scripts/derive_sparql.py",
        "D3c TTL-direct 派生 SPARQL Read 查询模板库（7 类 SELECT，纯 rdflib 内置 SPARQL），exit 0/1/2"),
    ("model", "diff"): (
        "skills/ontology-model/scripts/diff_ontology.py",
        "IT-07 两版本 TTL 三元组级机械 diff（具名构件 added/removed/changed + md 对照表），exit 0/2"),
    ("review", "extract"): (
        "skills/ontology-review/scripts/review_extract.py",
        "建模方案表 + TTL 双源提取 → review.json（TTL 权威）"),
    ("review", "page"): (
        "skills/ontology-review/scripts/build_review_page.py",
        "review.json → 单文件 HTML 审阅页（类图 + 规则双通道 + 批注 UI）"),
    ("review", "ingest"): (
        "skills/ontology-review/scripts/ingest_opinions.py",
        "专家批注 JSON → 审阅意见单（G1/S2 消费格式 + 入口(c) 同步位）"),
    ("review", "selftest"): (
        "skills/ontology-review/scripts/self_test.py",
        "审阅层自测电池 E1-E14（--runs/ONTOLOGY_SELFTEST_RUNS 显式传入）"),
    ("simulate", "signature"): (
        "skills/ontology-simulate/scripts/extract_signature.py",
        "TTL → 编译约束签名 signature.json（类/属性/受控值/规则面）"),
    ("simulate", "check"): (
        "skills/ontology-simulate/scripts/check_instance.py",
        "实例 JSON 机械校验 E01-E10（零臆造硬闸门），exit 0/1"),
    ("simulate", "reason"): (
        "skills/ontology-simulate/scripts/simulate_reason.py",
        "what-if 物化推理（双快照 diff + 规则归因 + canonical 缓存 + --render-md）"),
    ("simulate", "ab-score"): (
        "skills/ontology-simulate/scripts/ab_score.py",
        "A/B 三臂机械判据评分 + 专家盲评聚合"),
    ("suite", "test"): (
        "scripts/run_suite_tests.py",
        "统一验收电池 T0-T21（虚构示例 fixture，零副作用），exit 0/1/2"),
}

GROUPS = ("ingest", "model", "review", "simulate", "suite")


def print_help():
    print("ontology-suite 统一 CLI 入口 v%s —— 四件套机械能力门面" % __version__)
    print("")
    print("用法: python3 scripts/ontology_cli.py <group> <action> [args...]")
    print("      python3 scripts/ontology_cli.py <group> <action> --help  (底层脚本帮助)")
    print("")
    print("定位: 机械 backbone 统一命令面；LLM 编排（S0-S6/人工闸门/双模型）由外部编排器承担。")
    print("      薄分发——参数原样转发底层脚本，退出码透传，脚本行为零改变。")
    print("")
    print("能力地图:")
    for g in GROUPS:
        actions = [(a, v) for (gg, a), v in DISPATCH.items() if gg == g]
        if not actions:
            continue
        print("  [%s]" % g)
        for a, (rel, purpose) in actions:
            print("    %-12s %s" % (a, purpose))
        print("")
    print("  [suite] 额外命令:")
    print("    %-12s %s" % ("doctor", "只读环境自检（python/rdflib/owlready2/pyshacl/java/node/ingest 解析渲染库/LibreOffice）"))
    print("")
    print("示例:")
    print("    ontology_cli.py ingest parse 制度.docx 费率表.xlsx --output-dir 萃取原料包")
    print("    ontology_cli.py model validate examples/票据贴现/建模run/ontology.ttl")
    print("    ontology_cli.py model patch ontology.ttl patch.json --golden cases.json")
    print("    ontology_cli.py model shapes ontology.ttl --output-shapes shapes.ttl")
    print("    ontology_cli.py model shacl data.ttl shapes.ttl --strict")
    print("    ontology_cli.py review page --run-name 票据贴现")
    print("    ontology_cli.py simulate reason --instance inst.json --ttl ontology.ttl")
    print("    ontology_cli.py suite test --skip-java")
    print("")
    print("退出码: 底层脚本退出码透传；未知 group/action 或脚本缺失 = 2。")


def doctor():
    """只读环境自检——不安装不写盘。核心依赖缺失 exit 1，可选降级登记。"""
    print("ontology-suite 环境自检 (doctor) —— 只读，不安装不写盘")
    print("套件根: %s" % SUITE_ROOT)
    print("")
    ok = True

    # Python
    pv = sys.version.split()[0]
    py_ok = sys.version_info >= (3, 9)
    print("  [%s] python %s (要求 ≥3.9)" % ("OK" if py_ok else "FAIL", pv))
    ok = ok and py_ok

    # 核心 Python 依赖
    for mod in ("rdflib", "owlready2", "pyshacl"):
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "?")
            print("  [OK] %s %s" % (mod, ver))
        except ImportError:
            print("  [FAIL] %s 未安装 (pip install -r requirements.txt)" % mod)
            ok = False

    # Java（可选：L3 推理 / SWRL 物化；缺失降级 L2）
    java = shutil.which("java")
    if java:
        try:
            r = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=15)
            line = (r.stderr or r.stdout).strip().splitlines()[0]
            print("  [OK] java: %s" % line)
        except Exception as e:
            print("  [WARN] java 存在但版本探测失败: %s" % e)
    else:
        print("  [WARN] java 未找到 —— L3 一致性/SWRL 物化降级 L2（Pellet 需 ≥25，HermiT 需 ≥17）")

    # Node（可选：审阅页 self_test E9 语法检查；缺失 skip）
    node = shutil.which("node")
    if node:
        try:
            r = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=15)
            print("  [OK] node %s" % r.stdout.strip())
        except Exception as e:
            print("  [WARN] node 存在但版本探测失败: %s" % e)
    else:
        print("  [WARN] node 未找到 —— 审阅页 self_test E9 降级 skip")

    # ingest 解析/渲染库（可选：2.0 保真进料机械层；缺失 ingest parse 降级 exit2，不阻塞三件套）
    ingest_missing = []
    for mod in ("pypdf", "pypdfium2", "docx", "openpyxl", "pptx", "PIL"):
        try:
            __import__(mod)
        except ImportError:
            ingest_missing.append(mod)
    if ingest_missing:
        print("  [WARN] ingest 解析/渲染库未装: %s —— ingest parse 降级 exit2（pip install pypdf "
              "pypdfium2 python-docx openpyxl python-pptx Pillow），不阻塞 model/review/simulate"
              % ", ".join(ingest_missing))
    else:
        print("  [OK] ingest 解析/渲染库齐（pypdf/pypdfium2/python-docx/openpyxl/python-pptx/Pillow）")

    # LibreOffice（可选：office→PDF 全视觉渲染增强；缺失 office 退 substrate-only 纯 pip 主路径）
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice and os.path.isfile("/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        soffice = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if soffice:
        print("  [OK] LibreOffice: %s（office 全视觉渲染增强可用）" % soffice)
    else:
        print("  [WARN] LibreOffice 未找到 —— office（pptx/docx/xlsx）退 substrate-only（纯 pip 主路径仍工作；"
              "全视觉渲染增强需 brew install --cask libreoffice）")

    # 底层脚本就位检查
    print("")
    missing = [rel for rel, _ in DISPATCH.values() if not (SUITE_ROOT / rel).exists()]
    if missing:
        print("  [FAIL] %d 个底层脚本缺失:" % len(missing))
        for rel in missing:
            print("         - %s" % rel)
        ok = False
    else:
        print("  [OK] %d 个底层脚本全部就位（四 skill 同级布局）" % len(DISPATCH))

    print("")
    print("结论: %s" % ("核心环境就绪 ✓" if ok else "核心依赖缺失 ✗（见 FAIL 项）"))
    return 0 if ok else 1


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print_help()
        return 0
    if argv[0] in ("-V", "--version", "version"):
        print("ontology-suite CLI v%s" % __version__)
        return 0

    group = argv[0]
    # suite doctor 是本 CLI 自有命令（非分发）
    if group == "suite" and len(argv) >= 2 and argv[1] == "doctor":
        return doctor()

    if group not in GROUPS:
        sys.stderr.write("未知 group: %r（可用: %s）\n\n" % (group, ", ".join(GROUPS)))
        print_help()
        return 2
    if len(argv) < 2:
        sys.stderr.write("group %r 需要 action。运行 --help 查看能力地图。\n" % group)
        return 2

    action = argv[1]
    key = (group, action)
    if key not in DISPATCH:
        avail = ", ".join(a for (g, a) in DISPATCH if g == group)
        sys.stderr.write("未知 action: %s.%s（可用: %s）\n" % (group, action, avail))
        return 2

    rel, _ = DISPATCH[key]
    script = SUITE_ROOT / rel
    if not script.exists():
        sys.stderr.write("底层脚本缺失: %s\n（三 skill 须同级部署于套件 skills/ 下）\n" % script)
        return 2

    # 薄分发：剩余参数原样转发，退出码透传。各脚本自行 setup sys.path（跨 skill import）。
    rest = argv[2:]
    proc = subprocess.run([sys.executable, str(script), *rest])
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
