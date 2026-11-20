#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_suite_tests.py —— 本体能力套件统一验收入口。

以 examples/ 虚构载体为 fixture，编排套件 README 验收表 T1-T15 + py_compile，
替代分散的手工命令组合；CI（.github/workflows/tests.yml）消费本入口。

设计纪律：
  - 零副作用：一切输出落临时目录（签名/校验报告/物化结果/缓存/closeout 报告）；
    子进程统一 PYTHONPYCACHEPREFIX 指向临时目录；examples/ 只读。
  - T4 全量一致口径：冻结 signature 与当前引擎输出 JSON 全量相等 + 双跑字节确定性
    （确定性纪律：输出禁含 bnode 随机标签，跨进程零漂移）。
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

# T14 fixture 生成器（虚构票据中性，一次生成于 tmp；子进程执行，py3.9 兼容）。
# Office 保存字节跨次不稳是源件属性——契约=同源字节→同包字节，故 fixture 一次生成解析两次。
T14_FIXTURE_GEN = r'''
import os, sys
fix = sys.argv[1]
import docx, openpyxl
from pptx import Presentation
from pptx.util import Inches
from PIL import Image
d = docx.Document()
d.add_heading("票据定义", level=1)
d.add_paragraph("票据是指由出票人签发的、约定无条件支付确定金额的有价证券，包括汇票与本票。")
d.add_heading("贴现准入规则", level=1)
d.add_paragraph("若持票人信用评级不低于 AA，则允许贴现；贴现率阈值照录为 0.035，不得上浮。")
t = d.add_table(rows=3, cols=2)
t.cell(0,0).text="产品"; t.cell(0,1).text="费率"
t.cell(1,0).text="银票贴现"; t.cell(1,1).text="0.035"
t.cell(2,0).text="商票贴现"; t.cell(2,1).text="0.058"
d.save(os.path.join(fix,"票据贴现制度.docx"))
wb=openpyxl.Workbook(); ws=wb.active; ws.title="费率表"
ws["A1"]="产品"; ws["B1"]="费率"; ws["A2"]="银票贴现"; ws["B2"]=0.035
ws["A3"]="商票贴现"; ws["B3"]=0.058; ws["C1"]="上浮后"; ws["C2"]="=B2*1.1"
ws.merge_cells("A5:B5"); ws["A5"]="合计说明"
wb.save(os.path.join(fix,"票据费率表.xlsx"))
prs=Presentation(); slide=prs.slides.add_slide(prs.slide_layouts[5])
slide.shapes.title.text="票据贴现流程"
tb=slide.shapes.add_textbox(Inches(1),Inches(2),Inches(6),Inches(1))
tb.text_frame.text="贴现流程分为申请、审核、放款三个环节，须先审核后放款。"
tbl=slide.shapes.add_table(2,2,Inches(1),Inches(3),Inches(5),Inches(1)).table
tbl.cell(0,0).text="环节"; tbl.cell(0,1).text="权限"; tbl.cell(1,0).text="审核"; tbl.cell(1,1).text="须确认"
slide.notes_slide.notes_text_frame.text="专家口述：审核环节须双人复核，此为权威制度补充。"
prs.save(os.path.join(fix,"票据流程.pptx"))
objs=[b"<< /Type /Catalog /Pages 2 0 R >>",
 b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
 b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"]
stream=b"BT /F1 12 Tf 72 720 Td (Bill Discount Rule: rate threshold 0.035) Tj ET"
objs.append(b"<< /Length "+str(len(stream)).encode()+b" >>\nstream\n"+stream+b"\nendstream")
objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
out=b"%PDF-1.4\n"; offsets=[]
for i,o in enumerate(objs):
    offsets.append(len(out)); out+=str(i+1).encode()+b" 0 obj\n"+o+b"\nendobj\n"
xref=len(out); out+=b"xref\n0 "+str(len(objs)+1).encode()+b"\n0000000000 65535 f \n"
for off in offsets: out+=("%010d 00000 n \n"%off).encode()
out+=b"trailer\n<< /Size "+str(len(objs)+1).encode()+b" /Root 1 0 R >>\nstartxref\n"+str(xref).encode()+b"\n%%EOF\n"
open(os.path.join(fix,"bill_rule.pdf"),"wb").write(out)
im=Image.new("RGB",(200,100),(240,240,255)); im.save(os.path.join(fix,"票据样本.png"))
Image.open(os.path.join(fix,"票据样本.png")).save(os.path.join(fix,"票据扫描件.pdf"),"PDF",resolution=100.0)
print("fixtures ok")
'''


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
        for sk in ("ontology-model", "ontology-review", "ontology-simulate", "ontology-ingest"):
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
        self.record("T1", "review self_test（E1-E14）",
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

    # ---- T11 R2 增量 patch（6 子例聚合，patch JSON 运行时生成于 tmp，examples 零改动）----
    def t11_patch(self):
        before = {p: sha256(p) for p in (self.ttl, self.cases)}
        script = self.script("ontology-model", "incremental_patch.py")
        base_sha = sha256(self.ttl)
        details, fails = [], []

        def run_patch(ops, tag, extra=None, sha=None):
            patch = {"schema_version": "1.0", "patch_id": tag,
                     "baseline": {"path": self.ttl, "sha256": sha or base_sha},
                     "source": {"channel": "manual", "ref": "T11"},
                     "bump": "auto", "operations": ops}
            pj = os.path.join(self.tmp, tag + ".patch.json")
            with open(pj, "w", encoding="utf-8") as fh:
                json.dump(patch, fh, ensure_ascii=False)
            draft = os.path.join(self.tmp, tag + ".draft.ttl")
            rep = os.path.join(self.tmp, tag + ".report.json")
            p = self.py(script, self.ttl, pj, "--output-draft", draft,
                        "--report", rep, *(extra or []))
            r = json.load(open(rep, encoding="utf-8")) if os.path.exists(rep) else None
            return p.returncode, r, draft

        # T11a 注解正例：modify_label → PATCH + annotation-only skip（不付 JVM）
        rc, r, d = run_patch([{"op": "modify_label", "target": "Bill",
                               "label": "票据（T11 验收）", "lang": "zh"}],
                             "t11a", ["--golden", self.cases])
        da = d  # 锁定 T11a draft 路径（d 会被后续子例覆盖，T11f 双跑须比同一操作）
        a_ok = (rc == 0 and r and r["version"]["bump_applied"] == "patch"
                and r["regression"]["verdict"] == "skipped(annotation-only)"
                and os.path.exists(d))
        details.append("a=PATCH/annotation-skip" if a_ok else "a FAIL")
        if not a_ok:
            fails.append("a")

        # T11b 结构正例：add_class ⊑ Bill → MINOR（Java 档回归 pass / skip-java 档 not-requested）
        extra_b = [] if self.skip_java else ["--golden", self.cases]
        rc, r, d = run_patch([{"op": "add_class", "id": "PatchDemoClass",
                               "label": "补丁演示类", "subclass_of": "Bill"}],
                             "t11b", extra_b)
        if self.skip_java:
            b_ok = (rc == 0 and r and r["version"]["bump_applied"] == "minor"
                    and r["regression"]["verdict"] == "not-requested" and os.path.exists(d))
            b_detail = "b=MINOR/not-requested(skip-java)"
        else:
            b_ok = (rc == 0 and r and r["version"]["bump_applied"] == "minor"
                    and r["regression"]["verdict"] in ("pass", "downgraded")
                    and os.path.exists(d))
            b_detail = "b=MINOR/%s" % (r["regression"]["verdict"] if r else "?")
        details.append(b_detail if b_ok else "b FAIL")
        if not b_ok:
            fails.append("b")

        # T11c L2 反例：disjoint ∧ subClassOf → exit 1 + new_errors≥1 + 回归短路 + draft 仍产
        rc, r, d = run_patch([{"op": "add_triple", "s": "Discountable",
                               "p": "rdfs:subClassOf", "o": "NonDiscountable"}],
                             "t11c", ["--golden", self.cases])
        c_ok = (rc == 1 and r and len(r["validation"]["l1_l2"]["new_errors"]) >= 1
                and r["regression"]["verdict"] == "skipped(l1l2-blocked)"
                and os.path.exists(d))
        details.append("c=L2-blocked/短路" if c_ok else "c FAIL")
        if not c_ok:
            fails.append("c")

        # T11d 回归反例：replace_literal oneOf 已提交→已递交 → G1 翻转（需 Java；skip-java/无 Java→SKIP 登记）
        if self.skip_java:
            d_ok, d_detail = True, "d=SKIP(skip-java，翻转检出需 Java)"
        else:
            rc, r, d = run_patch([{"op": "replace_literal", "p": "rdf:first",
                                   "old": {"value": "已提交"}, "new": {"value": "已递交"}}],
                                 "t11d", ["--golden", self.cases])
            if r and r["regression"]["verdict"] == "downgraded":
                d_ok, d_detail = True, "d=SKIP(Java 不可用，MINOR 降级)"
            else:
                d_ok = (rc == 1 and r and "G1" in r["regression"].get("newly_failed", []))
                d_detail = "d=回归翻转 G1" if d_ok else "d FAIL"
        details.append(d_detail)
        if not d_ok:
            fails.append("d")

        # T11e 契约/政策：① remove_rule 无 --golden → MAJOR blocked exit 1；② sha 错配 → exit 2 不产 draft
        rc, r, d = run_patch([{"op": "remove_rule", "rule": "ruleR3"}], "t11e1")
        e1_ok = (rc == 1 and r and r["version"]["bump_applied"] == "major"
                 and r["regression"]["verdict"] == "blocked")
        rc2, r2, d2 = run_patch([{"op": "modify_label", "target": "Bill", "label": "x"}],
                                "t11e2", sha="0" * 64)
        e2_ok = (rc2 == 2 and not os.path.exists(d2))
        e_ok = e1_ok and e2_ok
        details.append("e=MAJOR-blocked/sha-exit2" if e_ok else "e FAIL")
        if not e_ok:
            fails.append("e")

        # T11f 确定性：同一 patch（同 patch_id=t11a）跨进程双跑 draft 字节一致
        # 复用 T11a 已落盘 patch JSON 二次跑——draft 溯源头含 patch_id，须同输入才同输出
        pj_a = os.path.join(self.tmp, "t11a.patch.json")
        d3 = os.path.join(self.tmp, "t11f.draft.ttl")
        rep3 = os.path.join(self.tmp, "t11f.report.json")
        self.py(script, self.ttl, pj_a, "--output-draft", d3,
                "--report", rep3, "--golden", self.cases)
        f_ok = (os.path.exists(da) and os.path.exists(d3)
                and open(da, "rb").read() == open(d3, "rb").read())
        details.append("f=双跑字节一致" if f_ok else "f FAIL")
        if not f_ok:
            fails.append("f")

        after = {p: sha256(p) for p in (self.ttl, self.cases)}
        zero_writeback = before == after
        if not zero_writeback:
            fails.append("zero-writeback")
        ok = not fails
        self.record("T11", "R2 增量 patch（6 子例）",
                    "PASS" if ok else "FAIL",
                    "｜".join(details) + ("｜零回写 ✓" if zero_writeback else "｜零回写 ✗"))

    # ---- T12 R4 SHACL 派生+校验（7 子例聚合，data/shapes 运行时生成于 tmp，examples 零改动）----
    def t12_shacl(self):
        before = {p: sha256(p) for p in (self.ttl, self.cases, self.sig)}
        derive = self.script("ontology-model", "derive_shacl.py")
        validate = self.script("ontology-model", "validate_shacl.py")
        check_inst = self.script("ontology-simulate", "check_instance.py")
        shapes = os.path.join(self.tmp, "t12a.shapes.ttl")
        dreport = os.path.join(self.tmp, "t12a.report.json")
        details, fails = [], []

        # 虚构票据数据构造器（运行时 tmp；金额裸 integer 字面量验 R-d 数值容忍；base 对齐 fixture）
        P = ('@prefix : <http://example.org/bill-discount#> .\n'
             '@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n')
        ACC = (':acc1 a :Acceptor ; :creditRating "AAA" ; '
               ':unifiedSocialCreditCode "91110000AAAAAAAAAA" .\n')
        HOLD = (':hold1 a :Holder ; :enterpriseName "虚构持票企业A" ; '
                ':unifiedSocialCreditCode "91110000BBBBBBBBBB" .\n')

        def bill(num="PJ202601010001", amt="500000", acc=":acc1", holder=":hold1"):
            return (':bill1 a :Bill ; :billNumber "%s" ; :faceAmount %s ; '
                    ':issueDate "2026-01-01"^^xsd:date ; :dueDate "2026-07-01"^^xsd:date ; '
                    ':hasAcceptor %s ; :currentHolder %s .\n' % (num, amt, acc, holder))

        def app(num="ZX202601010001", status="已提交", cls=":DiscountApplication",
                amt="495000", subj=":app1"):
            return ('%s a %s ; :applicationNumber "%s" ; '
                    ':applicationDate "2026-01-02"^^xsd:date ; :applicationStatus "%s" ; '
                    ':expectedDiscountAmount %s ; :targetsBill :bill1 ; :initiatedBy :hold1 .\n'
                    % (subj, cls, num, status, amt))

        def run_validate(tag, data):
            f = os.path.join(self.tmp, tag + ".data.ttl")
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(data)
            rep = os.path.join(self.tmp, tag + ".violations.json")
            p = self.py(validate, f, shapes, "--json-output", rep,
                        "--derivation-report", dreport)
            r = json.load(open(rep, encoding="utf-8")) if os.path.exists(rep) else None
            return p.returncode, r

        def comps(r):
            if not r:
                return set()
            return set(x["constraint_component"] for x in r["results"]
                       if x["severity"] == "error")

        # T12a 派生+确定性：双跑 shapes/report 字节一致 + 计数锚 + unmapped 登记（纯 rdflib 无 Java）
        shapes2 = os.path.join(self.tmp, "t12a2.shapes.ttl")
        dreport2 = os.path.join(self.tmp, "t12a2.report.json")
        pa1 = self.py(derive, self.ttl, "--output-shapes", shapes, "--report", dreport)
        pa2 = self.py(derive, self.ttl, "--output-shapes", shapes2, "--report", dreport2)
        ra = json.load(open(dreport, encoding="utf-8")) if os.path.exists(dreport) else None
        a_ok = (pa1.returncode == 0 and pa2.returncode == 0 and ra is not None
                and os.path.exists(shapes2)
                and open(shapes, "rb").read() == open(shapes2, "rb").read()
                and open(dreport, "rb").read() == open(dreport2, "rb").read())
        if a_ok:
            kc = ra["kind_counts"]
            uk = {}
            for u in ra["unmapped"]:
                uk[u["kind"]] = uk.get(u["kind"], 0) + 1
            a_ok = (kc.get("facet-datatype") == 3 and kc.get("oneOf-in") == 2
                    and kc.get("restriction-someValuesFrom") == 1
                    and kc.get("restriction-maxQualifiedCardinality") == 1
                    and kc.get("hasKey-sparql") == 4
                    and uk.get("SWRL-rule") == 5 and uk.get("TransitiveProperty") == 1
                    and uk.get("AllDisjointClasses") == 1)
        details.append("a=派生双跑字节一致/计数锚" if a_ok else "a FAIL")
        if not a_ok:
            fails.append("a")

        # T12b 正例 conform：完整 Bill（int 金额验 R-d）+ 一笔申请；变体仅类型化子类（验 R-c 闭包）
        rc1, r1 = run_validate("t12b1", P + ACC + HOLD + bill() + app())
        rc2, r2 = run_validate("t12b2", P + ACC + HOLD + bill()
                               + app(cls=":AcceptableApplication"))
        b_ok = (rc1 == 0 and r1 and r1["pass"] and rc2 == 0 and r2 and r2["pass"])
        details.append("b=conform×2(R-d/R-c)" if b_ok else "b FAIL")
        if not b_ok:
            fails.append("b")

        # T12c facet 越限（补洞演示）：SHACL 检出 MinExclusive+Pattern + 溯源挂源句；
        #      对偶 check_instance 同场景 W08 放行 rc=0（Pellet 剥离/旧闸门放行/SHACL 检出三态）
        rc, r = run_validate("t12c", P + ACC + HOLD + bill(num="随便写", amt="-5") + app())
        c_shacl = (rc == 1 and r and not r["pass"]
                   and "MinExclusiveConstraintComponent" in comps(r)
                   and "PatternConstraintComponent" in comps(r)
                   and any(x.get("source_sentences") for x in r["results"]
                           if x["severity"] == "error"))
        inst = json.load(open(os.path.join(self.demo, "demo1-instance.json"),
                              encoding="utf-8"))
        for ind in inst["individuals"]:
            if ind["name"] == "indBill1":
                ind["facts"]["faceAmount"] = -5
                ind["facts"]["billNumber"] = "随便写"
        cij = os.path.join(self.tmp, "t12c-instance.json")
        with open(cij, "w", encoding="utf-8") as fh:
            json.dump(inst, fh, ensure_ascii=False)
        pc = self.py(check_inst, cij, self.sig)
        c_ok = c_shacl and pc.returncode == 0 and "W08" in pc.stdout
        details.append("c=SHACL检出+溯源/check_instance放行(补洞对偶)" if c_ok else "c FAIL")
        if not c_ok:
            fails.append("c")

        # T12d 基数三反例：d1 无承兑人 MinCount / d2 两承兑人 MaxCount / d3 两笔审核中申请 QualifiedMaxCount
        #      （d3=R-a 定义类展开+R-b 逆路径验收锚，输入侧无 Java 检出）
        d1data = (P + ACC + HOLD
                  + ':bill1 a :Bill ; :billNumber "PJ202601010001" ; :faceAmount 500000 ; '
                    ':issueDate "2026-01-01"^^xsd:date ; :dueDate "2026-07-01"^^xsd:date ; '
                    ':currentHolder :hold1 .\n' + app())
        rc1, r1 = run_validate("t12d1", d1data)
        d2data = (P + ACC
                  + ':acc2 a :Acceptor ; :creditRating "AA" ; '
                    ':unifiedSocialCreditCode "91110000CCCCCCCCCC" .\n' + HOLD
                  + ':bill1 a :Bill ; :billNumber "PJ202601010001" ; :faceAmount 500000 ; '
                    ':issueDate "2026-01-01"^^xsd:date ; :dueDate "2026-07-01"^^xsd:date ; '
                    ':hasAcceptor :acc1, :acc2 ; :currentHolder :hold1 .\n' + app())
        rc2, r2 = run_validate("t12d2", d2data)
        d3data = (P + ACC + HOLD + bill()
                  + app(num="ZX202601010001", status="审核中",
                        cls=":AcceptableApplication", subj=":app1")
                  + app(num="ZX202601010002", status="审核中",
                        cls=":AcceptableApplication", subj=":app2"))
        rc3, r3 = run_validate("t12d3", d3data)
        d_ok = (rc1 == 1 and "MinCountConstraintComponent" in comps(r1)
                and rc2 == 1 and "MaxCountConstraintComponent" in comps(r2)
                and rc3 == 1 and "QualifiedMaxCountConstraintComponent" in comps(r3))
        details.append("d=MinCount/MaxCount/QualifiedMaxCount" if d_ok else "d FAIL")
        if not d_ok:
            fails.append("d")

        # T12e 枚举反例：creditRating="BBB" → InConstraintComponent（E07+Pellet oneOf+SHACL 三保险）
        rc, r = run_validate("t12e", P
                             + ':acc1 a :Acceptor ; :creditRating "BBB" ; '
                               ':unifiedSocialCreditCode "91110000AAAAAAAAAA" .\n'
                             + HOLD + bill() + app())
        e_ok = (rc == 1 and "InConstraintComponent" in comps(r))
        details.append("e=InConstraint" if e_ok else "e FAIL")
        if not e_ok:
            fails.append("e")

        # T12f hasKey 反例：两完整 Bill 同 billNumber → SPARQLConstraintComponent（类内键值重复）
        fdata = (P + ACC + HOLD
                 + ':acc2 a :Acceptor ; :creditRating "AA" ; '
                   ':unifiedSocialCreditCode "91110000CCCCCCCCCC" .\n'
                 + ':hold2 a :Holder ; :enterpriseName "虚构持票企业B" ; '
                   ':unifiedSocialCreditCode "91110000DDDDDDDDDD" .\n'
                 + bill() + app()
                 + ':bill2 a :Bill ; :billNumber "PJ202601010001" ; :faceAmount 600000 ; '
                   ':issueDate "2026-01-01"^^xsd:date ; :dueDate "2026-07-01"^^xsd:date ; '
                   ':hasAcceptor :acc2 ; :currentHolder :hold2 .\n')
        rc, r = run_validate("t12f", fdata)
        f_ok = (rc == 1 and "SPARQLConstraintComponent" in comps(r))
        details.append("f=SPARQL(hasKey)" if f_ok else "f FAIL")
        if not f_ok:
            fails.append("f")

        # T12g 契约错：缺失 data 文件 / 坏 TTL（解析失败）→ 各 exit 2
        missing = os.path.join(self.tmp, "t12g-missing.ttl")
        pg1 = self.py(validate, missing, shapes)
        bad = os.path.join(self.tmp, "t12g-bad.ttl")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("this is not valid turtle <<< @@@\n")
        pg2 = self.py(validate, bad, shapes)
        g_ok = (pg1.returncode == 2 and pg2.returncode == 2)
        details.append("g=缺文件/坏TTL exit2" if g_ok else "g FAIL")
        if not g_ok:
            fails.append("g")

        after = {p: sha256(p) for p in (self.ttl, self.cases, self.sig)}
        zero_writeback = before == after
        if not zero_writeback:
            fails.append("zero-writeback")
        ok = not fails
        self.record("T12", "R4 SHACL 派生+校验（7 子例）",
                    "PASS" if ok else "FAIL",
                    "｜".join(details) + ("｜零回写 ✓" if zero_writeback else "｜零回写 ✗"))

    # ---- T13 D2/D4 审阅页图形化+拖拽编辑端到端（6 子例，supply→产页→patch→引擎，tmp 零副作用）----
    def t13_d2d4(self):
        before = {p: sha256(p) for p in (self.ttl, self.cases, self.sig)}
        rx = self.script("ontology-review", "review_extract.py")
        bp = self.script("ontology-review", "build_review_page.py")
        engine = self.script("ontology-model", "incremental_patch.py")
        base_sha = sha256(self.ttl)
        details, fails = [], []
        rj = os.path.join(self.tmp, "t13.review.json")
        page = os.path.join(self.tmp, "t13.page.html")

        # T13a supply→产页：extract schema 1.1 + build exit0 + D2/D4 token + app 块 node --check 逐块
        pa = self.py(rx, self.run, "--output", rj)
        pb = self.py(bp, rj, "--output", page)
        D = json.load(open(rj, encoding="utf-8")) if os.path.exists(rj) else {}
        a_ok = (pa.returncode == 0 and pb.returncode == 0 and os.path.exists(page)
                and D.get("schema_version") == "1.1" and bool(D.get("iri_map")))
        if a_ok:
            html = open(page, encoding="utf-8").read()
            toks = ["GRAPHS", "print-only", "data-anchor-graph", "d4-toggle", "axiom_graph"]
            blocks = re.findall(r"<script>(.*?)</script>", html, re.S)
            a_ok = (all(t in html for t in toks) and "__DATA_JSON__" not in html
                    and len(blocks) == 4)
            if a_ok:
                appf = os.path.join(self.tmp, "t13.app.js")
                with open(appf, "w", encoding="utf-8") as fh:
                    fh.write(blocks[-1])
                nc = subprocess.run(["node", "--check", appf], capture_output=True, text=True)
                a_ok = nc.returncode == 0
        details.append("a=supply1.1/产页token/node逐块" if a_ok else "a FAIL")
        if not a_ok:
            fails.append("a")

        # patch 构造器（从 supply 镜像前端映射；patch_id 内容哈希同 self_test.d4_patch_id）
        def canon(o):
            return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

        def pid(ops):
            return "P-d4-" + hashlib.sha256(
                canon({"baseline": base_sha, "operations": ops}).encode("utf-8")).hexdigest()[:12]

        iris = D.get("iri_map", {})
        lit = D.get("literal_meta", {})
        enums = D.get("enum_literals", {})
        ci = iris.get("classes", {})
        opi = iris.get("object_properties", {})

        def mkpatch(ops, tag):
            p = {"schema_version": "1.0", "patch_id": pid(ops),
                 "baseline": {"path": "ontology.ttl", "sha256": base_sha},
                 "source": {"channel": "d4", "ref": "t13-" + tag},
                 "base_version": D.get("supply_meta", {}).get("ontology_version"),
                 "bump": "auto", "operations": ops}
            f = os.path.join(self.tmp, tag + ".patch.json")
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(p, fh, ensure_ascii=False)
            return f

        def run_engine(pf, tag, golden=True):
            d = os.path.join(self.tmp, tag + ".draft.ttl")
            rep = os.path.join(self.tmp, tag + ".report.json")
            args = [engine, self.ttl, pf, "--output-draft", d, "--report", rep]
            if golden:
                args += ["--golden", self.cases]
            pr = self.py(*args)
            r = json.load(open(rep, encoding="utf-8")) if os.path.exists(rep) else None
            return pr.returncode, r, d

        # T13b 5 类 patch 正例（label/comment=PATCH annotation；enum/subclass/range=MINOR）
        bill = ci.get("Bill", "")
        b_ok = True
        b_detail = []
        # label（modify_label，lang 省略引擎继承）
        pf = mkpatch([{"op": "modify_label", "target": bill, "label": "票据（T13 验收）"}], "t13b_label")
        rc, r, d = run_engine(pf, "t13b_label")
        ok = rc == 0 and r and r["version"]["bump_applied"] == "patch" and os.path.exists(d)
        b_ok &= ok
        b_detail.append("label" if ok else "label✗")
        # comment（存在→replace_literal 全等保 lang；缺失→add_triple）
        com = (lit.get("class:Bill", {}) or {}).get("comment")
        if com:
            newc = {"value": "T13 端到端注释"}
            if com.get("lang"):
                newc["lang"] = com["lang"]
            elif com.get("datatype"):
                newc["datatype"] = com["datatype"]
            cops = [{"op": "replace_literal", "s": bill, "p": "rdfs:comment", "old": com, "new": newc}]
        else:
            cops = [{"op": "add_triple", "s": bill, "p": "rdfs:comment", "o": {"value": "T13 端到端注释"}}]
        pf = mkpatch(cops, "t13b_comment")
        rc, r, d = run_engine(pf, "t13b_comment")
        ok = rc == 0 and r and r["version"]["bump_applied"] == "patch" and os.path.exists(d)
        b_ok &= ok
        b_detail.append("comment" if ok else "comment✗")
        # MINOR 三例（skip-java 档不带 --golden→not-requested，照 T11b 体例）
        minor_golden = not self.skip_java
        # enum 已划款→已付款（golden 引用 0 次回归中性）
        ast = enums.get("applicationStatus", [])
        oldv = next((e for e in ast if e["value"] == "已划款"), None)
        if oldv:
            newv = {"value": "已付款"}
            if oldv.get("lang"):
                newv["lang"] = oldv["lang"]
            elif oldv.get("datatype"):
                newv["datatype"] = oldv["datatype"]
            eops = [{"op": "replace_literal", "p": "rdf:first", "old": oldv, "new": newv}]
            pf = mkpatch(eops, "t13b_enum")
            rc, r, d = run_engine(pf, "t13b_enum", golden=minor_golden)
            ok = rc == 0 and r and r["version"]["bump_applied"] == "minor" and os.path.exists(d)
        else:
            ok = False
        b_ok &= ok
        b_detail.append("enum" if ok else "enum✗")
        # subclass Discountable reparent Bill→Holder（恰 1 具名父）
        sops = [{"op": "remove_triple", "s": ci.get("Discountable", ""), "p": "rdfs:subClassOf", "o": bill},
                {"op": "add_triple", "s": ci.get("Discountable", ""), "p": "rdfs:subClassOf", "o": ci.get("Holder", "")}]
        pf = mkpatch(sops, "t13b_subclass")
        rc, r, d = run_engine(pf, "t13b_subclass", golden=minor_golden)
        ok = rc == 0 and r and r["version"]["bump_applied"] == "minor" and os.path.exists(d)
        b_ok &= ok
        b_detail.append("subclass" if ok else "subclass✗")
        # range hasAcceptor Acceptor→Holder
        ha = next((p for p in D.get("object_properties", []) if p["ttl"]["id"] == "hasAcceptor"), None)
        old_range = ha["ttl"].get("range") if ha else None
        rops = [{"op": "remove_triple", "s": opi.get("hasAcceptor", ""), "p": "rdfs:range", "o": ci.get(old_range, "")},
                {"op": "add_triple", "s": opi.get("hasAcceptor", ""), "p": "rdfs:range", "o": ci.get("Holder", "")}]
        pf = mkpatch(rops, "t13b_range")
        rc, r, d = run_engine(pf, "t13b_range", golden=minor_golden)
        ok = rc == 0 and r and r["version"]["bump_applied"] == "minor" and os.path.exists(d)
        b_ok &= ok
        b_detail.append("range" if ok else "range✗")
        details.append("b=" + "/".join(b_detail) + ("(skip-java)" if self.skip_java else ""))
        if not b_ok:
            fails.append("b")

        # T13c 负例：G1 12 位 sha→exit2 不产 draft；G2 裸文本 old→exit2（0 匹配）
        pf = mkpatch([{"op": "modify_label", "target": bill, "label": "x"}], "t13c_sha12")
        p = json.load(open(pf, encoding="utf-8"))
        p["baseline"]["sha256"] = base_sha[:12]
        json.dump(p, open(pf, "w", encoding="utf-8"), ensure_ascii=False)
        rc, r, d = run_engine(pf, "t13c_sha12", golden=False)
        c1 = rc == 2 and not os.path.exists(d)
        neg2 = {"schema_version": "1.0", "patch_id": "P-d4-negg2",
                "baseline": {"path": "ontology.ttl", "sha256": base_sha},
                "source": {"channel": "d4", "ref": "t13c"}, "bump": "auto",
                "operations": [{"op": "replace_literal", "s": bill, "p": "rdfs:comment",
                                "old": "裸文本无编码", "new": {"value": "x"}}]}
        pf2 = os.path.join(self.tmp, "t13c_g2.patch.json")
        json.dump(neg2, open(pf2, "w", encoding="utf-8"), ensure_ascii=False)
        rc2, r2, d2 = run_engine(pf2, "t13c_g2", golden=False)
        c_ok = c1 and rc2 == 2
        details.append("c=sha12/G2 exit2" if c_ok else "c FAIL")
        if not c_ok:
            fails.append("c")

        # T13d 回归翻转：已提交→已递交 --golden→exit1 newly_failed G1（skip-java/无 Java→SKIP 登记）
        if self.skip_java:
            d_ok, d_detail = True, "d=SKIP(skip-java，翻转检出需 Java)"
        else:
            fops = [{"op": "replace_literal", "p": "rdf:first",
                     "old": {"value": "已提交"}, "new": {"value": "已递交"}}]
            pf = mkpatch(fops, "t13d_flip")
            rc, r, d = run_engine(pf, "t13d_flip")
            if r and r["regression"]["verdict"] == "downgraded":
                d_ok, d_detail = True, "d=SKIP(Java 不可用，MINOR 降级)"
            else:
                d_ok = rc == 1 and r and "G1" in r["regression"].get("newly_failed", [])
                d_detail = "d=回归翻转 G1" if d_ok else "d FAIL"
        details.append(d_detail)
        if not d_ok:
            fails.append("d")

        # T13e 确定性：同 label patch（内容哈希 patch_id）跨进程双跑 draft 字节一致
        pf = mkpatch([{"op": "modify_label", "target": bill, "label": "票据（T13 确定性）"}], "t13e_a")
        rc1, r1, da = run_engine(pf, "t13e_a")
        rc2, r2, db = run_engine(pf, "t13e_b")
        e_ok = os.path.exists(da) and os.path.exists(db) and open(da, "rb").read() == open(db, "rb").read()
        details.append("e=双跑字节一致" if e_ok else "e FAIL")
        if not e_ok:
            fails.append("e")

        # T13f merge 输出隔离：进程内 parse_ttl+supply+merge 后 build_signature==冻结件（T4 补充）
        review_dir = os.path.dirname(rx)
        sim_dir = os.path.dirname(self.script("ontology-simulate", "extract_signature.py"))
        scheme = os.path.join(self.run, "建模方案.md")
        code = (
            "import sys,json; sys.path.insert(0,r'%s'); sys.path.insert(0,r'%s');"
            "import review_extract as RX; import extract_signature as ES;"
            "ttl=RX.parse_ttl(r'%s'); assert 'supply' in ttl;"
            "md=RX.parse_scheme_md(r'%s'); merged=RX.merge(ttl,md,r'%s');"
            "assert merged.get('schema_version')=='1.1';"
            "sig=ES.build_signature(r'%s'); frozen=json.load(open(r'%s',encoding='utf-8'));"
            "assert sig==frozen,'T4 drift'; print('merge+supply isolation ok')"
        ) % (review_dir, sim_dir, self.ttl, scheme, self.run, self.ttl, self.sig)
        pf = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        f_ok = pf.returncode == 0
        details.append("f=merge隔离T4零漂移" if f_ok else "f FAIL:" + (pf.stderr or pf.stdout)[-100:])
        if not f_ok:
            fails.append("f")

        after = {p: sha256(p) for p in (self.ttl, self.cases, self.sig)}
        zero_writeback = before == after
        if not zero_writeback:
            fails.append("zero-writeback")
        ok = not fails
        self.record("T13", "D2/D4 审阅页图形化+拖拽编辑端到端（6 子例）",
                    "PASS" if ok else "FAIL",
                    "｜".join(details) + ("｜零回写 ✓" if zero_writeback else "｜零回写 ✗"))

    # ---- T14 ingest 2.1 保真进料机械层（纯 pip，入口库探测缺→整条 SKIP，照 T8 java SKIP 先例）----
    def t14_ingest(self):
        probe = self.py("-c", "import pypdf, pypdfium2, docx, openpyxl, pptx, PIL")
        if probe.returncode != 0:
            self.record("T14", "ingest 2.1 保真进料机械层（10 子例）", "SKIP",
                        "解析渲染库未装（pypdf/pypdfium2/python-docx/openpyxl/python-pptx/Pillow），pip install 后重跑")
            return
        before = {p: sha256(p) for p in (self.ttl, self.cases, self.sig)}
        details, fails = [], []
        fix = os.path.join(self.tmp, "t14_fix")
        os.makedirs(fix, exist_ok=True)
        gen = self.py("-c", T14_FIXTURE_GEN, fix)
        if gen.returncode != 0:
            self.record("T14", "ingest 2.1 保真进料机械层（10 子例）", "FAIL",
                        "fixture 生成失败：" + (gen.stderr or gen.stdout)[-200:])
            return
        names = ["票据贴现制度.docx", "票据费率表.xlsx", "票据流程.pptx",
                 "bill_rule.pdf", "票据样本.png", "票据扫描件.pdf"]
        srcs = [os.path.join(fix, n) for n in names]
        src_before = {p: sha256(p) for p in srcs}
        docx_p, xlsx_p, pptx_p, pdf_p, png_p, scan_p = srcs
        parser = self.script("ontology-ingest", "parse_documents.py")

        def parse(inputs, out, extra=None):
            # --no-office-render 强制 substrate-only canonical 档：T14 环境无关（CI 装 LibreOffice 亦同）
            return self.py(parser, *(inputs + ["--output-dir", out, "--no-office-render"] + (extra or [])))

        def load(out, did):
            return json.load(open(os.path.join(out, did, "manifest.json"), encoding="utf-8"))

        def md_text(out, did):
            return open(os.path.join(out, did, did + ".md"), encoding="utf-8").read()

        # a 四文本格式 schema 2.1（DOCX/XLSX/PPTX substrate + PDF rendered_image，全 prepared）
        out_a = os.path.join(self.tmp, "t14_a")
        pa = parse([docx_p, xlsx_p, pptx_p, pdf_p], out_a,
                   ["--authority", "正式制度", "--sensitivity", "虚构通用"])
        a_ok = pa.returncode == 0
        if a_ok:
            md_ = load(out_a, "票据贴现制度"); mx = load(out_a, "票据费率表")
            mp = load(out_a, "票据流程"); mf = load(out_a, "bill_rule")
            blob = json.dumps([md_, mx, mp, mf], ensure_ascii=False)
            a_ok = (all(m["schema_version"] == "2.1" for m in [md_, mx, mp, mf])
                    and all(s["extraction"] == "prepared" for m in [md_, mx, mp, mf] for s in m["sections"])
                    and md_["source"]["sha256"] == src_before[docx_p]
                    and md_["sections"][0]["substrate"] is not None  # DOCX 结构化 substrate
                    and mx["sections"][0]["substrate"] is not None    # XLSX 网格 substrate
                    and mp["sections"][0]["substrate"] is not None    # PPTX 位置 substrate
                    and mf["sections"][0]["rendered_image"] is not None  # PDF 渲染页图
                    and mf["sections"][0]["substrate"] is None
                    and "0.035" in blob
                    and any("商务参数" in s["sensitive_flags"] for s in md_["sections"])
                    and any(t["term"] == "票据定义" for t in md_["term_candidates"])
                    and any(s["locator"].get("sheet") == "费率表" for s in mx["sections"])
                    and any(s["locator"].get("kind") == "slide" for s in mp["sections"])
                    and "| 产品 | 费率 |" in md_text(out_a, "票据贴现制度")
                    and md_["parser"]["libreoffice_render"] is False  # --no-office-render 生效
                    and len(md_["sections"]) == 1)                    # substrate-only DOCX 单节
        details.append("a=四格式schema2.1" if a_ok else "a FAIL")
        if not a_ok:
            fails.append("a")

        # b 图片 rendered_image 直供（prepared，inventory items=[]，零 LLM 结构断言）
        out_b = os.path.join(self.tmp, "t14_b")
        pb = parse([png_p], out_b)
        b_ok = pb.returncode == 0
        if b_ok:
            mb = load(out_b, "票据样本"); s0 = mb["sections"][0]; att = mb["attachments"][0]
            att_path = os.path.join(out_b, "票据样本", "attachments", att["name"])
            b_ok = (s0["text"] is None and s0["extraction"] == "prepared"
                    and s0["rendered_image"] is not None
                    and s0["inventory"]["items"] == []
                    and att["sha256"] == src_before[png_p]
                    and sha256(att_path) == src_before[png_p])
        details.append("b=图片rendered直供" if b_ok else "b FAIL")
        if not b_ok:
            fails.append("b")

        # c 契约错四连 + 坏文件（各 exit2 不产包；--force 覆盖 exit0）
        rc1 = parse([os.path.join(fix, "不存在.docx")], os.path.join(self.tmp, "t14_c1")).returncode
        xyz = os.path.join(fix, "x.xyz")
        open(xyz, "w").write("x")
        rc2 = parse([xyz], os.path.join(self.tmp, "t14_c2")).returncode
        rc3 = parse([docx_p], out_a).returncode  # 再解析守卫（out_a 非空）
        rc4 = parse([docx_p], out_a, ["--force"]).returncode
        bad = os.path.join(fix, "坏.pdf")
        open(bad, "wb").write(b"%PDF-1.4 garbage")
        rc5 = parse([bad], os.path.join(self.tmp, "t14_c5")).returncode
        c_ok = (rc1 == 2 and rc2 == 2 and rc3 == 2 and rc4 == 0 and rc5 == 2)
        details.append("c=契约错exit2" if c_ok else "c FAIL%s" % [rc1, rc2, rc3, rc4, rc5])
        if not c_ok:
            fails.append("c")

        # d 扫描页整页渲染（2.0 反转：image-only-page gap + rendered_image PNG + inventory items=[]）
        out_d = os.path.join(self.tmp, "t14_d")
        pd_ = parse([scan_p], out_d)
        d_ok = pd_.returncode == 0
        if d_ok:
            ms = load(out_d, "票据扫描件"); s0 = ms["sections"][0]
            ri = s0["rendered_image"]
            att_path = os.path.join(out_d, "票据扫描件", "attachments", ri["name"])
            d_ok = (any(g["kind"] == "image-only-page" for g in ms["gaps"])
                    and s0["extraction"] == "prepared" and s0["text"] is None
                    and ri is not None and s0["inventory"]["items"] == []
                    and os.path.isfile(att_path) and sha256(att_path) == ri["sha256"]
                    and ri["bytes"] > 0)
        details.append("d=扫描页整页渲染" if d_ok else "d FAIL")
        if not d_ok:
            fails.append("d")

        # e 双跑全量字节等（无豁免条款，MD+manifest+attachments 含 PDF→PNG 渲染）
        out_e1 = os.path.join(self.tmp, "t14_e1"); out_e2 = os.path.join(self.tmp, "t14_e2")
        parse(srcs, out_e1); parse(srcs, out_e2)
        e_ok = True
        for did in os.listdir(out_e1):
            d1 = os.path.join(out_e1, did); d2 = os.path.join(out_e2, did)
            for root_, _, files in os.walk(d1):
                for fn in files:
                    p1 = os.path.join(root_, fn)
                    p2 = os.path.join(d2, os.path.relpath(p1, d1))
                    if not os.path.exists(p2) or open(p1, "rb").read() != open(p2, "rb").read():
                        e_ok = False
        details.append("e=双跑字节等含渲染" if e_ok else "e FAIL")
        if not e_ok:
            fails.append("e")

        # f 零回写（tmp 源件 + 冻结三件 ttl/cases/sig）
        after = {p: sha256(p) for p in (self.ttl, self.cases, self.sig)}
        src_after = {p: sha256(p) for p in srcs}
        f_ok = before == after and src_before == src_after
        details.append("f=零回写" if f_ok else "f FAIL")
        if not f_ok:
            fails.append("f")

        # g 边界矩阵（xlsx 公式无缓存/合并单元格 + pptx 备注进 inventory/substrate）
        mx = load(out_a, "票据费率表"); mp = load(out_a, "票据流程")
        mp_blob = json.dumps(mp, ensure_ascii=False)
        g_ok = (any(g["kind"] == "formula-no-cache" for g in mx["gaps"])
                and "=B2*1.1" in json.dumps(mx, ensure_ascii=False)
                and "合计说明" in json.dumps(mx, ensure_ascii=False)
                and "专家口述" in mp_blob  # 备注进 substrate/inventory（非 1.0 heading 子节）
                and "bbox=" in mp_blob)    # PPTX 位置 substrate bbox 坐标
        details.append("g=边界矩阵" if g_ok else "g FAIL")
        if not g_ok:
            fails.append("g")

        # h 清洁 md 零机器锚（全格式正文 grep 机器锚零命中）
        import re as _re
        anchor_pat = _re.compile(r"locator:|extraction:|## \[s|<!--|text_sha256|sensitive_flags")
        h_ok = True
        for did in ("票据贴现制度", "票据费率表", "票据流程", "bill_rule"):
            if anchor_pat.search(md_text(out_a, did)):
                h_ok = False
        if anchor_pat.search(md_text(out_b, "票据样本")):
            h_ok = False
        details.append("h=清洁md零机器锚" if h_ok else "h FAIL")
        if not h_ok:
            fails.append("h")

        # i inventory ground truth（PDF 文本层/XLSX 单元格/DOCX 段落，I3 交叉校验防漏字依据）
        mf = load(out_a, "bill_rule"); mx = load(out_a, "票据费率表"); md_ = load(out_a, "票据贴现制度")
        i_ok = (mf["sections"][0]["inventory"]["kind"] == "pdf-text-layer"
                and any("0.035" in it for it in mf["sections"][0]["inventory"]["items"])
                and mx["sections"][0]["inventory"]["kind"] == "xlsx-cell"
                and any("银票贴现" in it for it in mx["sections"][0]["inventory"]["items"])
                and md_["sections"][0]["inventory"]["kind"] == "docx-paragraph"
                and md_["sections"][0]["inventory"]["count"] > 0)
        details.append("i=inventory-ground-truth" if i_ok else "i FAIL")
        if not i_ok:
            fails.append("i")

        # j 接缝 affordance 准备态（2.1：unit_type/verification_status/md_heading=null，
        #   personal_info_regions=[]，机械层初始化、I2 LLM 回填前恒为准备态，s1-handoff-contract）
        j_ok = True
        for out_, dids in ((out_a, ("票据贴现制度", "票据费率表", "票据流程", "bill_rule")),
                           (out_b, ("票据样本",)), (out_d, ("票据扫描件",))):
            for did in dids:
                for s in load(out_, did)["sections"]:
                    if not (s["unit_type"] is None and s["verification_status"] is None
                            and s["personal_info_regions"] == [] and s["md_heading"] is None):
                        j_ok = False
        details.append("j=接缝affordance准备态" if j_ok else "j FAIL")
        if not j_ok:
            fails.append("j")

        ok = not fails
        self.record("T14", "ingest 2.1 保真进料机械层（10 子例）", "PASS" if ok else "FAIL",
                    "｜".join(details))

    # ---- T15 D3c SPARQL Read 查询模板派生（7 子例，纯 rdflib 内置 SPARQL 1.1，无 Java 无 SKIP）----
    def t15_sparql(self):
        from rdflib import Graph, Literal
        from rdflib.plugins.sparql import prepareQuery
        before = {p: sha256(p) for p in (self.ttl, self.cases, self.sig)}
        derive = self.script("ontology-model", "derive_sparql.py")
        details, fails = [], []

        # 虚构票据 T15 fixture（运行时 tmp 生成，examples 零改动；base bill-discount-test；
        # 6 类〔5 非 derived + Discountable derived ⊑ Bill〕/3 对象/5 数据/1 SWRL/2 hasKey/2 facet + 6 ABox）
        FIX = r'''@prefix : <http://example.org/bill-discount-test#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix swrl: <http://www.w3.org/2003/11/swrl#> .
@prefix swrlb: <http://www.w3.org/2003/11/swrlb#> .

:Bill a owl:Class ; rdfs:label "票据"@zh .
:Acceptor a owl:Class ; rdfs:label "承兑人"@zh .
:Holder a owl:Class ; rdfs:label "持票人"@zh .
:EndorsementRecord a owl:Class ; rdfs:label "背书记录"@zh .
:DiscountApplication a owl:Class ; rdfs:label "贴现申请"@zh .
:Discountable a owl:Class ; rdfs:subClassOf :Bill ; rdfs:label "可贴现票据"@zh .

:currentHolder a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain :Bill ; rdfs:range :Holder .
:hasEndorser a owl:ObjectProperty ; rdfs:domain :EndorsementRecord ; rdfs:range :Holder .
:targetsBill a owl:ObjectProperty ; rdfs:domain :DiscountApplication ; rdfs:range :Bill .

:BillNumberFormat a rdfs:Datatype ; owl:onDatatype xsd:string ; owl:withRestrictions ( [ xsd:pattern "PJ[0-9]{12}" ] ) .
:PositiveAmount a rdfs:Datatype ; owl:onDatatype xsd:decimal ; owl:withRestrictions ( [ xsd:minExclusive "0"^^xsd:decimal ] ) .

:billNumber a owl:DatatypeProperty, owl:FunctionalProperty ; rdfs:domain :Bill ; rdfs:range :BillNumberFormat .
:faceAmount a owl:DatatypeProperty ; rdfs:domain :Bill ; rdfs:range :PositiveAmount .
:applicationStatus a owl:DatatypeProperty ; rdfs:domain :DiscountApplication ; rdfs:range [ rdf:type rdfs:Datatype ; owl:oneOf ( "已提交" "审核中" "已通过" ) ] .
:creditRating a owl:DatatypeProperty ; rdfs:domain :Acceptor ; rdfs:range [ rdf:type rdfs:Datatype ; owl:oneOf ( "AAA" "AA" "A" ) ] .
:unifiedSocialCreditCode a owl:DatatypeProperty ; rdfs:domain :Acceptor ; rdfs:range xsd:string .

:Bill owl:hasKey ( :billNumber ) .
:Acceptor owl:hasKey ( :unifiedSocialCreditCode ) .

:vR1_b a swrl:Variable .
:vR1_m a swrl:Variable .
:ruleR1 a swrl:Imp ;
    swrl:body (
        [ a swrl:ClassAtom ; swrl:classPredicate :Bill ; swrl:argument1 :vR1_b ]
        [ a swrl:DatavaluedPropertyAtom ; swrl:propertyPredicate :faceAmount ; swrl:argument1 :vR1_b ; swrl:argument2 :vR1_m ]
        [ a swrl:BuiltinAtom ; swrl:builtin swrlb:greaterThan ; swrl:arguments ( :vR1_m 100000 ) ]
    ) ;
    swrl:head (
        [ a swrl:ClassAtom ; swrl:classPredicate :Discountable ; swrl:argument1 :vR1_b ]
    ) .

:bill1 a :Bill ; :billNumber "PJ000000000001" ; :faceAmount 150000 ; :currentHolder :holder1 .
:bill2 a :Discountable ; :billNumber "PJ000000000002" ; :faceAmount 80000 ; :currentHolder :holder1 .
:holder1 a :Holder .
:acceptor1 a :Acceptor ; :unifiedSocialCreditCode "91110000TEST0001XX" ; :creditRating "AAA" .
:app1 a :DiscountApplication ; :applicationStatus "审核中" ; :targetsBill :bill1 .
:endorsement1 a :EndorsementRecord ; :hasEndorser :holder1 .
'''
        fix = os.path.join(self.tmp, "t15.fixture.ttl")
        with open(fix, "w", encoding="utf-8") as fh:
            fh.write(FIX)
        src_before = sha256(fix)
        B = "http://example.org/bill-discount-test#"

        # T15a 派生双跑字节一致（json+md+report）+ 19 计数锚（纯 rdflib 无 Java）
        j1 = os.path.join(self.tmp, "t15a.json")
        m1 = os.path.join(self.tmp, "t15a.md")
        r1 = os.path.join(self.tmp, "t15a.report.json")
        j2 = os.path.join(self.tmp, "t15a2.json")
        m2 = os.path.join(self.tmp, "t15a2.md")
        r2 = os.path.join(self.tmp, "t15a2.report.json")
        pa1 = self.py(derive, fix, "--output-json", j1, "--output-md", m1, "--report", r1)
        pa2 = self.py(derive, fix, "--output-json", j2, "--output-md", m2, "--report", r2)
        a_ok = (pa1.returncode == 0 and pa2.returncode == 0 and os.path.exists(j2)
                and open(j1, "rb").read() == open(j2, "rb").read()
                and open(m1, "rb").read() == open(m2, "rb").read()
                and open(r1, "rb").read() == open(r2, "rb").read())
        lib = json.load(open(j1, encoding="utf-8")) if os.path.exists(j1) else None
        if a_ok and lib:
            c = lib["counts"]
            bk = c["by_kind"]
            gaps = lib["coverage"]["gaps"]
            a_ok = (c["classes"] == 6 and c["object_properties"] == 3
                    and c["data_properties"] == 5 and c["templates_total"] == 19
                    and bk.get("class-list") == 5 and bk.get("derived-query") == 1
                    and bk.get("key-lookup") == 2 and bk.get("property-get") == 5
                    and bk.get("enum-filter") == 2 and bk.get("facet-filter") == 1
                    and bk.get("op-join") == 3 and len(gaps) == 1
                    and gaps[0]["kind"] == "pattern-facet-no-regex")
        details.append("a=派生双跑字节一致/19计数锚" if a_ok else "a FAIL")
        if not a_ok:
            fails.append("a")
        tpls = {t["template_id"]: t for t in lib["templates"]} if lib else {}

        # T15b prepareQuery 语法 validity（全 19 模板，套件首个直接 SPARQL 语法消费）
        b_ok = bool(lib)
        if lib:
            try:
                for t in lib["templates"]:
                    prepareQuery(t["sparql"])
            except Exception:
                b_ok = False
        details.append("b=prepareQuery 19/19 valid" if b_ok else "b FAIL")
        if not b_ok:
            fails.append("b")

        # T15c graph.query 执行 5 正例（套件首个直接 graph.query 执行实证）
        #      class-list 闭包 2 / key-lookup 精查 1 / op-join 直接 domain 1 / enum 1 / facet 1
        g = Graph()
        g.parse(fix, format="turtle")

        def run(tid, binds=None):
            res = g.query(tpls[tid]["sparql"], initBindings=binds or {})
            return [tuple(str(v) for v in row) for row in res]

        c_ok = False
        try:
            cl = sorted(x[0] for x in run("q-class-list-Bill"))
            kl = [x[0] for x in run("q-key-lookup-Bill-billNumber",
                                    {"id": Literal("PJ000000000001")})]
            oj = sorted(run("q-op-join-currentHolder"))
            ef = [x[0] for x in run("q-enum-filter-applicationStatus",
                                    {"val": Literal("审核中")})]
            ff = [x[0] for x in run("q-facet-filter-faceAmount",
                                    {"min": Literal(100000), "max": Literal(200000)})]
            c_ok = (cl == [B + "bill1", B + "bill2"] and kl == [B + "bill1"]
                    and oj == [(B + "bill1", B + "holder1")]
                    and ef == [B + "app1"] and ff == [B + "bill1"])
        except Exception:
            c_ok = False
        details.append("c=graph.query执行5正例(闭包2/精查1/traversal1/枚举1/数值1)"
                       if c_ok else "c FAIL")
        if not c_ok:
            fails.append("c")

        # T15d derived-query 注记 + flag + derived 类不产 class-list（执行需 Pellet 不在 T15 断言）
        d_ok = False
        if "q-derived-query-Discountable" in tpls:
            dq = tpls["q-derived-query-Discountable"]
            d_ok = (dq["derived_flag"] is True and "物化" in dq["notes"]
                    and "q-class-list-Discountable" not in tpls)
        details.append("d=derived_flag+需先物化+不产class-list" if d_ok else "d FAIL")
        if not d_ok:
            fails.append("d")

        # T15e 参数化（数据值永不进 sparql 文本）+ IRI 守卫 + enum_values 排序
        IRI_UNSAFE = re.compile(r'''[\s"'<>]''')
        DATA_VALUES = ["PJ000000000001", "PJ000000000002", "审核中", "已提交",
                       "已通过", "AAA", "91110000TEST0001XX", "150000", "80000"]
        e_ok = bool(lib)
        if lib:
            for t in lib["templates"]:
                sp = t["sparql"]
                if any(dv in sp for dv in DATA_VALUES):
                    e_ok = False
                if any(IRI_UNSAFE.search(i) for i in re.findall(r"<([^>]+)>", sp)):
                    e_ok = False
                for p in t.get("params", []):
                    if "enum_values" in p and p["enum_values"] != sorted(p["enum_values"]):
                        e_ok = False
        details.append("e=参数化零泄漏/IRI守卫/enum排序" if e_ok else "e FAIL")
        if not e_ok:
            fails.append("e")

        # T15f 契约错三连：缺文件 / 坏 TTL / 输出 realpath==源 → 各 exit 2 且不产包
        missing = os.path.join(self.tmp, "t15f-missing.ttl")
        bad = os.path.join(self.tmp, "t15f-bad.ttl")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("this is not valid turtle <<< @@@\n")
        xout = os.path.join(self.tmp, "t15f-x.json")
        pf1 = self.py(derive, missing, "--output-json", xout)
        pf2 = self.py(derive, bad, "--output-json", xout)
        pf3 = self.py(derive, fix, "--output-json", fix)
        f_ok = (pf1.returncode == 2 and pf2.returncode == 2 and pf3.returncode == 2
                and not os.path.exists(xout))
        details.append("f=缺文件/坏TTL/输出==源 exit2" if f_ok else "f FAIL")
        if not f_ok:
            fails.append("f")

        # T15g 零回写（tmp fixture + 冻结三件 ttl/cases/sig）
        after = {p: sha256(p) for p in (self.ttl, self.cases, self.sig)}
        g_ok = before == after and sha256(fix) == src_before
        details.append("g=零回写" if g_ok else "g FAIL")
        if not g_ok:
            fails.append("g")

        ok = not fails
        self.record("T15", "D3c SPARQL 查询模板（7 子例）", "PASS" if ok else "FAIL",
                    "｜".join(details))

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
        self.t11_patch()
        self.t12_shacl()
        self.t13_d2d4()
        self.t14_ingest()
        self.t15_sparql()
        n_pass = sum(1 for r in self.results if r[2] == "PASS")
        n_fail = sum(1 for r in self.results if r[2] == "FAIL")
        n_skip = sum(1 for r in self.results if r[2] == "SKIP")
        print("-" * 60)
        print("套件验收：PASS %d / FAIL %d / SKIP %d（SKIP 已登记不计失败）"
              % (n_pass, n_fail, n_skip))
        return 1 if n_fail else 0


def main():
    ap = argparse.ArgumentParser(description="本体能力套件统一验收入口")
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
