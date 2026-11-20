#!/usr/bin/env bash
# 本体能力套件环境引导——依赖检查 + 安装 + 可选验收。
# 用法：bash scripts/bootstrap.sh [--no-install] [--run-tests] [--skip-java]
#   --no-install  只检查依赖不执行 pip install
#   --run-tests   引导完成后运行 scripts/run_suite_tests.py（--skip-java 透传）
# 许可以与依赖登记见 requirements.txt / THIRD-PARTY-LICENSES.md；
# Java/node 要求见 skills/ontology-model/references/reasoner-limits.md §一。
set -euo pipefail
SUITE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NO_INSTALL=0; RUN_TESTS=0; TEST_ARGS=()
for a in "$@"; do case "$a" in
  --no-install) NO_INSTALL=1;;
  --run-tests) RUN_TESTS=1;;
  --skip-java) TEST_ARGS+=(--skip-java);;
  *) echo "未知参数: $a" >&2; exit 2;;
esac; done

echo "== python3（≥3.9）=="
command -v python3 >/dev/null 2>&1 || { echo "缺 python3（需 ≥3.9）" >&2; exit 1; }
python3 - <<'PY'
import sys
v = sys.version_info
assert v >= (3, 9), "需要 python3 ≥3.9，当前 %d.%d" % v[:2]
print("python %d.%d.%d ✓" % v[:3])
PY

if [ "$NO_INSTALL" -eq 0 ]; then
  echo "== pip 依赖安装 =="
  python3 -m pip install -r "$SUITE_ROOT/requirements.txt"
else
  echo "== pip 依赖检查（--no-install）=="
  python3 - <<'PY'
import importlib
for m in ("rdflib", "owlready2", "pyshacl"):
    try:
        importlib.import_module(m); print(m, "✓")
    except ImportError:
        print(m, "缺失——去掉 --no-install 重跑以安装"); raise SystemExit(1)
PY
fi

echo "== Java（L3 推理机：Pellet 需 ≥25，HermiT 需 ≥17）=="
if command -v java >/dev/null 2>&1; then
  java -version 2>&1 | head -1
  MAJOR=$(java -version 2>&1 | head -1 | sed -E 's/.*version "([0-9]+).*/\1/')
  if [ "${MAJOR:-0}" -lt 25 ]; then
    echo "警告: Java <25——Pellet 不可用；L3 按三级降级链降级并登记（reasoner-limits.md）" >&2
  fi
else
  echo "警告: 缺 java——L3 不可用，脚本降级 L2 并登记（不阻塞 L1/L2 与验收 T1-T7/T9/T10）" >&2
fi

echo "== node（可选：review self_test E9 语法检查）=="
if command -v node >/dev/null 2>&1; then node --version; else
  echo "node 缺失——E9 降级 skip 并登记（不阻塞）"
fi

echo "== ingest 解析渲染库（可选：2.0 保真进料机械层，requirements.txt 默认已装）=="
python3 - <<'PY'
import importlib
missing = []
for m in ("pypdf", "pypdfium2", "docx", "openpyxl", "pptx", "PIL"):
    try:
        importlib.import_module(m)
    except ImportError:
        missing.append(m)
if missing:
    print("警告: ingest 解析渲染库缺失 %s——ingest parse 降级 exit2（不阻塞 model/review/simulate）" % missing)
    print("  提示: pypdfium2 须 pip install --only-binary=:all: pypdfium2（旧 pip 选 sdist 会触发 GitHub 下载超时）")
else:
    print("pypdf/pypdfium2/python-docx/openpyxl/python-pptx/Pillow ✓")
PY

echo "== LibreOffice（可选：office→PDF 全视觉渲染增强）=="
if command -v soffice >/dev/null 2>&1 || command -v libreoffice >/dev/null 2>&1; then
  echo "soffice ✓（office 全视觉渲染增强可用）"
elif [ -x "/Applications/LibreOffice.app/Contents/MacOS/soffice" ]; then
  echo "LibreOffice.app ✓（office 全视觉渲染增强可用）"
else
  echo "LibreOffice 缺失——office 退 substrate-only（纯 pip 主路径仍工作；全视觉增强需 brew install --cask libreoffice）"
fi

if [ "$RUN_TESTS" -eq 1 ]; then
  echo "== 套件验收 =="
  python3 "$SUITE_ROOT/scripts/run_suite_tests.py" ${TEST_ARGS[@]+"${TEST_ARGS[@]}"}
fi
echo "bootstrap 完成"
