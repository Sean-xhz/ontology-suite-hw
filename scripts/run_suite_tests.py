#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_suite_tests.py —— 本体能力套件统一验收入口（N5）。

以 examples/ 虚构载体为 fixture，编排套件 README 验收表 T1-T10 + py_compile，
替代分散的手工命令组合；CI（.github/workflows/tests.yml）消费本入口。

设计纪律：
  - 零副作用：一切输出落临时目录（签名/校验报告/物化结果/缓存/closeout 报告）；
    子进程统一 PYTHONPYCACHEPREFIX 指向临时目录；examples/ 只读。
  - T4 全量一致口径：冻结 signature 与当前引擎输出 JSON 全量相等 + 双跑字节确定性
    （2026-11-11 引擎维护批次修复 parse_ttl bnode 非确定性后，由计数口径升级；
    历史三类漂移〔union 字段/bnode 域标签/? 前缀〕已经冻结件重生成消除）。
  - T8 需 Java（Pellet ≥25）：--skip-java 强制跳过；引擎 exit 2（环境不可用）自动
    登记 SKIP——两者均不计 FAIL。
  - exit 0 = 全过（SKIP 已登记）；exit 1 = 存在 FAIL；exit 2 = 用法/fixture 错。

用法：
  python3 scripts/run_suite_tests.py [--skip-java] [--suite-root DIR] [--keep-temp]
