#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_instance.py —— 实例 JSON 机械校验（拦臆造的硬门禁，SG1 的机器侧）。

校验项（全部对照 signature.json）：
  E01 实例 JSON 结构（顶层字段/individuals 列表）
  E02 个体 name 唯一且为合法标识符（camelCase，映射为 :name）
  E03 类引用存在性——classes[] 中每个 id 必须在签名 classes
  E04 结论越权——derived 类不得出现在实例输入（结论由推理器物化产出）
  E05 数据属性存在性——facts 的 key 必须是签名 data_properties
  E06 数据属性 domain 兼容——实例某 class 须为属性 domain 或其后代
  E07 受控值——oneOf_enum 属性的值必须在枚举内
  E08 字面量类型——xsd 基型形态校验（integer/decimal/boolean/date）；具名
      datatype（pattern 类，如 ApplicationNumberFormat）只 WARN 不 FAIL
      （facet 校验由 ontology-model SHACL 层〔R4，derive_shacl+validate_shacl〕承接，
      模拟侧不做——限制⑩对偶登记）
  E09 对象属性存在性+domain/range 兼容+个体引用存在性
  E10 推导属性越权——规则 head 的 propertyPredicate（如 isUpstreamOf）是推导结论，
      不得出现在 relations 输入（与 E04 同语义：结论由推理器物化产出）

输出：校验报告（stdout + 可选 --json-output violations.json）
exit 0 = 无 error（warning 允许）；exit 1 = 存在 error；exit 2 = 参数/IO 错。

用法：
  python3 check_instance.py <instance.json> <signature.json> [--json-output FILE]
