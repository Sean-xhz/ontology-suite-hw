#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ab_score.py —— A/B 三臂实验机械判据 + 盲评表单生成 + 聚合。

设计纪律（确定性事实用规则判断；CEUR-4079 结论：
LLM-as-judge 在结构化知识上不可靠 → 机械判据只做确定性核对，语义质量交专家盲评）：

  score 模式（应答 → 机械判据 + 盲评表单）：
    - label 匹配（L2/L3 判定题）/ key_points 覆盖率（L1 事实题）
    - 规则引用真实性（引用的 R 编号在 TTL 存在）与 gold 命中率
    - 幻觉计数（应答引用的构件名不在本体词汇表）
    - 盲评表单：三臂应答乱序代名（A/B/C，seed=42 确定性可复现），
      映射表另落 key.json（仅主会话持有，表单不露臂别）
  aggregate 模式（盲评分数回收 → 聚合）：
    - 每臂×维度均值/中位数 + 两专家逐题一致率 + 代号还原臂别

应答文件命名：<answers>/Q01-arm1.json（arm1=本体臂 arm2=描述集臂 arm3=裸臂）。
机械判据盲区如实登记：裸臂编造「恰好存在于 TTL 的 R 编号」真实性判据无法
检出（编号真实但依据是虚构的）——该盲区由专家盲评补，score.json 记录在案。

用法：
  python3 ab_score.py score --questionbank qb.json --answers 应答/ --ttl ontology.ttl --output-dir 评分/
                            [--carrier 载体名 --form-note 表单头部纪律行]
  python3 ab_score.py aggregate --scores 盲评分数.json --key 评分/key.json [--output 聚合报告.md]

