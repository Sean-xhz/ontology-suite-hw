#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extract_signature.py —— TTL → 本体签名 JSON（ontology-whatif-compiler 的约束输入）。

签名内容（编译 agent 的「词汇表 + 合法值域」）：
  classes          : id/label/comment/superclasses/hasKey/derived
                     derived := 类出现在任一 SWRL 规则 head 的 classPredicate（结论类，
                     实例输入不得直接断言——结论由推理器产出，机械拦臆造）
  object_properties: id/label/domain/range/functional/transitive/inverseOf
  data_properties  : id/label/domain/range/oneOf_enum/functional
                     oneOf_enum = 受控值（编译 agent 只能从中取值）
  rules            : id/label/body_atoms/head_atoms（agent 理解推理面用，不用于实例断言）
  instance_schema  : 实例 JSON 契约（编译 agent 的输出格式说明，机器消费）

复用：ontology-review/scripts/review_extract.py::parse_ttl（跨 skill import，
      sys.path 垫片指向 ontology-review/scripts）——单一解析实现，禁分叉。

用法：
  python3 extract_signature.py <ontology.ttl> [--output signature.json]

exit 0 成功；exit 1 TTL 解析失败；exit 2 参数错。
"""
import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(_HERE, "../../ontology-review/scripts"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from review_extract import parse_ttl, file_sha  # noqa: E402

INSTANCE_SCHEMA = {
    "说明": "实例 JSON 契约（编译 agent 唯一输出格式；check_instance.py 机械校验）",
    "fields": {
        "scenario": "场景一句话描述（虚构画像摘要，供报告溯源）",
        "individuals": [
            {
                "name": "个体标识（camelCase 英文，如 indBill1；映射为 :name）",
                "classes": ["类 id 列表（必须存在于签名 classes，且不得为 derived）"],
                "facts": {"数据属性id": "字面量值（受控属性必须在 oneOf_enum 内取值）"},
            }
        ],
        "relations": [
            {"prop": "对象属性 id", "from": "个体 name", "to": "个体 name（或受控值属性的目标个体）"}
        ],
        "query": "业务诉求一句话（interpreter 报告的应答目标）",
    },
    "纪律": [
        "零臆造：只能引用签名内的类/属性/受控值，编造即被 check_instance 拦截（exit 1）",
        "derived 类不得出现在 individuals.classes——结论类由推理器物化产出，不进输入",
        "画像虚构：真实客户数据不进模拟（与黄金用例五项遮盖同构）",
    ],
}


def build_signature(ttl_path):
    ttl = parse_ttl(ttl_path)
    if not ttl.get("classes"):
        return None

    # derived 判定：任一规则 head 的 classPredicate（类）/ propertyPredicate（属性）
    head_classes, head_props = set(), set()
    for r in ttl.get("rules", []):
        for atom in r.get("head_atoms", []):
            if not atom.get("predicate"):
                continue
            if atom.get("atom_type") == "ClassAtom":
                head_classes.add(atom["predicate"])
            elif atom.get("atom_type") == "IndividualPropertyAtom":
                head_props.add(atom["predicate"])

    classes = []
    for c in ttl["classes"]:
        entry = {k: c.get(k, "") for k in
                 ("id", "label", "comment", "superclasses", "hasKey")}
        entry["derived"] = c["id"] in head_classes
        classes.append(entry)

    return {
        "source_ttl": os.path.basename(ttl_path),
        "ttl_sha": file_sha(ttl_path),
        "classes": classes,
        "derived_properties": sorted(head_props),
        "object_properties": [
            {k: p.get(k, "") for k in
             ("id", "label", "comment", "domain", "range",
              "domain_union", "range_union",
              "functional", "transitive", "inverseOf")}
            for p in ttl["object_properties"]],
        "data_properties": [
            {k: p.get(k, "") for k in
             ("id", "label", "comment", "domain", "domain_union", "range",
              "oneOf_enum", "functional")}
            for p in ttl["data_properties"]],
        "rules": [
            {k: r.get(k) for k in ("id", "label", "body_atoms", "head_atoms")}
            for r in ttl.get("rules", [])],
        "counts": ttl.get("counts", {}),
        "instance_schema": INSTANCE_SCHEMA,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ttl")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    if not os.path.exists(args.ttl):
        sys.exit("exit 2: TTL 不存在：%s" % args.ttl)

    try:
        sig = build_signature(args.ttl)
    except Exception as exc:  # rdflib 解析失败等
        sys.exit("exit 1: TTL 解析失败：%s" % exc)
    if sig is None:
        sys.exit("exit 1: TTL 无具名类（空本体？）")

    out = args.output or os.path.join(
        os.path.dirname(os.path.abspath(args.ttl)), "signature.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(sig, fh, ensure_ascii=False, indent=1)
    n_derived = sum(1 for c in sig["classes"] if c["derived"])
    print("signature →", out)
    print("类 %d（derived %d）/ 对象属性 %d / 数据属性 %d / 规则 %d" % (
        len(sig["classes"]), n_derived,
        len(sig["object_properties"]), len(sig["data_properties"]),
        len(sig["rules"])))


if __name__ == "__main__":
    main()
