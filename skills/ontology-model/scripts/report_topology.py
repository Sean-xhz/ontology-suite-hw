#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report_topology.py —— 本体 TTL 拓扑报告（S5 结构把关环节的无 Protégé 降级替代）

用法:
    python3 report_topology.py <ontology.ttl>

输出（纯文本，stdout）:
    一、类层级树（缩进树形，根=无 subClassOf 的类；循环处标注 [CYCLE] 防死循环）
    二、对象属性拓扑表（属性名 | domain → range | 特征标注 F/I/T/S/Asym/Irrefl/Refl/inv:Q）
    三、数据属性表（属性名 | domain | range(xsd 类型)）
    四、SWRL 规则清单（每条规则 body/head 的可读摘要：原子谓词+变量名）
    五、实例清单（individuals 按 rdf:type 分组）

退出码: 2=解析失败 / 0=正常。依赖: 仅 rdflib + 标准库。
"""

import argparse
import sys
from collections import defaultdict

from rdflib import Graph, Namespace, OWL, RDF, RDFS, URIRef
from rdflib.collection import Collection

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

VOCAB_NS = {str(OWL), str(RDF), str(RDFS), str(SWRL),
            "http://www.w3.org/2003/11/swrlb#"}

PROP_CHARS = [
    (OWL.FunctionalProperty, "F"),
    (OWL.InverseFunctionalProperty, "I"),
    (OWL.TransitiveProperty, "T"),
    (OWL.SymmetricProperty, "S"),
    (OWL.AsymmetricProperty, "Asym"),
    (OWL.IrreflexiveProperty, "Irrefl"),
    (OWL.ReflexiveProperty, "Refl"),
]


def local_name(iri):
    """取 IRI 局部名；非 URIRef 原样转字符串"""
    if iri is None:
        return "?"
    if not isinstance(iri, URIRef):
        return str(iri)
    s = str(iri)
    if "#" in s:
        return s.rsplit("#", 1)[-1]
    return s.rsplit("/", 1)[-1]


def parse(path):
    g = Graph()
    try:
        g.parse(path, format="turtle")
        return g
    except Exception as exc:
        sys.stderr.write("解析失败: %s\n" % exc)
        sys.exit(2)


def collect_classes(g):
    classes = set(s for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef))
    classes |= set(s for s in g.subjects(RDF.type, RDFS.Class) if isinstance(s, URIRef))
    return classes


def subclass_map(g, classes):
    """父类表：child → set(parents)，仅命名类之间"""
    parents = defaultdict(set)
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            classes.add(s)
            classes.add(o)
            parents[s].add(o)
    return parents


def print_class_tree(g):
    print("== 一、类层级树 ==")
    classes = collect_classes(g)
    parents = subclass_map(g, classes)
    children = defaultdict(set)
    for c in classes:
        for p in parents.get(c, ()):
            children[p].add(c)
    roots = sorted(c for c in classes if not parents.get(c))
    if not roots:
        roots = sorted(classes)  # 全为环时兜底，靠 [CYCLE] 终止

    def walk(node, depth, path):
        mark = ""
        if node in path:
            print("    " * depth + "- " + local_name(node) + " [CYCLE]")
            return
        print("    " * depth + "- " + local_name(node) + mark)
        for ch in sorted(children.get(node, ())):
            walk(ch, depth + 1, path | {node})

    for r in roots:
        walk(r, 0, frozenset())
    if not classes:
        print("    (无类声明)")
    print()


def render_type_node(g, o):
    """domain/range 节点可读化：URIRef 取局部名；bnode 展开 oneOf 值表 /
    unionOf 成员 / onDatatype 基类型（S5 工具观察①：bnode id 不可读）"""
    if isinstance(o, URIRef):
        return local_name(o)
    oneof = g.value(o, OWL.oneOf)
    if oneof is not None:
        try:
            vals = [str(v) for v in Collection(g, oneof)]
            return "oneOf{%s}" % "|".join(vals)
        except Exception:
            return "oneOf{...}"
    union = g.value(o, OWL.unionOf)
    if union is not None:
        try:
            parts = [render_type_node(g, u) for u in Collection(g, union)]
            return "union(%s)" % "|".join(parts)
        except Exception:
            return "union(...)"
    ondt = g.value(o, OWL.onDatatype)
    if ondt is not None:
        return "custom(%s+facet)" % local_name(ondt)
    return "<anon>"


def prop_domain_range(g, p):
    doms = ", ".join(sorted(render_type_node(g, o) for o in g.objects(p, RDFS.domain))) or "-"
    rngs = ", ".join(sorted(render_type_node(g, o) for o in g.objects(p, RDFS.range))) or "-"
    return doms, rngs


def prop_flags(g, p):
    types = set(g.objects(p, RDF.type))
    flags = [tag for cls, tag in PROP_CHARS if cls in types]
    for inv in g.objects(p, OWL.inverseOf):
        flags.append("inv:" + local_name(inv))
    return ",".join(flags) if flags else "-"


def classify_props(g):
    dt_props = set(g.subjects(RDF.type, OWL.DatatypeProperty))
    obj_props = set(g.subjects(RDF.type, OWL.ObjectProperty))
    for cls, _ in PROP_CHARS:
        obj_props |= set(g.subjects(RDF.type, cls))
    obj_props -= dt_props
    return obj_props, dt_props


def print_object_props(g):
    print("== 二、对象属性拓扑表 ==")
    obj_props, _ = classify_props(g)
    print("%-28s | %-24s -> %-24s | %s" % ("属性名", "domain", "range", "特征"))
    print("-" * 90)
    for p in sorted(obj_props, key=str):
        doms, rngs = prop_domain_range(g, p)
        print("%-28s | %-24s -> %-24s | %s"
              % (local_name(p), doms, rngs, prop_flags(g, p)))
    if not obj_props:
        print("(无对象属性)")
    print()


def print_datatype_props(g):
    print("== 三、数据属性表 ==")
    _, dt_props = classify_props(g)
    print("%-28s | %-24s | %s" % ("属性名", "domain", "range(xsd)"))
    print("-" * 70)
    for p in sorted(dt_props, key=str):
        doms, rngs = prop_domain_range(g, p)
        print("%-28s | %-24s | %s" % (local_name(p), doms, rngs))
    if not dt_props:
        print("(无数据属性)")
    print()


# SWRL atom 类型名双规范兼容——
# SWRL 提交规范名（IndividualPropertyAtom/DatavaluedPropertyAtom/BuiltinAtom）
# 与 OWLAPI/OWL 2 映射名（ObjectPropertyAtom/DatatypePropertyAtom/BuiltinsAtom）
# 均合法出现，须同时识别（只认其一会导致另一显示为 <占位符>）
_ATOM_PROP = (SWRL.ObjectPropertyAtom, SWRL.IndividualPropertyAtom)
_ATOM_DATA = (SWRL.DatatypePropertyAtom, SWRL.DatavaluedPropertyAtom)
_ATOM_BUILTIN = (SWRL.BuiltinsAtom, SWRL.BuiltinAtom)


def render_atom(g, atom):
    types = set(g.objects(atom, RDF.type))
    if SWRL.ClassAtom in types:
        return "%s(%s)" % (local_name(g.value(atom, SWRL.classPredicate)),
                           local_name(g.value(atom, SWRL.argument1)))
    if types & set(_ATOM_PROP) or types & set(_ATOM_DATA):
        return "%s(%s, %s)" % (local_name(g.value(atom, SWRL.propertyPredicate)),
                               local_name(g.value(atom, SWRL.argument1)),
                               local_name(g.value(atom, SWRL.argument2)))
    if types & set(_ATOM_BUILTIN):
        args_node = g.value(atom, SWRL.arguments)
        args = []
        if args_node is not None:
            try:
                args = [local_name(a) for a in Collection(g, args_node)]
            except Exception:
                pass
        return "builtin:%s(%s)" % (local_name(g.value(atom, SWRL.builtin)),
                                   ", ".join(args))
    if SWRL.SameIndividualAtom in types or SWRL.DifferentIndividualsAtom in types:
        t = g.value(atom, RDF.type)
        return "%s(%s, %s)" % (local_name(t),
                               local_name(g.value(atom, SWRL.argument1)),
                               local_name(g.value(atom, SWRL.argument2)))
    return "<%s>" % "/".join(sorted(local_name(t) for t in types)) if types else "<无类型atom>"


def print_swrl(g):
    print("== 四、SWRL 规则清单 ==")
    imps = sorted(g.subjects(RDF.type, SWRL.Imp), key=str)
    if not imps:
        print("(无 SWRL 规则)")
        print()
        return
    for idx, imp in enumerate(imps, 1):
        print("规则 #%d:" % idx)
        for part, pname in ((SWRL.body, "body"), (SWRL.head, "head")):
            node = g.value(imp, part)
            atoms = []
            if node is not None and node != RDF.nil:
                try:
                    atoms = [render_atom(g, a) for a in Collection(g, node)]
                except Exception as exc:
                    atoms = ["<列表解析失败: %s>" % exc]
            joiner = " ∧ " if pname == "body" else " → "
            print("    %-4s: %s" % (pname, joiner.join(atoms) if atoms else "(空/缺失)"))
        # 可读整体式：body → head
        b, h = g.value(imp, SWRL.body), g.value(imp, SWRL.head)
        try:
            b_atoms = [render_atom(g, a) for a in Collection(g, b)] if b is not None else []
            h_atoms = [render_atom(g, a) for a in Collection(g, h)] if h is not None else []
        except Exception:
            b_atoms, h_atoms = [], []
        if b_atoms or h_atoms:
            print("    摘要: %s → %s" % (" ∧ ".join(b_atoms) or "(空)",
                                        " ∧ ".join(h_atoms) or "(空)"))
    print()


def print_individuals(g):
    print("== 五、实例清单（按 rdf:type 分组） ==")
    groups = defaultdict(set)
    for s, o in g.subject_objects(RDF.type):
        if isinstance(o, URIRef) and not any(str(o).startswith(ns) for ns in VOCAB_NS):
            groups[o].add(s)
    if not groups:
        print("(无实例)")
    for t in sorted(groups, key=str):
        names = ", ".join(sorted(local_name(s) for s in groups[t]))
        print("%s (%d): %s" % (local_name(t), len(groups[t]), names))
    print()


def main():
    parser = argparse.ArgumentParser(
        description="本体 TTL 拓扑报告（类树/属性表/SWRL 清单/实例分组，无 Protégé 降级替代）")
    parser.add_argument("ontology", help="本体 TTL 文件路径")
    args = parser.parse_args()

    g = parse(args.ontology)
    print("本体拓扑报告: %s" % args.ontology)
    print("三元组总数: %d" % len(g))
    print()
    print_class_tree(g)
    print_object_props(g)
    print_datatype_props(g)
    print_swrl(g)
    print_individuals(g)
    sys.exit(0)


if __name__ == "__main__":
    main()
