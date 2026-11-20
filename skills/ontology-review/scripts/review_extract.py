#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review_extract.py —— 审阅层数据提取（双源，TTL 为权威）。

输入：ontology run 目录（含 ontology.ttl + 建模方案.md）
输出：review.json —— build_review_page.py 的唯一数据源

双源设计（md 表解析脆弱风险的缓解）：
  - TTL 层（权威）：rdflib 解析——类/属性/公理/规则/SKOS 的结构事实
  - md 层（专家语言）：建模方案表解析——自然语言陈述/源句编号/违反处置
    解析失败降级：构件缺专家字段时标 "md_missing"，TTL 结构仍在（显式报错不静默）

用法：
  python3 review_extract.py <run目录> [--output review.json]

exit 0 成功（含降级）；exit 1 致命（TTL 解析失败）；exit 2 参数错。
"""
import argparse
import hashlib
import json
import os
import re
import sys
from collections import deque

import rdflib
from rdflib import RDF, RDFS, OWL, XSD, BNode, URIRef, Literal
from rdflib.namespace import Namespace

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = Namespace("http://www.w3.org/2003/11/swrlb#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

# review.json 子协议版本（独立登记，不联动 skill 版本；1.3.0 批次 1.0→1.1：
# 新增 supply 供给层〔D2 六图 + D4 编辑〕+ meta.sources.ttl.sha256_full）。
# 模板守卫 DATA.schema_version||"1.0"；legacy（无 supply）→D2 hint/D4 禁用。
REVIEW_JSON_SCHEMA = "1.1"


def local(n):
    s = str(n)
    for sep in ("#", "/"):
        if sep in s:
            s = s.rsplit(sep, 1)[1]
    return s


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def file_sha_full(path):
    """全 64 位 sha256（D4 patch baseline.sha256 须 64hex，R2 validate_patch
    fullmatch；12 位 file_sha 不动——意见导出链 HTML→ingest_opinions 消费）。"""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- TTL 层

def rdf_list_items(g, node):
    items = []
    while node is not None and isinstance(node, BNode):
        first = g.value(node, RDF.first)
        if first is not None:
            items.append(first)
        node = g.value(node, RDF.rest)
    return items


def parse_oneof_enum(g, range_node):
    """数据属性 range 指向匿名 onDatatype+oneOf bnode → 枚举值列表。"""
    if not isinstance(range_node, BNode):
        return None
    oneof = g.value(range_node, OWL.oneOf)
    if oneof is None:
        return None
    return [str(v) for v in rdf_list_items(g, oneof)]


def union_class_members(g, node):
    """domain/range 节点为匿名 owl:unionOf bnode → 成员类 ID 列表；否则 []。
    S3 裁量登记的联合值域形态（如某对象属性值域为 企业∪个人 的匿名 union），
    供 check_instance E06/E09 做 domain/range 兼容判定——须输出成员类 ID
    而非 bnode ID，否则兼容判定误报。"""
    if not isinstance(node, BNode):
        return []
    union = g.value(node, OWL.unionOf)
    if union is None:
        return []
    return [local(m) for m in rdf_list_items(g, union)
            if isinstance(m, URIRef)]


def _arg_str(g, a):
    """atom 实参 → 字符串。变量（swrl:Variable）加 ? 前缀（SWRL 标准记法，
    也是下游 plain_swrl 的变量判据——? 前缀使变量与类名可区分，
    保障通俗翻译的变量重命名与图例正确）；字面量原样。"""
    if a is None:
        return "?"
    if isinstance(a, Literal):
        return str(a)
    if g.value(a, RDF.type) == SWRL.Variable:
        return "?" + local(a)
    return local(a)


def parse_atoms(g, imp, pred):
    """swrl:Imp 的 body/head → 原子结构列表（专家可读呈现的 TTL 通道）。"""
    atoms = []
    lst = g.value(imp, pred)
    for atom in rdf_list_items(g, lst):
        if not isinstance(atom, BNode):
            continue
        atom_type = None
        for t in g.objects(atom, RDF.type):
            if str(t).startswith(str(SWRL)):
                atom_type = local(t)
        entry = {"atom_type": atom_type}
        cp = g.value(atom, SWRL.classPredicate)
        pp = g.value(atom, SWRL.propertyPredicate)
        bl = g.value(atom, SWRL.builtin)
        if cp is not None:
            entry["predicate"] = local(cp)
        elif pp is not None:
            entry["predicate"] = local(pp)
        elif bl is not None:
            entry["predicate"] = "swrlb:" + local(bl)
        args_node = g.value(atom, SWRL.arguments)
        if args_node is not None:
            entry["arguments"] = [_arg_str(g, a)
                                  for a in rdf_list_items(g, args_node)]
        else:
            a1 = g.value(atom, SWRL.argument1)
            a2 = g.value(atom, SWRL.argument2)
            args = []
            if a1 is not None:
                args.append(_arg_str(g, a1))
            if a2 is not None:
                args.append(_arg_str(g, a2))
            entry["arguments"] = args
        atoms.append(entry)
    return atoms


def parse_ttl(ttl_path):
    g = rdflib.Graph()
    g.parse(ttl_path, format="turtle")
    base_ns = str(g.base or "")
    if not base_ns:
        # @base 缺省时用首个具名类 namespace 猜测
        for c in g.subjects(RDF.type, OWL.Class):
            if isinstance(c, URIRef) and "example" in str(c):
                base_ns = str(c).rsplit(local(c), 1)[0]
                break

    def in_base(n):
        return isinstance(n, URIRef) and str(n).startswith(base_ns)

    ttl = {"classes": [], "object_properties": [], "data_properties": [],
           "rules": [], "skos_concepts": [], "skos_scheme": None,
           "counts": {}}

    for c in sorted(g.subjects(RDF.type, OWL.Class), key=str):
        if not in_base(c):
            continue
        key_props = []
        for hk in g.objects(c, OWL.hasKey):
            key_props = [local(p) for p in rdf_list_items(g, hk)]
        sup = [local(s) for s in g.objects(c, RDFS.subClassOf)
               if isinstance(s, URIRef) and not str(s).startswith(str(SWRL))]
        ttl["classes"].append({
            "id": local(c), "iri": str(c),
            "label": str(g.value(c, RDFS.label) or ""),
            "comment": str(g.value(c, RDFS.comment) or ""),
            "superclasses": sup, "hasKey": key_props,
        })

    for p in sorted(g.subjects(RDF.type, OWL.ObjectProperty), key=str):
        if not in_base(p):
            continue
        types = {local(t) for t in g.objects(p, RDF.type)}
        inv = g.value(p, OWL.inverseOf)
        dom, rng = g.value(p, RDFS.domain), g.value(p, RDFS.range)
        ttl["object_properties"].append({
            "id": local(p),
            "label": str(g.value(p, RDFS.label) or ""),
            "comment": str(g.value(p, RDFS.comment) or ""),
            # 确定性纪律：具名字段只承载具名 IRI localname；匿名类表达式
            # （unionOf 等）→ 空串，联合成员经 domain_union/range_union 承载
            # （rdflib bnode 标签跨进程随机，禁入输出）
            "domain": local(dom) if isinstance(dom, URIRef) else "",
            "range": local(rng) if isinstance(rng, URIRef) else "",
            "domain_union": union_class_members(g, dom),
            "range_union": union_class_members(g, rng),
            "inverseOf": local(inv) if isinstance(inv, URIRef) else "",
            "functional": "FunctionalProperty" in types,
            "transitive": "TransitiveProperty" in types,
        })

    for p in sorted(g.subjects(RDF.type, OWL.DatatypeProperty), key=str):
        if not in_base(p):
            continue
        types = {local(t) for t in g.objects(p, RDF.type)}
        rng = g.value(p, RDFS.range)
        dom = g.value(p, RDFS.domain)
        enum = parse_oneof_enum(g, rng) if rng is not None else None
        rng_str = local(rng) if isinstance(rng, URIRef) else ""
        ttl["data_properties"].append({
            "id": local(p),
            "label": str(g.value(p, RDFS.label) or ""),
            "comment": str(g.value(p, RDFS.comment) or ""),
            "domain": local(dom) if isinstance(dom, URIRef) else "",
            "domain_union": union_class_members(g, dom),
            "range": rng_str, "oneOf_enum": enum,
            "functional": "FunctionalProperty" in types,
        })

    variables = {str(v): local(v) for v in g.subjects(RDF.type, SWRL.Variable)}
    for imp in sorted(g.subjects(RDF.type, SWRL.Imp), key=str):
        body = parse_atoms(g, imp, SWRL.body)
        head = parse_atoms(g, imp, SWRL.head)
        # variables=本规则真实变量名（? 前缀，与 arguments 记法一致，排序去重）。
        # 从已解析 atom 实参导出（单一解析源）——确定性纪律：bnode 随机标签
        # 禁入确定性输出（跨进程漂移）。
        rule_vars = sorted({a for atom in body + head
                            for a in atom.get("arguments", [])
                            if a.startswith("?") and len(a) > 1})
        ttl["rules"].append({
            "id": local(imp),
            "label": str(g.value(imp, RDFS.label) or ""),
            "comment": str(g.value(imp, RDFS.comment) or ""),
            "body_atoms": body,
            "head_atoms": head,
            "variables": rule_vars,
            "_n_vars": len(variables),
        })

    for c in sorted(g.subjects(RDF.type, SKOS.Concept), key=str):
        ttl["skos_concepts"].append({
            "id": local(c),
            "prefLabel": str(g.value(c, SKOS.prefLabel) or ""),
            "definition": str(g.value(c, SKOS.definition) or ""),
            "comment": str(g.value(c, RDFS.comment) or ""),
            "broader": local(g.value(c, SKOS.broader) or ""),
        })
    scheme = next(iter(g.subjects(RDF.type, SKOS.ConceptScheme)), None)
    if scheme is not None:
        ttl["skos_scheme"] = {
            "id": local(scheme),
            "label": str(g.value(scheme, RDFS.label) or ""),
        }

    ttl["counts"] = {
        "classes": len(ttl["classes"]),
        "object_properties": len(ttl["object_properties"]),
        "data_properties": len(ttl["data_properties"]),
        "swrl_rules": len(ttl["rules"]),
        "skos_concepts": len(ttl["skos_concepts"]),
    }
    # D2/D4 供给层（schema 1.1）：唯一新顶层键，图访问集中于 build_supply 纯函数。
    # T4 安全：extract_signature.build_signature 逐键白名单投影构造全新 dict，
    # 从不迭代 ttl 顶层键、从不引用 supply（实证注入后 signature JSON/字节全等）。
    ttl["supply"] = build_supply(g, base_ns)
    return ttl


# ---------------------------------------------------------------- supply 供给层（D2/D4，schema 1.1）
# 图访问集中于 build_supply 纯函数（parse_ttl 唯一新顶层键）。确定性纪律：所有
# 列表/映射排序，公理图节点 id 内容派生（禁 bnode 随机标签）；T4 安全（白名单不取 supply）。

FILLER_PREDS = [
    (OWL.someValuesFrom, "someValuesFrom"), (OWL.allValuesFrom, "allValuesFrom"),
    (OWL.hasValue, "hasValue"), (OWL.hasSelf, "hasSelf"),
    (OWL.minCardinality, "minCardinality"), (OWL.maxCardinality, "maxCardinality"),
    (OWL.minQualifiedCardinality, "minQualifiedCardinality"),
    (OWL.maxQualifiedCardinality, "maxQualifiedCardinality"),
]
FILLER_CN = {
    "someValuesFrom": "至少一个", "allValuesFrom": "全部", "hasValue": "值为",
    "hasSelf": "自反", "minCardinality": "至少", "maxCardinality": "至多",
    "minQualifiedCardinality": "至少(限定)", "maxQualifiedCardinality": "至多(限定)",
}
FACET_PREDS = [XSD.pattern, XSD.minExclusive, XSD.maxExclusive, XSD.minInclusive,
               XSD.maxInclusive, XSD.length, XSD.minLength, XSD.maxLength,
               XSD.totalDigits, XSD.fractionDigits]
CHAR_TYPES = {"FunctionalProperty", "InverseFunctionalProperty", "TransitiveProperty",
              "SymmetricProperty", "AsymmetricProperty", "ReflexiveProperty",
              "IrreflexiveProperty"}


def _literal_meta(lit):
    """rdflib Literal → {value, lang?, datatype?} 精确编码（G2 replace_literal old
    全等）。None→None；lang/datatype 互斥（rdflib 有 lang 则无显式 datatype）。"""
    if lit is None:
        return None
    if not isinstance(lit, Literal):
        return {"value": str(lit)}
    d = {"value": str(lit)}
    if lit.language:
        d["lang"] = lit.language
    elif lit.datatype is not None:
        d["datatype"] = str(lit.datatype)
    return d


def _label(g, iri):
    """参考节点 label：rdfs:label 优先，回退 localname。"""
    return str(g.value(iri, RDFS.label) or local(iri))


def _anchor_owners(g, node):
    """反向 BFS 回溯具名 owner（本地重实现 ontology-model incremental_patch
    .anchor_resolve 算法，避 review→model import 禁区）。URIRef→{自身}；BNode→
    穿透 bnode 主语收集 URIRef 主语（嵌套 restriction/intersectionOf 链可达）。"""
    if isinstance(node, URIRef):
        return {node}
    seen, owners, queue = set(), set(), deque([node])
    while queue:
        cur = queue.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        for s, p, o in g.triples((None, None, cur)):
            if isinstance(s, URIRef):
                owners.add(s)
            elif isinstance(s, BNode) and s not in seen:
                queue.append(s)
    return owners


def _filler_token(g, filler):
    """restriction filler → 内容派生 token（禁 bnode 标签）。URIRef→localname；
    Literal→str；BNode→unionOf/intersectionOf 成员或嵌套 restriction 递归。"""
    if isinstance(filler, URIRef):
        return local(filler)
    if isinstance(filler, Literal):
        return str(filler)
    for lp, tag in [(OWL.unionOf, "∪"), (OWL.intersectionOf, "∩")]:
        lst = g.value(filler, lp)
        if lst is not None:
            members = sorted(_filler_token(g, m) for m in rdf_list_items(g, lst))
            return tag + "(" + ",".join(members) + ")"
    if (filler, RDF.type, OWL.Restriction) in g:
        op = g.value(filler, OWL.onProperty)
        for fp, fk in FILLER_PREDS:
            fv = g.value(filler, fp)
            if fv is not None:
                return "R(%s,%s,%s)" % (local(op) if op is not None else "?",
                                        fk, _filler_token(g, fv))
    return "anon"


def _restriction_info(g, r):
    """owl:Restriction bnode → 内容派生节点信息（id 禁 bnode 标签，owner 经反向
    BFS）。无识别 filler→None。qualified cardinality 的 onClass 并入 filler token
    保 id 唯一。equivalentClass 成员引用复用本函数算同一 id。"""
    op = g.value(r, OWL.onProperty)
    op_local = local(op) if op is not None else "?"
    filler_kind, filler_val = None, None
    for fp, fk in FILLER_PREDS:
        fv = g.value(r, fp)
        if fv is not None:
            filler_kind, filler_val = fk, fv
            break
    if filler_kind is None:
        return None
    onclass = g.value(r, OWL.onClass)
    owners = _anchor_owners(g, r)
    owner_str = "|".join(sorted(local(o) for o in owners)) or "orphan"
    filler_tok = _filler_token(g, filler_val)
    if onclass is not None and filler_kind in ("minQualifiedCardinality",
                                               "maxQualifiedCardinality"):
        filler_tok = "%s@%s" % (filler_tok, local(onclass))
    nid = "ax:R:%s:%s:%s:%s" % (owner_str, op_local, filler_kind, filler_tok)
    label = "%s %s %s %s" % (owner_str, FILLER_CN.get(filler_kind, filler_kind),
                             op_local, filler_tok)
    return {"nid": nid, "owner_str": owner_str, "owners": owners, "op": op,
            "op_local": op_local, "filler_kind": filler_kind,
            "filler_val": filler_val, "filler_tok": filler_tok,
            "onclass": onclass, "label": label}


def build_axiom_graph(g, base_ns):
    """D2④b 公理族约束图：从 TTL OWL 公理构件提取（Restriction/equivalentClass/
    AllDisjointClasses+pairwise disjointWith/hasKey/characteristics/inverseOf 镜像
    去重/datatypeFacet/oneOf）。节点 id 内容派生（禁 bnode 随机标签），owner 经
    通用反向 BFS；nodes 按 id 排序、edges 按 (source,target,kind) 排序→双跑字节等。
    md 形式化表达 overlay 在 merge 层做（表仍权威，md_only 显式）。"""
    def in_base(n):
        return isinstance(n, URIRef) and str(n).startswith(base_ns)

    nodes, edges = {}, set()

    def add_node(nid, kind, label, **extra):
        if nid not in nodes:
            n = {"id": nid, "kind": kind, "label": label}
            n.update(extra)
            nodes[nid] = n

    def add_edge(s, t, kind):
        edges.add((s, t, kind))

    def cls_node(iri):
        nid = "c:" + local(iri)
        add_node(nid, "class", _label(g, iri))
        return nid

    def prop_node(iri):
        nid = "p:" + local(iri)
        add_node(nid, "property", _label(g, iri))
        return nid

    def dt_node(iri):
        nid = "dt:" + local(iri)
        add_node(nid, "datatype", _label(g, iri))
        return nid

    # 1. Restriction（owner 经反向 BFS；嵌套 restriction 经 equivalentClass 可达）
    for r in g.subjects(RDF.type, OWL.Restriction):
        info = _restriction_info(g, r)
        if info is None:
            continue
        add_node(info["nid"], "restriction", info["label"],
                 owner=info["owner_str"], onProperty=info["op_local"],
                 fillerKind=info["filler_kind"], filler=info["filler_tok"])
        for o in sorted(info["owners"], key=str):
            add_edge(cls_node(o), info["nid"], "constrains")
        if info["op"] is not None:
            add_edge(info["nid"], prop_node(info["op"]), "onProperty")
        fv = info["filler_val"]
        if isinstance(fv, URIRef):
            if (fv, RDF.type, OWL.Class) in g:
                add_edge(info["nid"], cls_node(fv), "filler")
            elif (fv, RDF.type, RDFS.Datatype) in g:
                add_edge(info["nid"], dt_node(fv), "filler")
        if info["onclass"] is not None and isinstance(info["onclass"], URIRef):
            add_edge(info["nid"], cls_node(info["onclass"]), "onClass")

    # 2. equivalentClass（具名等价 + 匿名 intersectionOf/unionOf 成员）
    for c in g.subjects(OWL.equivalentClass, None):
        if not in_base(c):
            continue
        for eq in g.objects(c, OWL.equivalentClass):
            if isinstance(eq, URIRef):
                nid = "ax:eq:%s:%s" % (local(c), local(eq))
                add_node(nid, "equivalent", "%s ≡ %s" % (local(c), local(eq)))
                add_edge(cls_node(c), nid, "equivalent")
                add_edge(nid, cls_node(eq), "member")
            elif isinstance(eq, BNode):
                for lp, tag in [(OWL.intersectionOf, "∩"), (OWL.unionOf, "∪")]:
                    lst = g.value(eq, lp)
                    if lst is None:
                        continue
                    members = rdf_list_items(g, lst)
                    toks = sorted(_filler_token(g, m) for m in members)
                    nid = "ax:eq:%s:%s:%s" % (local(c), tag, ",".join(toks))
                    add_node(nid, "equivalent",
                             "%s ≡ %s(%s)" % (local(c), tag, ",".join(toks)))
                    add_edge(cls_node(c), nid, "equivalent")
                    for m in members:
                        if isinstance(m, URIRef):
                            add_edge(nid, cls_node(m), "member")
                        elif isinstance(m, BNode) and (m, RDF.type, OWL.Restriction) in g:
                            minfo = _restriction_info(g, m)
                            if minfo:
                                add_edge(nid, minfo["nid"], "member")

    # 3. disjoint（AllDisjointClasses bnode 主语 + pairwise disjointWith 双形态去重）
    for d in g.subjects(RDF.type, OWL.AllDisjointClasses):
        members = [m for m in rdf_list_items(g, g.value(d, OWL.members))
                   if isinstance(m, URIRef)]
        toks = sorted(local(m) for m in members)
        if not toks:
            continue
        nid = "ax:disjoint:" + "|".join(toks)
        add_node(nid, "disjoint", "互斥: " + ", ".join(toks))
        for m in members:
            add_edge(nid, cls_node(m), "disjointMember")
    for a, b in g.subject_objects(OWL.disjointWith):
        if in_base(a) and in_base(b):
            pair = sorted([local(a), local(b)])
            nid = "ax:disjoint:" + "|".join(pair)
            add_node(nid, "disjoint", "互斥: " + ", ".join(pair))
            for x in (a, b):
                add_edge(nid, cls_node(x), "disjointMember")

    # 4. hasKey
    for c in g.subjects(OWL.hasKey, None):
        if not in_base(c):
            continue
        for hk in g.objects(c, OWL.hasKey):
            keys = sorted(local(k) for k in rdf_list_items(g, hk)
                          if isinstance(k, URIRef))
            if not keys:
                continue
            nid = "ax:key:%s:%s" % (local(c), ",".join(keys))
            add_node(nid, "hasKey", "%s 键: %s" % (local(c), ", ".join(keys)))
            add_edge(cls_node(c), nid, "hasKey")
            for k in keys:
                add_edge(nid, prop_node(URIRef(base_ns + k)), "keyProp")

    # 5. characteristics（Functional/Transitive/…）
    for p in list(g.subjects(RDF.type, OWL.ObjectProperty)) + \
            list(g.subjects(RDF.type, OWL.DatatypeProperty)):
        if not in_base(p):
            continue
        for t in g.objects(p, RDF.type):
            tl = local(t)
            if tl in CHAR_TYPES:
                nid = "ax:char:%s:%s" % (local(p), tl)
                add_node(nid, "characteristic", "%s: %s" % (local(p), tl))
                add_edge(prop_node(p), nid, "characteristic")

    # 6. inverseOf（镜像去重：A inverseOf B ∧ B inverseOf A → 单节点）
    for p in g.subjects(OWL.inverseOf, None):
        if not in_base(p):
            continue
        for q in g.objects(p, OWL.inverseOf):
            if isinstance(q, URIRef) and in_base(q):
                pair = sorted([local(p), local(q)])
                nid = "ax:inv:" + "|".join(pair)
                add_node(nid, "inverse", "逆: " + ", ".join(pair))
                for x in (p, q):
                    add_edge(nid, prop_node(x), "inverse")

    # 7. datatypeFacet（具名 rdfs:Datatype onDatatype+withRestrictions）
    for dt in g.subjects(RDF.type, RDFS.Datatype):
        if not in_base(dt):
            continue
        ondt = g.value(dt, OWL.onDatatype)
        wr = g.value(dt, OWL.withRestrictions)
        facets = []
        if wr is not None:
            for cell in rdf_list_items(g, wr):
                for fp in FACET_PREDS:
                    fv = g.value(cell, fp)
                    if fv is not None:
                        facets.append("%s=%s" % (local(fp), str(fv)))
        facets.sort()
        if not facets:
            continue
        nid = "ax:dt:%s:%s" % (local(dt), ",".join(facets))
        add_node(nid, "datatypeFacet", "%s: %s" % (local(dt), ", ".join(facets)),
                 base=local(ondt) if ondt is not None else "", facets=facets)
        add_edge(dt_node(dt), nid, "rangeDatatype")

    # 8. oneOf（数据属性 range 匿名 oneOf 受控值）
    for p in g.subjects(RDF.type, OWL.DatatypeProperty):
        if not in_base(p):
            continue
        rng = g.value(p, RDFS.range)
        if not isinstance(rng, BNode):
            continue
        oneof = g.value(rng, OWL.oneOf)
        if oneof is None:
            continue
        vals = [str(v) for v in rdf_list_items(g, oneof)]
        nid = "ax:oneOf:" + local(p)
        add_node(nid, "oneOf", "%s 受控值: %s" % (local(p), "/".join(vals)),
                 values=vals)
        add_edge(prop_node(p), nid, "controlledRange")
        ondt = g.value(rng, OWL.onDatatype)
        if ondt is not None and in_base(ondt):
            add_edge(nid, dt_node(ondt), "rangeDatatype")

    return {
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": [{"source": s, "target": t, "kind": k}
                  for s, t, k in sorted(edges)],
    }


def build_supply(g, base_ns):
    """D2/D4 供给层纯函数（parse_ttl 唯一新顶层键 ttl["supply"]）。集中图访问，
    产 iris/literals/enum/class_parents/atom_meta/broader_list/axiom_graph 等平行表，
    既有实体 dict 字节不动（T4 白名单不取 supply）。所有输出确定性排序。"""
    def in_base(n):
        return isinstance(n, URIRef) and str(n).startswith(base_ns)

    supply = {"base_ns": base_ns}
    supply["prefixes"] = {str(p): str(ns) for p, ns in
                          sorted(g.namespaces(), key=lambda x: (str(x[1]), str(x[0])))}
    versions = sorted({str(v) for v in g.objects(None, OWL.versionInfo)})
    supply["ontology_version"] = versions[0] if len(versions) == 1 else None

    # iris（G3：D4 一律产全 IRI，避默认 ns 歧义）
    iris = {"classes": {}, "object_properties": {}, "data_properties": {},
            "rules": {}, "skos_concepts": {}, "scheme": None}
    for c in sorted(g.subjects(RDF.type, OWL.Class), key=str):
        if in_base(c):
            iris["classes"][local(c)] = str(c)
    for p in sorted(g.subjects(RDF.type, OWL.ObjectProperty), key=str):
        if in_base(p):
            iris["object_properties"][local(p)] = str(p)
    for p in sorted(g.subjects(RDF.type, OWL.DatatypeProperty), key=str):
        if in_base(p):
            iris["data_properties"][local(p)] = str(p)
    for imp in sorted(g.subjects(RDF.type, SWRL.Imp), key=str):
        iris["rules"][local(imp)] = str(imp)
    for c in sorted(g.subjects(RDF.type, SKOS.Concept), key=str):
        iris["skos_concepts"][local(c)] = str(c)
    scheme = next(iter(sorted(g.subjects(RDF.type, SKOS.ConceptScheme), key=str)), None)
    if scheme is not None:
        iris["scheme"] = str(scheme)
    supply["iris"] = iris

    # literals（G2：replace_literal old 全等编码取精确 lang/datatype）
    literals = {}
    for kind, stype in [("class", OWL.Class), ("object_property", OWL.ObjectProperty),
                        ("data_property", OWL.DatatypeProperty), ("rule", SWRL.Imp)]:
        for s in sorted(g.subjects(RDF.type, stype), key=str):
            if kind != "rule" and not in_base(s):
                continue
            literals["%s:%s" % (kind, local(s))] = {
                "label": _literal_meta(g.value(s, RDFS.label)),
                "comment": _literal_meta(g.value(s, RDFS.comment)),
            }
    for c in sorted(g.subjects(RDF.type, SKOS.Concept), key=str):
        literals["skos:%s" % local(c)] = {
            "prefLabel": _literal_meta(g.value(c, SKOS.prefLabel)),
            "definition": _literal_meta(g.value(c, SKOS.definition)),
            "comment": _literal_meta(g.value(c, RDFS.comment)),
        }
    supply["literals"] = literals

    # enum_literals + enum_editable（G8 重名预检：全图 rdf:first 字面量计数）
    first_counts = {}
    for o in g.objects(None, RDF.first):
        if isinstance(o, Literal):
            first_counts[str(o)] = first_counts.get(str(o), 0) + 1
    enum_literals, enum_editable = {}, {}
    for p in sorted(g.subjects(RDF.type, OWL.DatatypeProperty), key=str):
        if not in_base(p):
            continue
        rng = g.value(p, RDFS.range)
        if not isinstance(rng, BNode):
            continue
        oneof = g.value(rng, OWL.oneOf)
        if oneof is None:
            continue
        vals = rdf_list_items(g, oneof)
        pid = local(p)
        enum_literals[pid] = [_literal_meta(v) for v in vals]
        ed = []
        for v in vals:
            cnt = first_counts.get(str(v), 0)
            if cnt > 1:
                ed.append({"value": str(v), "editable": False,
                           "reason": "重名不可消歧（全图 %d 处 rdf:first），转入口 (c)" % cnt})
            else:
                ed.append({"value": str(v), "editable": True, "reason": ""})
        enum_editable[pid] = ed
    supply["enum_literals"] = enum_literals
    supply["enum_editable"] = enum_editable

    # class_parents（G4 拖拽守卫：具名父列表 + 匿名父计数）
    class_parents = {}
    for c in sorted(g.subjects(RDF.type, OWL.Class), key=str):
        if not in_base(c):
            continue
        named, anon = [], 0
        for s in g.objects(c, RDFS.subClassOf):
            if isinstance(s, URIRef) and not str(s).startswith(str(SWRL)):
                named.append(local(s))
            elif isinstance(s, BNode):
                anon += 1
        class_parents[local(c)] = {"named": sorted(named), "anon": anon}
    supply["class_parents"] = class_parents

    # atom_meta（D2⑤c 规则流图：atom_id 位置派生 <rid>.b<i>/.h<i>，跨 parse 确定；
    # arg_kinds 与 parse_atoms arguments 同序同数，索引只计 bnode atom 对齐 body_atoms）
    atom_meta = {}
    for imp in sorted(g.subjects(RDF.type, SWRL.Imp), key=str):
        rid = local(imp)
        meta = {}
        for side, pred, tag in [("body", SWRL.body, "b"), ("head", SWRL.head, "h")]:
            entries, bi = [], 0
            for atom in rdf_list_items(g, g.value(imp, pred)):
                if not isinstance(atom, BNode):
                    continue
                args_node = g.value(atom, SWRL.arguments)
                if args_node is not None:
                    arg_nodes = rdf_list_items(g, args_node)
                else:
                    arg_nodes = [a for a in (g.value(atom, SWRL.argument1),
                                             g.value(atom, SWRL.argument2))
                                 if a is not None]
                arg_kinds = []
                for a in arg_nodes:
                    if isinstance(a, Literal):
                        ak = {"kind": "literal", "value": str(a)}
                        if a.language:
                            ak["lang"] = a.language
                        elif a.datatype is not None:
                            ak["datatype"] = str(a.datatype)
                        arg_kinds.append(ak)
                    elif (a, RDF.type, SWRL.Variable) in g:
                        arg_kinds.append({"kind": "var", "name": local(a)})
                    else:
                        arg_kinds.append({"kind": "iri", "iri": str(a),
                                          "name": local(a)})
                entries.append({"atom_id": "%s.%s%d" % (rid, tag, bi),
                                "arg_kinds": arg_kinds})
                bi += 1
            meta[side] = entries
        atom_meta[rid] = meta
    supply["atom_meta"] = atom_meta

    # broader_list（D2⑥b SKOS 多父：g.objects 通用实现，broader 单值保留保⑥区 compat）
    broader_list = {}
    for c in sorted(g.subjects(RDF.type, SKOS.Concept), key=str):
        broader_list[local(c)] = sorted(local(b) for b in g.objects(c, SKOS.broader)
                                        if isinstance(b, URIRef))
    supply["broader_list"] = broader_list

    # axiom_graph（D2④b 公理约束图）
    supply["axiom_graph"] = build_axiom_graph(g, base_ns)
    return supply


# ---------------------------------------------------------------- md 层

def split_table_row(line):
    """md 表行 → 单元格。支持 `\\|` 转义管道（正则/枚举值常出现在单元格内，
    如 pattern `(JD\\|PJ\\|BX)+[0-9]+`）——朴素 split 会把一个 cell 切成多个。"""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]
    return cells


def looks_like_table(line):
    return line.strip().startswith("|") and line.count("|") >= 2


def is_separator(cells):
    return all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c) and any(cells)


# 表头跨 run 漂移归一：不同 run 的实体表列名不同（如「属性/类型/取值」，
# 或「属性标准名/类型取值/约束要点/消费级/硬软分类」）——按关键词认列，不写死列名。
COL_PATTERNS = {
    "prop": [r"属性标准名", r"属性名", r"属性", r"标准名", r"字段"],
    "type": [r"类型/取值", r"类型取值", r"类型.*取值", r"^\s*类型\s*$", r"取值"],
    "constraint": [r"约束要点", r"约束说明", r"约束", r"说明"],
    "level": [r"消费级", r"消费级别", r"优先级"],
}


def header_col_index(header, kind):
    """在表头中按关键词优先级找列下标；找不到返回 None。"""
    for pat in COL_PATTERNS[kind]:
        for i, h in enumerate(header):
            if re.search(pat, str(h)):
                return i
    return None


def prop_name_from_cell(raw):
    """首列单元格 → 属性英文名（`productName 产品名称` → `productName`；
    `:billNumber 票号` → `billNumber`）。取不到英文名则退回原文首段。"""
    s = str(raw or "").strip()
    m = re.match(r"^:?([A-Za-z_][A-Za-z0-9_]*)", s)
    if m:
        return m.group(1)
    return s.split()[0] if s.split() else ""


def entity_rows_normalized(header, rows):
    """实体表行 → 规范键 md_props（prop/prop_cn/type/constraint/level/extras）。"""
    i_prop = header_col_index(header, "prop")
    i_type = header_col_index(header, "type")
    i_con = header_col_index(header, "constraint")
    i_lvl = header_col_index(header, "level")
    used = {i_prop, i_type, i_con, i_lvl}

    def cell(r, i):
        return r[i] if i is not None and i < len(r) else ""

    out = []
    for r in rows:
        raw = cell(r, i_prop if i_prop is not None else 0)
        extras = [(header[i], r[i]) for i in range(min(len(header), len(r)))
                  if i not in used and str(r[i]).strip()]
        out.append({
            "prop": prop_name_from_cell(raw),
            "prop_cn": str(raw).strip(),
            "type": cell(r, i_type),
            "constraint": cell(r, i_con),
            "level": cell(r, i_lvl),
            "extras": extras,
        })
    return out


def parse_md_tables(lines, section_pattern, max_tables=1):
    """取匹配节内的前 max_tables 个表 → [{header: [...], rows: [[...]]}]。"""
    tables, in_section, current = [], False, None
    for line in lines:
        m = re.match(r"^#{2,4}\s", line)
        if m:
            in_section = bool(re.search(section_pattern, line))
            current = None
            continue
        if not in_section:
            continue
        if looks_like_table(line):
            cells = split_table_row(line)
            if is_separator(cells):
                continue
            if current is None:
                current = {"header": cells, "rows": []}
            else:
                current["rows"].append(cells)
        else:
            if current is not None and current["rows"]:
                tables.append(current)
                if len(tables) >= max_tables:
                    break
                current = None
    if current is not None and current["rows"] and current not in tables:
        tables.append(current)
    return tables


def rows_as_dicts(table):
    header = table["header"]
    out = []
    for r in table["rows"]:
        d = {}
        for i, h in enumerate(header):
            d[h] = r[i] if i < len(r) else ""
        out.append(d)
    return out


def entity_name_from_heading(heading):
    # 两种实体节标题记法：`实体名（:LocalName）`（带冒号）与 `实体名（LocalName）`（无冒号，可带尾注）
    m = re.search(r"[（(]:([A-Za-z0-9_]+)[）)]", heading)
    if m:
        return m.group(1)
    m = re.search(r"[（(]([A-Za-z][A-Za-z0-9_]*)[，,）)]", heading)
    if m:
        return m.group(1)
    m = re.search(r":([A-Za-z][A-Za-z0-9_]*)", heading)
    return m.group(1) if m else None


def store_entity_table(md, entity, table):
    """实体表落库（保留原始行 + 规范键行，后者供审阅页属性表使用）。"""
    md["entities"][entity] = {
        "header": table["header"],
        "rows": table["rows"],
        "rows_dicts": rows_as_dicts(table),
        "props": entity_rows_normalized(table["header"], table["rows"]),
    }


def parse_scheme_md(md_path):
    md = {"entities": {}, "relations": [], "axiom_families": {},
          "rules": [], "parse_errors": []}
    text = open(md_path, encoding="utf-8").read()
    lines = text.splitlines()

    # 实体节：### 2.N 名称（:Class）——表与散文（①定义②子类分叉等）都收集。
    # 节内可能内联多张表（属性表+关系表片段）：属性表只取首表，后续表入
    # entity_extra_tables（混入会把关系行伪装成属性行显示）。新表起始判据=
    # 该行后紧跟分隔行（GFM 表头必跟分隔行，数据行不会）。
    md["entity_text"] = {}
    md["entity_extra_tables"] = {}
    cur_entity = None
    cur_table = None
    cur_extra = None

    def flush_table():
        nonlocal cur_table, cur_extra
        if cur_table is not None and cur_table["rows"]:
            store_entity_table(md, cur_entity, cur_table)
        cur_table = None
        if cur_extra is not None and cur_extra["rows"]:
            md["entity_extra_tables"].setdefault(cur_entity, []).append(cur_extra)
        cur_extra = None

    for idx, line in enumerate(lines):
        m = re.match(r"^###\s+(.*)$", line)
        if m:
            if cur_entity is not None:
                flush_table()
            cur_entity = entity_name_from_heading(m.group(1))
            md["entity_text"].setdefault(cur_entity, [])
            continue
        if cur_entity is None:
            continue
        if looks_like_table(line):
            cells = split_table_row(line)
            if is_separator(cells):
                continue
            nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
            starts_new = looks_like_table(nxt) and is_separator(split_table_row(nxt))
            if cur_table is None and cur_extra is None:
                cur_table = {"header": cells, "rows": []}
            elif starts_new:
                # 又一张新表起始（第 2、3…张）：收存当前表，开新 extra 表
                flush_table()
                cur_extra = {"header": cells, "rows": []}
            elif cur_extra is not None:
                cur_extra["rows"].append(cells)
            else:
                cur_table["rows"].append(cells)
        elif line.strip():
            md["entity_text"].setdefault(cur_entity, []).append(line)
    if cur_entity is not None:
        flush_table()

    # 关系表（§三）
    rel_tables = parse_md_tables(lines, r"^##\s*三|关系层", max_tables=1)
    if rel_tables:
        md["relations"] = rows_as_dicts(rel_tables[0])
    else:
        md["parse_errors"].append("关系层表未解析")

    # 公理族（§4.F/L/C/P/X/S 约束侧六族 + §4.R 推导族=七族；空族（如敏感族设计空置）不报错）
    for fam, pat in [("F", r"4\.F"), ("L", r"4\.L"), ("C", r"4\.C"),
                     ("P", r"4\.P"), ("X", r"4\.X"), ("S", r"4\.S")]:
        t = parse_md_tables(lines, pat, max_tables=1)
        if t:
            md["axiom_families"][fam] = rows_as_dicts(t[0])
        else:
            in_section = any(re.search(pat, l) for l in lines)
            md["axiom_families"][fam] = []
            if not in_section:
                md["parse_errors"].append("公理族 %s 节缺失" % fam)

    # 规则表（§4.R）
    rule_tables = parse_md_tables(lines, r"4\.R", max_tables=1)
    if rule_tables:
        md["rules"] = rows_as_dicts(rule_tables[0])
    else:
        md["parse_errors"].append("规则表未解析")

    return md


# ---------------------------------------------------------------- 合并

AXIOM_COLS = ["编号", "名称", "自然语言陈述", "形式化表达", "判定依据",
              "违反处置", "约束等级"]
REL_COLS = ["关系", "定义", "域→值域", "基数", "逆关系", "边属性",
            "推理用途", "主链路"]


def first_col_key(row, prefix=":"):
    """取行首单元里的首个 :localname token。"""
    for v in row.values():
        m = re.search(prefix + r"([A-Za-z0-9_]+)", str(v))
        if m:
            return m.group(1)
    return None


def parse_term_dicts(paths):
    """术语词典 md → {标准名: 定义}。

    兼容两种表头：`术语（prefLabel）| 定义（definition）| …`（基线词典）
    与 `# | 标准名 | 定义 | 同义词/别名 | 上位词 | 溯源`（增补词典）。
    用途：TTL 的 skos:Concept 常缺 skos:definition，审阅页定义列需回填，
    否则专家看到空定义——词典是人写的权威定义来源。
    """
    defs = {}
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        header, idx = None, (None, None)
        for line in open(p, encoding="utf-8").read().splitlines():
            if not looks_like_table(line):
                header = None
                continue
            cells = split_table_row(line)
            if is_separator(cells):
                continue
            if header is None:
                header = cells
                i_name = next((i for i, h in enumerate(cells)
                               if re.search(r"标准名|prefLabel|^\s*术语\s*$", str(h))), None)
                i_def = next((i for i, h in enumerate(cells)
                              if re.search(r"^\s*定义|definition", str(h))), None)
                idx = (i_name, i_def)
                continue
            i_name, i_def = idx
            if i_name is None or i_def is None:
                continue
            if i_name >= len(cells) or i_def >= len(cells):
                continue
            name, definition = cells[i_name].strip(), cells[i_def].strip()
            if name and definition and definition not in ("—", "-", "—", ""):
                defs.setdefault(name, definition)
    return defs


def class_hierarchy(classes):
    """类继承树 → [{root, root_label, ids}]（组内先序：父类在前、子类紧随）。
    供审阅页「类与属性」分组呈现（避免平铺无层次）。"""
    ids = {c["id"] for c in classes}
    label = {c["id"]: (c["label"] or c["id"]) for c in classes}
    sup = {c["id"]: [s for s in c["superclasses"] if s in ids] for c in classes}
    children = {cid: [] for cid in ids}
    for cid, sups in sup.items():
        for s in sups:
            children[s].append(cid)
    roots = sorted([cid for cid in ids if not sup[cid]],
                   key=lambda x: (x != "Thing", label[x]))
    groups, depth_of = [], {}
    seen = set()

    def walk(cid, depth):
        if cid in seen:
            return
        seen.add(cid)
        depth_of[cid] = depth
        order.append(cid)
        for ch in sorted(children[cid], key=lambda x: label[x]):
            walk(ch, depth + 1)

    for r in roots:
        order = []
        walk(r, 0)
        groups.append({"root": r, "root_label": label.get(r, r), "ids": order})
    # 环等异常兜底：未访问到的类各成一组
    for cid in sorted(ids - seen, key=lambda x: label[x]):
        order = []
        walk(cid, 0)
        groups.append({"root": cid, "root_label": label.get(cid, cid) + "（未挂根）",
                       "ids": order})
    return groups, depth_of


# SWRL builtin → 中文比较词（通俗翻译用；未收录者回退原文呈现，不猜语义）
BUILTIN_CN = {
    "swrlb:equal": "等于", "swrlb:notEqual": "不等于",
    "swrlb:greaterThan": "大于", "swrlb:greaterThanOrEqual": "大于等于",
    "swrlb:lessThan": "小于", "swrlb:lessThanOrEqual": "小于等于",
    "swrlb:contains": "包含", "swrlb:startsWith": "以…开头",
    "swrlb:endsWith": "以…结尾", "swrlb:stringContains": "文本包含",
    "swrlb:matches": "匹配正则", "swrlb:regex": "匹配正则",
    "swrlb:add": "= 两者之和（", "swrlb:subtract": "= 两者之差（",
    "swrlb:multiply": "= 两者之积（", "swrlb:divide": "= 两者之商（",
}


def plain_swrl(t, cls_label, prop_label, prop_range):
    """SWRL atoms → 业务可读的通俗翻译（业务专家读不懂 SWRL 结构，需业务名翻译）。

    确定性模板翻译（机械回归层纪律：不过 LLM，同输入必同输出）。变量不暴露
    占位符（?1/?2 仍需人脑对照图例），直接代入**角色名词**：
      角色定名 = ClassAtom 类中文名（权威）> 对象属性第二参 range 类名
               > 数据属性第二参「属性名+值」> 兜底「对象」
      首现 = 「某+角色」（存在引入），回指 = 「该+角色」；
      同角色名词被多个变量占用时以甲/乙消歧（某实体甲/某实体乙）
    句式（以中性占位「实体/关系/属性」示意，实际代入本体类中文名）：
      ClassAtom 且角色==类名 → 独立句「某实体」（存在引入）；回指时省略
        （角色名词已隐含类归属，冗余回指句会产出「如果· 该实体」式残句）
      ClassAtom 且角色!=类名 → 「该实体 是『某结论类』」（归类结论）
      IndividualPropertyAtom → 「该实体 的『某关系』是 某关联实体」
      DatavaluedPropertyAtom → 「该关联实体 的『某属性』= 值」
      BuiltinAtom            → 「该数值 大于 360」（未收录比较词回退原文）
    无 atoms 返回 None。
    """
    body = t.get("body_atoms") or []
    head = t.get("head_atoms") or []
    if not body and not head:
        return None

    role, seen, base_count = {}, {}, {}

    def assign(v, base):
        n = base_count.get(base, 0) + 1
        base_count[base] = n
        role[v] = base if n == 1 else base + "甲乙丙丁戊"[n - 2]

    # 角色定名只看 body（head 的 ClassAtom 是结论归类，不得篡夺主语角色——
    # 曾现 head 结论类(?1) 把主体角色从「主体类」覆写成「结论类」）
    # 第一遍：body ClassAtom 权威（角色名=该类中文名）
    for a in body:
        if a.get("atom_type") != "ClassAtom":
            continue
        args = [str(x) for x in (a.get("arguments") or [])]
        pred = a.get("predicate", "")
        if args and args[0].startswith("?") and pred in cls_label \
                and args[0] not in role:
            assign(args[0], cls_label[pred])
    # 第二遍：属性推断（对象属性第二参→range 类名；数据属性第二参→属性值）
    for a in body:
        at, pred = a.get("atom_type"), a.get("predicate", "")
        args = [str(x) for x in (a.get("arguments") or [])]
        if at == "IndividualPropertyAtom" and len(args) == 2 \
                and args[1].startswith("?") and args[1] not in role:
            rng = prop_range.get(pred, "")
            assign(args[1], cls_label.get(rng)
                   or ((prop_label.get(pred) or pred) + "对象"))
        elif at == "DatavaluedPropertyAtom" and len(args) == 2 \
                and args[1].startswith("?") and args[1] not in role:
            assign(args[1], (prop_label.get(pred) or pred) + "值")
    # 第三遍兜底：仍无角色的变量（首现即属性第一参/builtin 实参）
    for a in body + head:
        for x in (a.get("arguments") or []):
            x = str(x)
            if x.startswith("?") and x not in role:
                assign(x, "对象")

    def sv(a):
        a = str(a)
        if not a.startswith("?"):
            return a.strip('"')
        r = role[a]
        if a in seen:
            return "该" + r
        seen[a] = True
        return "某" + r

    def conv(atoms):
        out = []
        for a in atoms:
            at = a.get("atom_type")
            pred = a.get("predicate", "")
            args = [str(x) for x in (a.get("arguments") or [])]
            name = cls_label.get(pred) or prop_label.get(pred) or pred
            if at == "ClassAtom" and args and args[0].startswith("?"):
                if pred in cls_label and role.get(args[0]) == cls_label[pred]:
                    if args[0] in seen:
                        continue  # 回指独立句冗余（角色名词已隐含类归属），省略
                    out.append(sv(args[0]))  # 存在引入独立句
                else:
                    out.append("%s 是「%s」" % (sv(args[0]), name))
            elif at in ("IndividualPropertyAtom",
                        "DatavaluedPropertyAtom") and len(args) == 2:
                if args[1].startswith("?"):
                    out.append("%s 的「%s」是 %s" % (sv(args[0]), name, sv(args[1])))
                else:
                    out.append("%s 的「%s」= %s"
                               % (sv(args[0]), name, args[1].strip('"')))
            elif at == "BuiltinAtom" and len(args) >= 2:
                cn = BUILTIN_CN.get(pred)
                if cn and not cn.startswith("="):
                    out.append("%s %s %s" % (sv(args[0]), cn, sv(args[1])))
                elif cn:  # 算术类：result = op(a, b)
                    out.append("%s %s%s, %s)"
                               % (sv(args[0]), cn, sv(args[1]), sv(args[2])
                                  if len(args) > 2 else "?"))
                else:
                    out.append("%s(%s)" % (pred, ", ".join(sv(x) for x in args)))
            else:
                out.append("%s(%s)" % (name, ", ".join(sv(x) for x in args)))
        return out

    # vars=role（角色定名 map 本就存在，原 vars:{} 丢弃致图例恒空——1.3.0 一行修）；
    # body/head 串逐规则全等（E10 安全），模板 plainOf 渲染 p.vars 立即生效。
    return {"body": conv(body), "head": conv(head), "vars": role}


def merge(ttl, md, run_dir, term_defs=None):
    md_ok = not md["parse_errors"]
    supply = ttl.get("supply", {})
    out = {
        "schema_version": REVIEW_JSON_SCHEMA,
        "meta": {
            # run_dir 取 basename：此字段经意见单导出与浏览器 localStorage key 消费，
            # 禁绝对本地路径泄漏；与 sources.path/term_dicts 同构，跨部署确定性。
            "run_dir": os.path.basename(run_dir.rstrip("/")) if run_dir else "",
            "extractor": "review_extract.py（ontology-review skill）",
            "md_parse_ok": md_ok,
            "md_parse_errors": md["parse_errors"],
        },
        "classes": [], "object_properties": [], "data_properties": [],
        "axioms": [], "rules": [], "skos": [], "scheme": ttl["skos_scheme"],
        "counts": ttl["counts"],
    }
    # supply 透传（D2/D4 表面字段，schema 1.1；legacy 无 supply→空 dict，模板守卫降级）。
    # 签名零改动：merge 输出从不见于 extract_signature（白名单取 parse_ttl 实体键）。
    out["iri_map"] = supply.get("iris", {})
    out["literal_meta"] = supply.get("literals", {})
    out["enum_literals"] = supply.get("enum_literals", {})
    out["enum_editable"] = supply.get("enum_editable", {})
    out["supply_meta"] = {
        "base_ns": supply.get("base_ns", ""),
        "prefixes": supply.get("prefixes", {}),
        "ontology_version": supply.get("ontology_version"),
    }

    # 类 + 实体 md 表合并；衍生/子类（实体节「②子类」文本、规则/公理表形式化列承载）标 derived 不报错
    ent_tables = md["entities"]
    derived_mentions = set()
    for rows in list(md["axiom_families"].values()) + [md["rules"]]:
        for r in rows:
            for v in r.values():
                for m in re.finditer(r":([A-Za-z0-9_]+)", str(v)):
                    derived_mentions.add(m.group(1))
    # 实体节全文（含①定义②子类分叉描述）中提及的子类也算有承载（某 run 形态：产品叶类在父节描述）
    # entity_extra_tables（实体节内联关系表等，与属性表分离）
    # 的提及同样计入——它们也是建模方案承载，只是不进 md_props 显示
    for tbl in ent_tables.values():
        for r in tbl["rows_dicts"]:
            for v in r.values():
                for m in re.finditer(r":([A-Za-z0-9_]+)", str(v)):
                    derived_mentions.add(m.group(1))
    for extra_list in (md.get("entity_extra_tables") or {}).values():
        for tbl in extra_list:
            for cells in [tbl["header"]] + tbl["rows"]:
                for v in cells:
                    for m in re.finditer(r":([A-Za-z0-9_]+)", str(v)):
                        derived_mentions.add(m.group(1))
    for text_lines in (md.get("entity_text") or {}).values():
        for line in text_lines:
            for m in re.finditer(r":([A-Za-z0-9_]+)", line):
                derived_mentions.add(m.group(1))
    # 中文 label 桥：实体节散文用中文名列子类（如「银票贴现/商票贴现」），
    # 以 TTL rdfs:label 对照——类 label 出现在实体节文本即有承载
    all_entity_text = "\n".join(
        "\n".join(v) for v in (md.get("entity_text") or {}).values())
    for c in ttl["classes"]:
        if c["label"] and len(c["label"]) >= 2 and c["label"] in all_entity_text:
            derived_mentions.add(c["id"])
            derived_label_mentions = True  # noqa: F841（登记用途）
    for c in ttl["classes"]:
        e = {"ttl": c, "md": None, "md_props": [],
             "derived": c["id"] not in ent_tables and c["id"] in derived_mentions}
        if c["id"] in ent_tables:
            t = ent_tables[c["id"]]
            e["md"] = {"entity": c["id"], "rows": t["rows_dicts"],
                       "header": t["header"]}
            e["md_props"] = entity_rows_normalized(t["header"], t["rows"])
        elif not e["derived"]:
            md["parse_errors"].append("类 %s 无 md 实体表" % c["id"])
        # G4 拖拽守卫表（D4①c）：具名父列表 + 匿名父计数（匿名 Restriction 不可寻址）
        e["parents_guard"] = supply.get("class_parents", {}).get(
            c["id"], {"named": [], "anon": 0})
        out["classes"].append(e)

    # 关系合并（按行首 :prop 匹配）
    rel_by_id = {}
    for r in md["relations"]:
        k = first_col_key(r)
        if k:
            rel_by_id[k] = r
    for p in ttl["object_properties"]:
        row = rel_by_id.get(p["id"])
        out["object_properties"].append({
            "ttl": p,
            "md": ({k: v for k, v in row.items()} if row else None),
        })
        if row is None:
            md["parse_errors"].append("对象属性 %s 无 md 行" % p["id"])

    # 数据属性：md 挂到所属类的 md_props（域内）
    prop_owner = {}
    for e in out["classes"]:
        for mp in e["md_props"]:
            if mp["prop"]:
                prop_owner[mp["prop"]] = e["ttl"]["id"]
    for p in ttl["data_properties"]:
        owner = prop_owner.get(p["id"], p["domain"])
        md_row = None
        for e in out["classes"]:
            if e["ttl"]["id"] == owner:
                for mp in e["md_props"]:
                    if mp["prop"] == p["id"]:
                        md_row = mp
        out["data_properties"].append({"ttl": p, "md": md_row, "owner": owner})

    # 公理族
    for fam, rows in md["axiom_families"].items():
        for r in rows:
            out["axioms"].append({"family": fam, "md": r})

    # 规则双通道：TTL atom 结构 + md 自然语言
    # 同一业务规则的编译变体：引用通道（ruleR1）与字面量展开通道（ruleR1c）共享 md 行，
    # 直接逐 TTL imp 出卡会显示成重复卡片——按 md 编号分组，前端同组折叠。
    md_rules = {}
    for r in md["rules"]:
        rid = str(r.get("编号", ""))
        md_rules[rid] = r
    rule_ids = {r["id"] for r in ttl["rules"]}
    # 通俗翻译的中文名映射（业务专家读不懂 SWRL 结构，需业务名翻译）
    cls_label = {c["id"]: c["label"] for c in ttl["classes"] if c.get("label")}
    prop_label = {p["id"]: p["label"]
                  for p in ttl["object_properties"] + ttl["data_properties"]
                  if p.get("label")}
    prop_range = {p["id"]: p.get("range")
                  for p in ttl["object_properties"] if p.get("range")}
    for rule in ttl["rules"]:
        mnum = re.search(r"[Rr]([0-9]+)", rule["id"])
        key = "R" + mnum.group(1) if mnum else rule["id"]
        # 通道判定：id 去掉末尾 c 后仍在规则集合中 ⇒ 本 imp 是字面量展开变体
        stem = rule["id"][:-1] if rule["id"].endswith("c") else None
        channel = "literal" if stem and stem in rule_ids else "reference"
        out["rules"].append({"ttl": rule, "md": md_rules.get(key),
                             "md_key": key, "channel": channel,
                             "plain": plain_swrl(rule, cls_label,
                                                 prop_label, prop_range),
                             "atom_meta": supply.get("atom_meta", {}).get(
                                 rule["id"], {"body": [], "head": []})})
        if md_rules and key not in md_rules:
            md["parse_errors"].append("规则 %s 无 md 行" % rule["id"])

    # 类层级分组（审阅页「类与属性」按根分组 + 组内先序）
    groups, depth_of = class_hierarchy(ttl["classes"])
    out["class_groups"] = groups
    for e in out["classes"]:
        e["depth"] = depth_of.get(e["ttl"]["id"], 0)

    # SKOS 定义回填：TTL 无 skos:definition 时用术语词典 md 的权威定义补齐
    for c in ttl["skos_concepts"]:
        if not c.get("definition"):
            filled = (term_defs or {}).get(c["prefLabel"]) or \
                     (term_defs or {}).get(c["prefLabel"].split("/")[0].strip())
            if filled:
                c["definition"] = filled
                c["definition_source"] = "term_dict"
            else:
                c["definition_missing"] = True
        # D2⑥b SKOS 层级图多父边（broader 单值保留保⑥区 compat；skos 不在签名白名单）
        c["broader_list"] = supply.get("broader_list", {}).get(c["id"], [])

    out["skos"] = ttl["skos_concepts"]

    # 公理图 md overlay（D2④b，best-effort：形式化表达列 :localname token 匹配约束
    # 节点，按承载特异性排序产候选列表；表仍权威，md_only 显式不静默）。
    ag = supply.get("axiom_graph", {"nodes": [], "edges": []})
    md_overlay, md_only = {}, []
    if ag.get("nodes"):
        node_tokens, kind_of = {}, {}
        for n in ag["nodes"]:
            kind_of[n["id"]] = n["kind"]
            toks = set(re.findall(r"[A-Za-z0-9_]+", n["id"]))
            for fld in ("owner", "onProperty", "filler", "base"):
                if n.get(fld):
                    toks.update(re.findall(r"[A-Za-z0-9_]+", str(n[fld])))
            for fld in ("facets", "values"):
                for v in n.get(fld, []):
                    toks.update(re.findall(r"[A-Za-z0-9_]+", str(v)))
            node_tokens[n["id"]] = toks
        # 承载特异性：结构约束 > 逆关系 > 特征（参考节点 class/property/datatype 不算承载）
        spec = {"restriction": 6, "oneOf": 6, "hasKey": 6, "datatypeFacet": 6,
                "disjoint": 6, "equivalent": 6, "inverse": 3, "characteristic": 2}
        for ax in out["axioms"]:
            r = ax["md"]
            tokens = set(re.findall(r":([A-Za-z0-9_]+)", str(r.get("形式化表达", ""))))
            num = str(r.get("编号", ""))
            candidates = []
            if tokens:
                for nid, ntoks in node_tokens.items():
                    if kind_of[nid] in ("class", "property", "datatype"):
                        continue
                    inter = tokens & ntoks
                    if inter:
                        candidates.append((spec.get(kind_of[nid], 1), nid, len(inter)))
            if not candidates:
                if num:
                    md_only.append(num)
                continue
            candidates.sort(key=lambda x: (-x[0], -x[2], x[1]))
            ref = {"family": ax["family"], "编号": num, "名称": str(r.get("名称", ""))}
            for _, nid, _ in candidates:
                md_overlay.setdefault(nid, []).append(ref)
    out["axiom_graph"] = {"nodes": ag.get("nodes", []), "edges": ag.get("edges", []),
                          "md_overlay": md_overlay, "md_only": sorted(set(md_only))}
    out["meta"]["md_parse_ok"] = not md["parse_errors"]
    out["meta"]["md_parse_errors"] = md["parse_errors"][:20]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--ttl", default="ontology.ttl")
    ap.add_argument("--scheme", default="建模方案.md")
    ap.add_argument("--output", default=None)
    ap.add_argument("--term-dict", action="append", default=None,
                    help="术语词典 md（可多次；缺省自动取 run 目录内 术语词典*.md）")
    args = ap.parse_args()
    if not os.path.isdir(args.run_dir):
        sys.exit("exit 2: run 目录不存在")

    ttl_path = os.path.join(args.run_dir, args.ttl)
    md_path = os.path.join(args.run_dir, args.scheme)
    out_path = args.output or os.path.join(args.run_dir, "review.json")

    try:
        ttl = parse_ttl(ttl_path)
    except Exception as e:
        print("exit 1: TTL 解析失败：%s: %s" % (e.__class__.__name__, e))
        sys.exit(1)

    md = {"entities": {}, "relations": [], "axiom_families": {},
          "rules": [], "parse_errors": []}
    if os.path.exists(md_path):
        md = parse_scheme_md(md_path)
    else:
        md["parse_errors"].append("建模方案.md 缺失——仅 TTL 层（专家语言层缺失）")

    dict_paths = args.term_dict or sorted(
        os.path.join(args.run_dir, f) for f in os.listdir(args.run_dir)
        if f.startswith("术语词典") and f.endswith(".md"))
    term_defs = parse_term_dicts(dict_paths)

    merged = merge(ttl, md, os.path.abspath(args.run_dir), term_defs=term_defs)
    merged["meta"]["term_dicts"] = [os.path.basename(p) for p in dict_paths]
    merged["meta"]["term_defs_loaded"] = len(term_defs)
    merged["meta"]["sources"] = {
        "ttl": {"path": args.ttl, "sha": file_sha(ttl_path),
                "sha256_full": file_sha_full(ttl_path)},
        "scheme": {"path": args.scheme,
                   "sha": file_sha(md_path) if os.path.exists(md_path) else None},
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=1)

    print("review.json →", out_path)
    print("counts:", json.dumps(merged["counts"], ensure_ascii=False))
    print("md_parse_ok:", merged["meta"]["md_parse_ok"])
    for err in merged["meta"]["md_parse_errors"][:10]:
        print("  md warn:", err)
    sys.exit(0 if ttl else 1)


if __name__ == "__main__":
    main()