载体中立：表单标题载体名经 --carrier 传入（缺省=虚构示例载体；
复现历史 run 表单时显式传入原载体名）；真实载体 run 必须传 --form-note 声明内部流转纪律。
exit 0 正常；1 数据错误（缺应答/题库 schema 错）；2 环境/参数错。
"""
import argparse
import json
import os
import random
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# 跨 skill import（禁分叉纪律）：复用 ontology-review 的 TTL 解析
sys.path.insert(0, os.path.join(HERE, "..", "..", "ontology-review", "scripts"))
import review_extract as RX  # noqa: E402

CAMEL = re.compile(r"\b[A-Z][a-zA-Z0-9]{2,}\b")
# 族号口径：不带尾 \b——「R15a/R18k」等后缀分支编号
# 取前导数字为族号（与 build_vocab 的 ruleR(\d+) 口径一致；无后缀 gold 不受影响）
RNUM = re.compile(r"\bR(\d+)")
# 本体词汇白名单外的常见英文误报词（应答纪律允许的普通词）
COMMON_WORDS = {"JSON", "AAA", "AA", "AcceptableApplication"}  # AAA/AA 另由受控值表覆盖


def norm(s):
    """归一化：去空白/全角空格，小写——key_point 子串匹配用。"""
    return re.sub(r"[\s　]+", "", str(s)).lower()


def build_vocab(ttl_path):
    """TTL → 构件词汇表（local name 集合 + R 编号集合 + 受控值集合）。"""
    ttl = RX.parse_ttl(ttl_path)
    words, rnums = set(), set()
    for c in ttl["classes"]:
        words.add(c["id"])
    for p in ttl["object_properties"] + ttl["data_properties"]:
        words.add(p["id"])
    for r in ttl["rules"]:
        rid = r["id"]
        words.add(rid)
        m = re.match(r"ruleR(\d+)", rid)
        if m:
            rnums.add(int(m.group(1)))
    # 受控值（oneOf 枚举字面量）
    for p in ttl["data_properties"]:
        for v in p.get("enum_values") or []:
            words.add(str(v))
    return words, rnums


def text_of(resp):
    """应答 JSON → 判分用全文（explanation + evidence notes + refs）。"""
    parts = [resp.get("conclusion", {}).get("explanation", "")]
    for e in resp.get("evidence") or []:
        parts.append(str(e.get("ref", "")))
        parts.append(str(e.get("note", "")))
    return "\n".join(parts)


def refs_of(resp):
    """应答引用的构件 ref 列表（type 非 common_sense/not_covered 的）。"""
    return [str(e.get("ref", "")) for e in resp.get("evidence") or []
            if e.get("type") not in ("common_sense", "not_covered")]


def score_one(q, resp, vocab, rnums):
    """单题×单应答机械判据 → dict。"""
    out = {"qid": q["id"], "layer": q["layer"], "kind": q.get("kind", "judge"),
           "parse_ok": True, "label_match": None, "kp_coverage": None,
           "rule_refs_true": None, "rule_refs_gold": None, "hallucinations": []}
    if resp is None:
        out.update(parse_ok=False)
        return out
    gold = q.get("gold") or {}
    label = (resp.get("conclusion") or {}).get("label")
    full = text_of(resp)
    nfull = norm(full)
    # 1. label 匹配（fact 题跳过——考要点覆盖）
    if gold.get("label") and gold["label"] != "fact":
        out["label_match"] = (label == gold["label"])
    # 2. key_points 覆盖率（子串匹配，归一化）
    kps = gold.get("key_points") or []
    if kps:
        hit = sum(1 for k in kps if norm(k) in nfull)
        out["kp_coverage"] = round(hit / len(kps), 3)
    # 3. 规则引用：真实性（R 编号在 TTL）+ gold 命中
    cited = {int(m.group(1)) for r in refs_of(resp) + [full]
             for m in RNUM.finditer(str(r))}
    if cited:
        out["rule_refs_true"] = sorted(c for c in cited if c in rnums)
        gold_rs = {int(m.group(1)) for g in gold.get("rule_refs") or []
                   for m in [re.match(r"R(\d+)", str(g))] if m}
        out["rule_refs_gold"] = sorted(cited & gold_rs)
        out["rule_refs_fake"] = sorted(c for c in cited if c not in rnums)
    # 4. 幻觉计数：refs+全文中的 CamelCase/R 编号不在词汇表
    halluc = set()
    for token_src in refs_of(resp) + [full]:
        for t in CAMEL.findall(str(token_src)):
            if t not in vocab and t not in COMMON_WORDS:
                halluc.add(t)
        for m in RNUM.finditer(str(token_src)):
            if "R" + m.group(1) not in vocab and int(m.group(1)) not in rnums:
                halluc.add("R" + m.group(1))
    out["hallucinations"] = sorted(halluc)
    return out


def arm_aggregate(rows):
    """单臂全部题目判分行 → 聚合指标。"""
    judged = [r for r in rows if r["label_match"] is not None]
    facts = [r for r in rows if r["kp_coverage"] is not None]
    halluc_total = sum(len(r["hallucinations"]) for r in rows)
    fake_total = sum(len(r.get("rule_refs_fake") or []) for r in rows)
    return {
        "n": len(rows),
        "parse_fail": sum(1 for r in rows if not r["parse_ok"]),
        "label_accuracy": (round(sum(r["label_match"] for r in judged) / len(judged), 3)
                           if judged else None),
        "kp_coverage_mean": (round(statistics.mean(r["kp_coverage"] for r in facts), 3)
                             if facts else None),
        "rule_ref_fake_total": fake_total,
        "hallucination_total": halluc_total,
        "hallucination_detail": sorted({h for r in rows for h in r["hallucinations"]}),
    }


def cmd_score(args):
    qb = json.load(open(args.questionbank, encoding="utf-8"))
    if "questions" not in qb or "meta" not in qb:
        sys.exit("exit 1: 题库 schema 缺 meta/questions")
    vocab, rnums = build_vocab(args.ttl)
    os.makedirs(args.output_dir, exist_ok=True)
    answers = {}
    all_rows = {"arm1": [], "arm2": [], "arm3": []}
    missing = []
    for q in qb["questions"]:
        for arm in ("arm1", "arm2", "arm3"):
            path = os.path.join(args.answers, "%s-%s.json" % (q["id"], arm))
            resp = None
            if os.path.exists(path):
                try:
                    resp = json.load(open(path, encoding="utf-8"))
                except json.JSONDecodeError as e:
                    resp = None
                    print("WARN 应答 JSON 解析失败 %s: %s" % (path, e))
            else:
                missing.append(os.path.basename(path))
            answers[(q["id"], arm)] = resp
            row = score_one(q, resp, vocab, rnums)
            row["arm"] = arm
            all_rows[arm].append(row)
    if missing:
        print("WARN 缺应答 %d 份: %s" % (len(missing), missing[:6]))
    result = {
        "meta": {
            "questionbank": os.path.basename(args.questionbank),
            "frozen_sha": qb["meta"].get("frozen_sha"),
            "ontology_sha": qb["meta"].get("ontology_sha"),
            "scorer": "ab_score.py v1.0",
            "blind_spot": "裸臂编造恰好存在于 TTL 的 R 编号时真实性判据不检出——由专家盲评补",
        },
        "per_question": all_rows,
        "arm_summary": {arm: arm_aggregate(rows) for arm, rows in all_rows.items()},
    }
    with open(os.path.join(args.output_dir, "score.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    # 盲评表单（三臂乱序代名，seed=42 确定性）+ key.json（仅主会话持有）
    rng = random.Random(42)
    form_parts = ["# A/B 盲评表单（%s）" % args.carrier, ""]
    if args.form_note:
        form_parts += ["> **%s**" % args.form_note, ""]
    form_parts += ["> 评分说明：每题给出三份应答（代号 A/B/C，顺序随机）。请对每份应答按三个维度打 1-5 分：",
                   "> **业务正确性**（结论与依据是否符合业务事实）/ **解释质量**（业务人员能否直读、逻辑是否清楚）/ **依据充分性**（依据是否具体可核、有无编造痕迹）。可加一句评语。",
                   "> 请勿尝试猜测应答来源；三份应答回答的是同一道题。",
                   ""]
    key = {}
    for q in qb["questions"]:
        codes = ["A", "B", "C"]
        rng.shuffle(codes)
        mapping = {}  # code -> arm
        for arm, code in zip(("arm1", "arm2", "arm3"), codes):
            mapping[code] = arm
        key[q["id"]] = mapping
        form_parts.append("---\n\n## %s（%s）\n" % (q["id"], q["layer"]))
        form_parts.append("**情境**：%s\n" % q.get("scenario", "—"))
        form_parts.append("**问题**：%s\n" % q["question"])
        for code in ("A", "B", "C"):
            arm = mapping[code]
            resp = answers[(q["id"], arm)]
            if resp is None:
                body = "（应答缺失）"
            else:
                c = resp.get("conclusion") or {}
                ev = "\n".join("- [%s] %s：%s" % (e.get("type", "?"), e.get("ref", ""),
                                                    e.get("note", ""))
                               for e in resp.get("evidence") or []) or "-（无）"
                body = ("**结论**（%s）：%s\n\n**依据**：\n%s\n\n**置信度**：%s"
                        % (c.get("label", "?"), c.get("explanation", "—"), ev,
                           resp.get("confidence", "?")))
            form_parts.append("\n### 应答 %s\n\n%s\n\n**评分**：业务正确性 __/5 ｜ 解释质量 __/5 ｜ 依据充分性 __/5 ｜ 评语：______\n" % (code, body))
    with open(os.path.join(args.output_dir, "盲评表单.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(form_parts))
    with open(os.path.join(args.output_dir, "key.json"), "w", encoding="utf-8") as fh:
        json.dump(key, fh, ensure_ascii=False, indent=1)
    print("score.json / 盲评表单.md / key.json → %s" % args.output_dir)
    for arm, s in result["arm_summary"].items():
        print("  %s: label 正确率=%s 要点覆盖=%s 幻觉=%d 编造R编号=%d"
              % (arm, s["label_accuracy"], s["kp_coverage_mean"],
                 s["hallucination_total"], s["rule_ref_fake_total"]))


def cmd_aggregate(args):
    key = json.load(open(args.key, encoding="utf-8"))
    scores = json.load(open(args.scores, encoding="utf-8"))
    # scores schema: [{"expert":"E1","qid":"Q01","code":"A","correctness":4,"explanation":4,"evidence":3,"comment":"..."}]
    per_arm = {}   # arm -> {dim: [vals]}
    per_expert_q = {}  # (expert,qid,arm) -> {dim:val}
    dims = ("correctness", "explanation", "evidence")
    for row in scores:
        arm = (key.get(row["qid"]) or {}).get(row["code"])
        if arm is None:
            print("WARN 无法还原代号 qid=%s code=%s" % (row["qid"], row["code"]))
            continue
        per_arm.setdefault(arm, {d: [] for d in dims})
        for d in dims:
            v = row.get(d)
            if isinstance(v, (int, float)):
                per_arm[arm][d].append(v)
        per_expert_q[(row.get("expert"), row["qid"], arm)] = {d: row.get(d) for d in dims}
    # 两专家一致率：同 qid×arm×维度，两专家都打了分的条目中分数相等占比
    by_qa = {}
    for (exp, qid, arm), vals in per_expert_q.items():
        by_qa.setdefault((qid, arm), []).append((exp, vals))
    agree = total = 0
    for pairs in by_qa.values():
        if len(pairs) < 2:
            continue
        for d in dims:
            vs = [v.get(d) for _, v in pairs[:2] if isinstance(v.get(d), (int, float))]
            if len(vs) == 2:
                total += 1
                agree += (vs[0] == vs[1])
    lines = ["# A/B 盲评聚合", "",
             "| 臂 | 业务正确性 | 解释质量 | 依据充分性 | 样本 |", "|---|---|---|---|---|"]
    arm_names = {"arm1": "①本体臂", "arm2": "②描述集臂", "arm3": "③裸臂"}
    for arm in ("arm1", "arm2", "arm3"):
        d = per_arm.get(arm)
        if not d:
            lines.append("| %s | — | — | — | 0 |" % arm_names[arm])
            continue
        def fmt(vals):
            if not vals:
                return "—"
            return "%.2f (中位 %.1f)" % (statistics.mean(vals), statistics.median(vals))
        lines.append("| %s | %s | %s | %s | %d |" % (
            arm_names[arm], fmt(d["correctness"]), fmt(d["explanation"]),
            fmt(d["evidence"]), len(d["correctness"])))
    lines += ["", "两专家逐题×维度一致率：%s（%d/%d，小样本仅供参考）"
              % ("%.0f%%" % (100.0 * agree / total) if total else "—", agree, total),
              "", "> 纪律：未过 AG2 终审的数字不入任何对外材料；本聚合不支撑「本体无用/万能」式泛化结论。"]
    report = "\n".join(lines)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
        print(report)
        print("\n→ %s" % args.output)
    else:
        print(report)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--questionbank", required=True)
    s.add_argument("--answers", required=True, help="应答目录（Q01-arm1.json 形态）")
    s.add_argument("--ttl", required=True)
    s.add_argument("--output-dir", required=True)
    s.add_argument("--carrier", default="虚构示例载体",
                   help="盲评表单标题的载体名（真实载体 run 应如实标注）")
    s.add_argument("--form-note", default=None,
                   help="盲评表单头部附加纪律行（真实载体 run 必传内部流转声明）")
    a = sub.add_parser("aggregate")
    a.add_argument("--scores", required=True, help="盲评分数 JSON（expert/qid/code/三维度）")
    a.add_argument("--key", required=True, help="score 模式产出的 key.json")
    a.add_argument("--output", default=None)
    args = ap.parse_args()
    if args.cmd == "score":
        cmd_score(args)
    else:
        cmd_aggregate(args)


if __name__ == "__main__":
    main()