"""
import argparse
import hashlib
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SUITE = os.path.dirname(HERE)
BRAND_RE = re.compile(r"万[业]贷|微[业]贷|万[连]融|货[通]宝|车[主]融")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class SuiteTests:
    def __init__(self, root, tmp, skip_java):
        self.root = root
        self.skills = os.path.join(root, "skills")
        self.ex = os.path.join(root, "examples", "票据贴现")
        self.run = os.path.join(self.ex, "建模run")
        self.demo = os.path.join(self.ex, "模拟demo")
        self.ttl = os.path.join(self.run, "ontology.ttl")
        self.cases = os.path.join(self.run, "golden-cases.json")
        self.sig = os.path.join(self.demo, "票据_signature.json")
        self.tmp = tmp
        self.skip_java = skip_java
        self.env = dict(os.environ,
                        PYTHONPYCACHEPREFIX=os.path.join(tmp, "pycache"))
        self.results = []

    def script(self, skill, name):
        return os.path.join(self.skills, skill, "scripts", name)

    def py(self, *args):
        return subprocess.run([sys.executable] + list(args),
                              capture_output=True, text=True, env=self.env)

    def record(self, tid, name, status, detail=""):
        self.results.append((tid, name, status, detail))
        print("%-4s %s %s%s" % (status, tid, name,
                                (" — " + detail) if detail else ""))

    def check_fixtures(self):
        need = [self.run, self.demo, self.ttl, self.cases, self.sig,
                os.path.join(self.demo, "demo1-instance.json"),
                os.path.join(self.demo, "demo1-bad-instance.json"),
                os.path.join(self.demo, "demo1-sim-result.json")]
        missing = [p for p in need if not os.path.exists(p)]
        if missing:
            for p in missing:
                print("fixture 缺失: %s" % p, file=sys.stderr)
            print("本入口须以套件根为基准运行（examples/ 虚构载体为 fixture）",
                  file=sys.stderr)
            sys.exit(2)

    # ---- T0 py_compile（全部 skill 脚本，编译产物落临时目录）----
    def t0_py_compile(self):
        n, errs = 0, []
        for sk in ("ontology-model", "ontology-review", "ontology-simulate"):
            d = os.path.join(self.skills, sk, "scripts")
            for f in sorted(os.listdir(d)):
                if not f.endswith(".py"):
                    continue
                n += 1
                try:
                    py_compile.compile(os.path.join(d, f),
                                       cfile=os.path.join(self.tmp, "pyc",
                                                          sk + "_" + f + "c"),
                                       doraise=True)
                except py_compile.PyCompileError as exc:
                    errs.append("%s: %s" % (f, exc))
        self.record("T0", "py_compile 全脚本", "FAIL" if errs else "PASS",
                    "; ".join(errs) if errs else "%d 脚本" % n)

    # ---- T1 review self_test 全链 ----
    def t1_self_test(self):
        p = self.py(self.script("ontology-review", "self_test.py"),
                    "--runs", self.run)
        m = re.search(r"PASS (\d+) / FAIL (\d+)", p.stdout)
        ok = (p.returncode == 0 and m and m.group(2) == "0"
              and int(m.group(1)) >= 10)
        self.record("T1", "review self_test（E1-E10）",
                    "PASS" if ok else "FAIL",
                    m.group(0) if m else (p.stderr or p.stdout)[-200:])

    # ---- T2 golden-cases schema ----
    def t2_golden_schema(self):
        p = self.py(self.script("ontology-model", "run_golden_cases.py"),
                    self.ttl, self.cases, "--check")
        self.record("T2", "golden-cases --check（schema 1.0）",
                    "PASS" if p.returncode == 0 else "FAIL",
                    (p.stdout or p.stderr).strip().splitlines()[-1][:120]
                    if (p.stdout or p.stderr).strip() else "")

    # ---- T3 validate L1+L2 ----
    def t3_validate(self):
        p = self.py(self.script("ontology-model", "validate_ontology.py"),
                    self.ttl, "--json-output",
                    os.path.join(self.tmp, "validate.json"))
        self.record("T3", "validate_ontology（L1+L2）",
                    "PASS" if p.returncode == 0 else "FAIL",
                    "exit %d" % p.returncode)

    # ---- T4 signature 全量一致 + 双跑确定性 ----
    def t4_signature(self):
        out1 = os.path.join(self.tmp, "sig1.json")
        out2 = os.path.join(self.tmp, "sig2.json")
        ex = self.script("ontology-simulate", "extract_signature.py")
        p1 = self.py(ex, self.ttl, "--output", out1)
        p2 = self.py(ex, self.ttl, "--output", out2)
        if p1.returncode != 0 or p2.returncode != 0:
            self.record("T4", "extract_signature vs 冻结签名", "FAIL",
                        ((p1.stderr or p1.stdout) + (p2.stderr or p2.stdout))[-200:])
            return
        with open(out1, "rb") as f1, open(out2, "rb") as f2:
            deterministic = f1.read() == f2.read()
        if not deterministic:
            self.record("T4", "extract_signature vs 冻结签名", "FAIL",
                        "双跑字节不一致（非确定性回归）")
            return
        new = json.load(open(out1, encoding="utf-8"))
        frozen = json.load(open(self.sig, encoding="utf-8"))
        keys = ("classes", "object_properties", "data_properties", "rules")
        detail = "类 %d/对象 %d/数据 %d/规则 %d" % tuple(
            len(new[k]) for k in keys)
        if new != frozen:
            diffs = [k for k in sorted(set(new) | set(frozen))
                     if new.get(k) != frozen.get(k)]
            self.record("T4", "extract_signature vs 冻结签名", "FAIL",
                        "冻结件漂移（字段: %s）" % ", ".join(diffs))
            return
        self.record("T4", "extract_signature vs 冻结签名", "PASS",
                    "双跑字节一致 + 冻结件全量一致（%s）" % detail)

    # ---- T5/T6 check_instance 正反例 ----
    def t5_t6_check_instance(self):
        good = os.path.join(self.demo, "demo1-instance.json")
        bad = os.path.join(self.demo, "demo1-bad-instance.json")
        p = self.py(self.script("ontology-simulate", "check_instance.py"),
                    good, self.sig)
        self.record("T5", "check_instance 正例",
                    "PASS" if p.returncode == 0 else "FAIL",
                    "exit %d（期望 0）" % p.returncode)
        p = self.py(self.script("ontology-simulate", "check_instance.py"),
                    bad, self.sig)
        self.record("T6", "check_instance 反例拦截",
                    "PASS" if p.returncode == 1 else "FAIL",
                    "exit %d（期望 1）" % p.returncode)

    # ---- T7 跨 skill import ----
    def t7_cross_import(self):
        sim_scripts = os.path.join(self.skills, "ontology-simulate", "scripts")
        code = (
            "import sys; sys.path.insert(0, r'%s'); import simulate_reason; "
            "assert 'run_golden_cases' in sys.modules, 'model 跨 skill import 未解析'; "
            "assert 'review_extract' in sys.modules, 'review 跨 skill import 未解析'; "
            "print('cross-skill import ok')" % sim_scripts)
        p = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, env=self.env)
        self.record("T7", "跨 skill import（simulate→model+review）",
                    "PASS" if p.returncode == 0 else "FAIL",
                    (p.stdout or p.stderr).strip()[-160:])

    # ---- T8 物化实跑（Java）----
    def t8_simulate(self):
        if self.skip_java:
            self.record("T8", "simulate_reason demo1 物化", "SKIP",
                        "--skip-java 用户指定")
            return
        before = {p: sha256(p) for p in (self.ttl, self.cases)}
        out = os.path.join(self.tmp, "sim.json")
        p = self.py(self.script("ontology-simulate", "simulate_reason.py"),
                    "--instance", os.path.join(self.demo, "demo1-instance.json"),
                    "--ttl", self.ttl, "--signature", self.sig,
                    "--json-output", out,
                    "--cache-dir", os.path.join(self.tmp, "cache"))
        if p.returncode == 2:
            self.record("T8", "simulate_reason demo1 物化", "SKIP",
                        "Java 环境不可用（引擎 exit 2），L3 降级登记")
            return
        if p.returncode != 0:
            self.record("T8", "simulate_reason demo1 物化", "FAIL",
                        (p.stderr or p.stdout)[-200:])
            return
        r = json.load(open(out, encoding="utf-8"))
        f = json.load(open(os.path.join(self.demo, "demo1-sim-result.json"),
                           encoding="utf-8"))
        want_rules = {"ruleR1", "ruleR3", "ruleR7"}
        ok = (r.get("consistency") == "consistent"
              and len(r.get("inferred", [])) == len(f.get("inferred", [])) == 3
              and set(r.get("attribution_summary", {})) == want_rules
              and set(f.get("attribution_summary", {})) == want_rules)
        after = {p: sha256(p) for p in (self.ttl, self.cases)}
        zero_writeback = before == after
        self.record("T8", "simulate_reason demo1 物化",
                    "PASS" if (ok and zero_writeback) else "FAIL",
                    "推断 %d/3 归因 %s%s" % (
                        len(r.get("inferred", [])),
                        sorted(r.get("attribution_summary", {})),
                        " + 零回写 ✓" if zero_writeback else " + 零回写 ✗"))

    # ---- T9 closeout（报告外置，不覆盖冻结件）----
    def t9_closeout(self):
        p = self.py(self.script("ontology-model", "closeout_check.py"),
                    self.run, "--report",
                    os.path.join(self.tmp, "closeout.md"))
        self.record("T9", "closeout_check（齐套+敏感扫描）",
                    "PASS" if p.returncode == 0 else "FAIL",
                    "exit %d（报告外置临时目录）" % p.returncode)

    # ---- T10 品牌名契约 ----
    def t10_brand(self):
        text = open(self.ttl, encoding="utf-8").read()
        hits = BRAND_RE.findall(text)
        self.record("T10", "品牌名 grep 契约（虚构载体）",
                    "PASS" if not hits else "FAIL",
                    "%d 命中" % len(hits))

    def run_all(self):
        self.check_fixtures()
        self.t0_py_compile()
        self.t1_self_test()
        self.t2_golden_schema()
        self.t3_validate()
        self.t4_signature()
        self.t5_t6_check_instance()
        self.t7_cross_import()
        self.t8_simulate()
        self.t9_closeout()
        self.t10_brand()
        n_pass = sum(1 for r in self.results if r[2] == "PASS")
        n_fail = sum(1 for r in self.results if r[2] == "FAIL")
        n_skip = sum(1 for r in self.results if r[2] == "SKIP")
        print("-" * 60)
        print("套件验收：PASS %d / FAIL %d / SKIP %d（SKIP 已登记不计失败）"
              % (n_pass, n_fail, n_skip))
        return 1 if n_fail else 0


def main():
    ap = argparse.ArgumentParser(description="本体能力套件统一验收入口（N5）")
    ap.add_argument("--skip-java", action="store_true",
                    help="跳过 T8 物化实跑（无 Java 环境或快速档）")
    ap.add_argument("--suite-root", default=None,
                    help="套件根目录（缺省=本脚本所在 scripts/ 的上级）")
    ap.add_argument("--keep-temp", action="store_true",
                    help="保留临时输出目录（调试用）")
    args = ap.parse_args()
    root = os.path.abspath(args.suite_root or DEFAULT_SUITE)
    if not os.path.isdir(os.path.join(root, "skills")) or \
       not os.path.isdir(os.path.join(root, "examples")):
        print("套件根无效（缺 skills/ 或 examples/）: %s" % root, file=sys.stderr)
        sys.exit(2)
    tmp = tempfile.mkdtemp(prefix="suite-tests-")
    print("套件根: %s\n临时输出: %s" % (root, tmp))
    try:
        rc = SuiteTests(root, tmp, args.skip_java).run_all()
    finally:
        if args.keep_temp:
            print("临时目录保留: %s" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