"""
import argparse
import json
import os
import re
import sys

NAME_RE = re.compile(r"^[a-z][A-Za-z0-9_]*$")
XSD_PATTERNS = {
    "integer": re.compile(r"^-?\d+$"),
    "decimal": re.compile(r"^-?\d+(\.\d+)?$"),
    "double": re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$"),
    "boolean": re.compile(r"^(true|false)$"),
    "date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "dateTime": re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"),
    "string": None,  # 任意
}


def load_json(path, code="E00"):
    if not os.path.exists(path):
        sys.exit("exit 2: 文件不存在：%s" % path)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        sys.exit("exit 2: JSON 解析失败（%s）：%s" % (path, exc))


def ancestors(sig, class_id):
    """class_id 的祖先闭包（含自身）——用 superclasses 逐级上溯。"""
    by_id = {c["id"]: c for c in sig["classes"]}
    seen, stack = {class_id}, [class_id]
    while stack:
        cur = by_id.get(stack.pop())
        if not cur:
            continue
        for sup in cur.get("superclasses") or []:
            if sup and sup not in seen:
                seen.add(sup)
                stack.append(sup)
    return seen


def domain_ok(sig, class_ids, domain, union=None):
    """实例的任一类 ∈ domain 或其后代。domain 空视为不限。
    union 非空 = domain/range 为匿名 owl:unionOf 类表达式（bnode ID 不可
    直接判定）——按「实例任一类 ∈ 任一联合成员或其后代」判定。"""
    if union:
        closure = set()
        for m in union:
            closure |= ancestors(sig, m)
        return any(cid in closure for cid in class_ids)
    if not domain:
        return True
    dom_desc = ancestors(sig, domain)
    return any(cid in dom_desc for cid in class_ids)


def check_instance(inst, sig):
    """返回 (errors, warnings)——违反项列表。"""
    errors, warnings = [], []

    def err(code, msg):
        errors.append({"level": "error", "code": code, "message": msg})

    def warn(code, msg):
        warnings.append({"level": "warning", "code": code, "message": msg})

    # ---- 结构
    if not isinstance(inst, dict):
        err("E01", "实例顶层必须是 JSON 对象")
        return errors, warnings
    for field in ("scenario", "individuals", "query"):
        if field not in inst:
            err("E01", "缺顶层字段 %s" % field)
    individuals = inst.get("individuals") or []
    relations = inst.get("relations") or []
    if not individuals:
        err("E01", "individuals 为空——what-if 至少需要一个个体")
        return errors, warnings

    cls_by_id = {c["id"]: c for c in sig["classes"]}
    dp_by_id = {p["id"]: p for p in sig["data_properties"]}
    op_by_id = {p["id"]: p for p in sig["object_properties"]}

    # ---- 个体
    seen_names = {}
    for ind in individuals:
        name = ind.get("name", "")
        if not NAME_RE.match(name or ""):
            err("E02", "个体名非法（须 camelCase 英文）：%r" % name)
            continue
        if name in seen_names:
            err("E02", "个体名重复：%s" % name)
            continue
        seen_names[name] = ind

        class_ids = ind.get("classes") or []
        if not class_ids:
            err("E03", "个体 %s 未声明任何类" % name)
        for cid in class_ids:
            if cid not in cls_by_id:
                err("E03", "个体 %s 引用不存在的类：%s（臆造拦截）" % (name, cid))
            elif cls_by_id[cid].get("derived"):
                err("E04", "个体 %s 断言了 derived 结论类 %s（%s）——结论类由推理器物化产出，"
                           "不得进入实例输入" % (name, cid, cls_by_id[cid].get("label", "")))

        # ---- facts
        for key, val in (ind.get("facts") or {}).items():
            prop = dp_by_id.get(key)
            if prop is None:
                err("E05", "个体 %s 引用不存在的数据属性：%s（臆造拦截）" % (name, key))
                continue
            if not domain_ok(sig, class_ids, prop.get("domain"),
                             prop.get("domain_union")):
                err("E06", "属性 %s 的 domain=%s，个体 %s 的类 %s 不兼容"
                           % (key, prop.get("domain"), name, class_ids))
            enum = prop.get("oneOf_enum")
            if enum:
                if str(val) not in enum:
                    err("E07", "属性 %s 是受控值属性，%r 不在枚举 %s 内"
                               % (key, val, enum))
                continue
            rng = prop.get("range") or "string"
            pat = XSD_PATTERNS.get(rng)
            if rng in XSD_PATTERNS:
                if pat is not None and not isinstance(val, (bool, int, float)):
                    if not pat.match(str(val)):
                        err("E08", "属性 %s 类型 %s 不符：%r" % (key, rng, val))
            else:
                warn("W08", "属性 %s 为具名 datatype %s（pattern 类）——模拟侧不做 "
                            "facet 校验（SHACL 层 R4 承接），值 %r 未验证" % (key, rng, val))

    # ---- 关系
    derived_props = set(sig.get("derived_properties") or [])
    for rel in relations:
        prop = op_by_id.get(rel.get("prop", ""))
        if rel.get("prop") in derived_props:
            err("E10", "关系 %r 是推导结论属性（规则 head）——由推理器物化产出，"
                       "不得进入实例输入（写业务数据让规则自推）" % rel.get("prop"))
            continue
        if prop is None:
            # 受控值型对象属性误用也在此拦截（如把数据属性写进 relations）
            err("E09", "关系引用不存在的对象属性：%r（臆造拦截）" % rel.get("prop"))
            continue
        src, dst = rel.get("from"), rel.get("to")
        if src not in seen_names:
            err("E09", "关系 %s 的 from 个体不存在：%r" % (rel.get("prop"), src))
            continue
        if dst not in seen_names:
            err("E09", "关系 %s 的 to 个体不存在：%r" % (rel.get("prop"), dst))
            continue
        src_classes = seen_names[src].get("classes") or []
        if not domain_ok(sig, src_classes, prop.get("domain"),
                         prop.get("domain_union")):
            err("E09", "关系 %s 的 domain=%s，个体 %s 的类 %s 不兼容"
                       % (rel.get("prop"), prop.get("domain"), src, src_classes))
        dst_classes = seen_names[dst].get("classes") or []
        if not domain_ok(sig, dst_classes, prop.get("range"),
                         prop.get("range_union")):
            err("E09", "关系 %s 的 range=%s，个体 %s 的类 %s 不兼容"
                       % (rel.get("prop"), prop.get("range"), dst, dst_classes))

    return errors, warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_json")
    ap.add_argument("signature_json")
    ap.add_argument("--json-output", default=None)
    args = ap.parse_args()

    inst = load_json(args.instance_json)
    sig = load_json(args.signature_json)

    errors, warnings = check_instance(inst, sig)
    report = {
        "instance": os.path.basename(args.instance_json),
        "signature_sha": sig.get("ttl_sha"),
        "pass": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {"individuals": len(inst.get("individuals") or []),
                   "relations": len(inst.get("relations") or []),
                   "error": len(errors), "warning": len(warnings)},
    }

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)

    print("校验结果：%s（error %d / warning %d / 个体 %d / 关系 %d）" % (
        "通过" if not errors else "不通过",
        len(errors), len(warnings),
        report["counts"]["individuals"], report["counts"]["relations"]))
    for v in errors:
        print("  [error %s] %s" % (v["code"], v["message"]))
    for v in warnings:
        print("  [warn  %s] %s" % (v["code"], v["message"]))

    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
