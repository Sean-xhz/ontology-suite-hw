#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""derive_shacl.py —— R4 SHACL shapes 派生器（TTL-direct，机械 backbone）。

定位
----
从 ontology.ttl（TBox）直接派生 W3C SHACL shapes.ttl + derivation-report.json。
SHACL（封闭世界数据完整性）补 OWL（开放世界逻辑一致性）盲区：限制⑩下 Pellet 剥离
facet 后推理器侧永不校验实例值，check_instance E08 对具名 facet datatype 只 WARN 放行
——本脚本产出的 shapes 经 validate_shacl（pyshacl）承接实例级 facet/基数/唯一性强制。
纯 rdflib，无 Java、无 LLM、无 pyshacl（派生不需校验）。是 R6 实例化管道前置地基。

四设计裁定（实证驱动，正确性必需，契约详见 assets/tpl-shacl-shapes.md）
--------------------------------------------------------------------
R-a 定义类展开：qualified cardinality 的 onClass 若为定义类（equivalentClass），输入侧
    未物化→漏检；展开 intersectionOf/hasValue/someValuesFrom 为 qualifiedValueShape。
R-b 逆路径：带 owl:inverseOf 的属性，path=sh:alternativePath(p, inversePath(q))——
    公理挂 p 而数据走 q 时仍可匹配。**构造要点**：alternativePath 须独立 rdf:list 节点
    + sh:alternativePath 谓词包裹（path 节点本身不可建成 rdf:list，否则 pyshacl 误判为
    序列路径，实证 2026-11-17）。
R-c 子类闭包：sh:class 值约束改具名子类闭包 sh:or——个体仅类型化子类时不误报
    （与 check_instance E06 ancestors 对齐，SHACL 不得比它更严）。hasKey SPARQL 的
    ?other 类型匹配同用闭包 UNION（子类类型化个体不漏检）。
R-d 数值 datatype 容忍：decimal/double/float range 不发 sh:datatype（compile 把 JSON
    int 编码 xsd:integer，严格 sh:datatype decimal 误报），只发 facet+nodeKind Literal。
    实证 minExclusive decimal 对 integer 字面量数值比较成立（跨 datatype 提升）。

纪律（不可绕过）
----------------
- TTL-direct：不改 extract_signature/parse_ttl/review_extract（避 T4 冻结签名漂移）。
- shapes 非权威·可再生·零回写：源 TTL sha256 前后断言；输出 realpath 碰撞守卫；
  默认输出落 cwd，不进 run 目录。源 TTL 不变则 shapes 字节不变。
- 确定性：canonical-copy-rebind（to_canonical_graph→copy→rebind→serialize）+ 无时间戳
  溯源头；report 排序无时间戳；禁 bnode 随机标签泄漏（unmapped construct 用
  内容标识非裸 bnode）。**序列化前绝不喂 pyshacl**（validate 会篡改 shapes 图注入 owl
  公理，破坏确定性——实证 2026-11-17）。
- 纯 rdflib 核心：顶层只 import 标准库+rdflib+同目录 validate_ontology 常量；
  rdf_list/union 算法本地重实现（不 import review_extract，避 model→review 反向分层，
  照 incremental_patch drop_rule 本地重实现先例）。

复用：validate_ontology.VOCAB_NS/local_name（只读 import）；incremental_patch.serialize_draft
      确定性配方（同算法重实现）；review_extract.rdf_list_items/union_class_members 算法
      （本地重实现）；simulate_reason.compile_instance_ttl base 回推算法（TTL-direct 版）。

退出码：0=派生成功 / 1=派生阻断（shape IRI 与源图碰撞/零回写失败）/ 2=输入错（解析/IO）。

用法：
  python3 derive_shacl.py <ontology.ttl> [--output-shapes PATH] [--report PATH]
"""
import argparse
import hashlib
import json
import os
import re
import sys

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD
from rdflib.collection import Collection
from rdflib.compare import to_canonical_graph

# 同目录复用（rdflib-only 模块，不破坏纯 rdflib 核心）
from validate_ontology import VOCAB_NS, local_name

SH = Namespace("http://www.w3.org/ns/shacl#")
SWRL = Namespace("http://www.w3.org/2003/11/swrl#")

SHAPES_SCHEMA_VERSION = "1.0"

# facet 谓词映射（xsd → sh 同名局部名）；generic 支持即使 fixture 无素材
FACET_MAP = {
    XSD.pattern: SH.pattern,
    XSD.minExclusive: SH.minExclusive,
    XSD.minInclusive: SH.minInclusive,
    XSD.maxExclusive: SH.maxExclusive,
    XSD.maxInclusive: SH.maxInclusive,
    XSD.minLength: SH.minLength,
    XSD.maxLength: SH.maxLength,
}
# R-d：数值容忍集——这些 base datatype 不发 sh:datatype（compile int→xsd:integer 误报）
NUMERIC_TOLERANT = {XSD.decimal, XSD.double, XSD.float}
# 源句 provenance 提取（rdfs:comment "源 1.3a/2.4" / "源：4.1-R1"）
SOURCE_RE = re.compile(r"源\s*[:：]?\s*([0-9][0-9A-Za-z./\-]*)")
# IRI 注入守卫（sh:sparql 嵌入前拒空白/引号/尖括号；数据值永不进查询文本）
IRI_UNSAFE_RE = re.compile(r"""[\s"'<>]""")


# ============================================================ 基础设施

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ontology(path):
    if not os.path.exists(path):
        sys.stderr.write("exit 2: 文件不存在：%s\n" % path)
        sys.exit(2)
    g = Graph()
    try:
        g.parse(path, format="turtle")
    except Exception as exc:
        sys.stderr.write("exit 2: TTL 解析失败（%s）：%s\n" % (path, exc))
        sys.exit(2)
    return g


def base_namespace(g, path):
    """@prefix : 回推 base（compile_instance_ttl 同算法的 TTL-direct 版）。"""
    for prefix, ns in g.namespaces():
        if prefix == "":
            return str(ns)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"@prefix\s+:\s*<([^>]*)>", line)
            if m:
                return m.group(1)
    sys.stderr.write("exit 2: 无法确定 base namespace（TTL 无 @prefix : 声明）\n")
    sys.exit(2)


def rdf_list_items(g, node):
    """rdf:List → items（本地重实现 review_extract.rdf_list_items 算法）。"""
    items = []
    while node is not None and isinstance(node, BNode):
        first = g.value(node, RDF.first)
        if first is not None:
            items.append(first)
        node = g.value(node, RDF.rest)
    return items


def facet_datatypes(g):
    """具名 facet datatype（URIRef + onDatatype + withRestrictions）→
    {dt: (base_datatype, [(sh_pred, Literal)])}。parse_ttl 从未做的遍历——R4 核心新素材。
    内联 oneOf bnode（无 onDatatype）自然排除。"""
    out = {}
    for dt in g.subjects(RDF.type, RDFS.Datatype):
        if not isinstance(dt, URIRef):
            continue
        base = g.value(dt, OWL.onDatatype)
        wr = g.value(dt, OWL.withRestrictions)
        if base is None or wr is None:
            continue
        facets = []
        for cell in rdf_list_items(g, wr):
            for pred, obj in g.predicate_objects(cell):
                if pred in FACET_MAP:
                    facets.append((FACET_MAP[pred], obj))
        facets.sort(key=lambda x: (str(x[0]), str(x[1])))
        out[dt] = (base, facets)
    return out


def descendants_closure(g):
    """每个具名类 → 具名后代闭包（含自身，排序）。R-c 用（反向 subClassOf 传递闭包）。"""
    children = {}
    classes = set()
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            children.setdefault(o, set()).add(s)
            classes.add(s)
            classes.add(o)
    for c in g.subjects(RDF.type, OWL.Class):
        if isinstance(c, URIRef):
            classes.add(c)
    out = {}
    for c in classes:
        seen = {c}
        stack = list(children.get(c, ()))
        while stack:
            d = stack.pop()
            if d not in seen:
                seen.add(d)
                stack.extend(children.get(d, ()))
        out[c] = sorted(seen, key=str)
    return out


def inverse_map(g):
    inv = {}
    for s, o in g.subject_objects(OWL.inverseOf):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            inv[s] = o
    return inv


def _domain_or_range_classes(g, prop, pred):
    """domain/range 类列表（URIRef→[它]，bnode unionOf→成员；本地重实现 union 算法）。"""
    out = []
    for node in g.objects(prop, pred):
        if isinstance(node, URIRef):
            out.append(node)
        elif isinstance(node, BNode):
            un = g.value(node, OWL.unionOf)
            if un is not None:
                out.extend(m for m in rdf_list_items(g, un) if isinstance(m, URIRef))
    return sorted(set(out), key=str)


def domain_classes(g, prop):
    return _domain_or_range_classes(g, prop, RDFS.domain)


def range_classes(g, prop):
    return _domain_or_range_classes(g, prop, RDFS.range)


# ============================================================ 派生器

class Deriver(object):
    def __init__(self, g, base, source_path):
        self.g = g
        self.base = base
        self.source_path = source_path
        self.sg = Graph()
        self.sg.bind("", base)
        self.sg.bind("sh", SH)
        self.sg.bind("xsd", XSD)
        self.facets = facet_datatypes(g)
        self.desc = descendants_closure(g)
        self.inv = inverse_map(g)
        self._path_cache = {}        # prop -> path node（幂等合并）
        self._class_node_cache = {}  # frozenset(desc) -> sh:or list node（幂等）
        self._node_shapes = {}       # cls -> NodeShape IRI
        self._facet_consumed = set()
        self._oneof_consumed = set()
        self._defined_consumed = set()
        self.mapped = []
        self.unmapped = []

    # ---------- 构造原语 ----------

    def node_shape(self, cls):
        if cls in self._node_shapes:
            return self._node_shapes[cls]
        iri = URIRef(self.base + local_name(cls) + "Shape")
        self._node_shapes[cls] = iri
        self.sg.add((iri, RDF.type, SH.NodeShape))
        self.sg.add((iri, SH.targetClass, cls))
        return iri

    def path_for(self, prop):
        """R-b：inverseOf 属性 → sh:alternativePath(p, inversePath(q))。memoized 幂等。
        构造要点：path 节点 ap 持 sh:alternativePath 谓词指向独立 list 节点 lst；
        ap 本身不可有 rdf:first（否则 pyshacl 误判序列路径）。"""
        if prop in self._path_cache:
            return self._path_cache[prop]
        q = self.inv.get(prop)
        if q is not None:
            ap = BNode()
            lst = BNode()
            invn = BNode()
            self.sg.add((invn, SH.inversePath, q))
            Collection(self.sg, lst, [prop, invn])
            self.sg.add((ap, SH.alternativePath, lst))
            node = ap
        else:
            node = prop
        self._path_cache[prop] = node
        return node

    def prop_shape(self, cls, prop):
        ns = self.node_shape(cls)
        iri = URIRef(self.base + local_name(cls) + "Shape_" + local_name(prop))
        self.sg.add((iri, RDF.type, SH.PropertyShape))
        self.sg.add((ns, SH.property, iri))
        self.sg.add((iri, SH.path, self.path_for(prop)))
        return iri

    def add_class_constraint(self, subj, classes):
        """R-c：具名子类闭包 sh:or（单类无子类→sh:class）。memoized by frozenset 幂等。
        classes 可为 URIRef 或 list（union range 展平全部后代）。"""
        if isinstance(classes, URIRef):
            classes = [classes]
        all_desc = set()
        for c in classes:
            all_desc.update(self.desc.get(c, [c]))
        all_desc = sorted(all_desc, key=str)
        if not all_desc:
            return
        if len(all_desc) == 1:
            self.sg.add((subj, SH["class"], all_desc[0]))
            return
        key = frozenset(all_desc)
        if key in self._class_node_cache:
            self.sg.add((subj, SH["or"], self._class_node_cache[key]))
            return
        lst = BNode()
        items = []
        for d in all_desc:
            n = BNode()
            self.sg.add((n, SH["class"], d))
            items.append(n)
        Collection(self.sg, lst, items)
        self._class_node_cache[key] = lst
        self.sg.add((subj, SH["or"], lst))

    def provenance(self, iri):
        out = set()
        for comment in self.g.objects(iri, RDFS.comment):
            for m in SOURCE_RE.findall(str(comment)):
                out.add(m)
        return sorted(out)

    # ---------- R-a 定义类展开 ----------

    def expand_defined(self, cls, depth=0):
        """qualifiedValueShape 节点（bnode NodeShape）。定义类展开 equivalentClass；
        非定义类→纯 class 约束。深度>3/不支持形态→None（调用方登记 unmapped）。"""
        if depth > 3:
            return None
        qvs = BNode()
        eq = self.g.value(cls, OWL.equivalentClass)
        if eq is None:
            self.add_class_constraint(qvs, cls)
            return qvs
        self._defined_consumed.add(eq)
        if self._expand_expr(qvs, eq, depth) is None:
            return None
        return qvs

    def _expand_expr(self, qvs, node, depth):
        if depth > 3:
            return None
        if isinstance(node, URIRef):
            self.add_class_constraint(qvs, node)
            return qvs
        inter = self.g.value(node, OWL.intersectionOf)
        if inter is not None:
            for m in rdf_list_items(self.g, inter):
                if self._expand_expr(qvs, m, depth + 1) is None:
                    return None
            return qvs
        union = self.g.value(node, OWL.unionOf)
        if union is not None:
            orlst = BNode()
            items = []
            for m in rdf_list_items(self.g, union):
                sub = BNode()
                if self._expand_expr(sub, m, depth + 1) is None:
                    return None
                items.append(sub)
            Collection(self.sg, orlst, items)
            self.sg.add((qvs, SH["or"], orlst))
            return qvs
        onprop = self.g.value(node, OWL.onProperty)
        if onprop is not None:
            return self._expand_restriction(qvs, node, onprop, depth)
        return None  # onDatatype/oneOf/complementOf 等不支持

    def _expand_restriction(self, qvs, node, onprop, depth):
        hv = self.g.value(node, OWL.hasValue)
        if hv is not None:
            np = BNode()
            self.sg.add((np, SH.path, self.path_for(onprop)))
            self.sg.add((np, SH.hasValue, hv))
            self.sg.add((qvs, SH.property, np))
            return qvs
        svf = self.g.value(node, OWL.someValuesFrom)
        if svf is not None:
            np = BNode()
            self.sg.add((np, SH.path, self.path_for(onprop)))
            self.sg.add((np, SH.minCount, Literal(1)))
            if isinstance(svf, URIRef):
                self.add_class_constraint(np, svf)
            self.sg.add((qvs, SH.property, np))
            return qvs
        avf = self.g.value(node, OWL.allValuesFrom)
        if avf is not None:
            np = BNode()
            self.sg.add((np, SH.path, self.path_for(onprop)))
            if isinstance(avf, URIRef):
                self.add_class_constraint(np, avf)
            self.sg.add((qvs, SH.property, np))
            return qvs
        return None  # 定义类内 cardinality restriction MVP 不展开

    # ---------- 数据属性 ----------

    def derive_data_properties(self):
        for prop in sorted(self.g.subjects(RDF.type, OWL.DatatypeProperty), key=str):
            if not isinstance(prop, URIRef):
                continue
            doms = domain_classes(self.g, prop)
            if not doms:
                self.unmapped.append({"construct": str(prop), "kind": "no-domain",
                    "reason": "数据属性无 rdfs:domain，无法定位 targetClass（MVP）"})
                continue
            rng = self.g.value(prop, RDFS.range)
            functional = (prop, RDF.type, OWL.FunctionalProperty) in self.g
            for cls in doms:
                ps = self.prop_shape(cls, prop)
                self._add_data_range(ps, prop, rng)
                if functional:
                    self.sg.add((ps, SH.maxCount, Literal(1)))
                self.mapped.append({"shape": str(ps), "source_construct": str(prop),
                    "kind": "data_property", "provenance": self.provenance(prop)})

    def _add_data_range(self, ps, prop, rng):
        self.sg.add((ps, SH.nodeKind, SH.Literal))
        if rng is None:
            return
        if isinstance(rng, URIRef):
            if rng in self.facets:
                base, facets = self.facets[rng]
                for sh_pred, val in facets:
                    self.sg.add((ps, sh_pred, val))
                if base == XSD.string:
                    self.sg.add((ps, SH.datatype, XSD.string))
                elif base not in NUMERIC_TOLERANT:
                    self.sg.add((ps, SH.datatype, base))
                # base ∈ 数值容忍集 → 不发 sh:datatype（R-d）
                if rng not in self._facet_consumed:
                    self._facet_consumed.add(rng)
                    self.mapped.append({"shape": str(ps), "source_construct": str(rng),
                        "kind": "facet-datatype", "provenance": self.provenance(rng)})
            elif str(rng).startswith(str(XSD)):
                if rng not in NUMERIC_TOLERANT:
                    self.sg.add((ps, SH.datatype, rng))
            else:
                self.unmapped.append({"construct": str(prop), "kind": "unknown-datatype-range",
                    "reason": "range %s 非 xsd 基型/具名 facet datatype" % local_name(rng)})
        elif isinstance(rng, BNode):
            oneof = self.g.value(rng, OWL.oneOf)
            if oneof is not None:
                vals = rdf_list_items(self.g, oneof)
                lst = BNode()
                Collection(self.sg, lst, vals)
                self.sg.add((ps, SH["in"], lst))
                if prop not in self._oneof_consumed:
                    self._oneof_consumed.add(prop)
                    self.mapped.append({"shape": str(ps), "source_construct": str(prop),
                        "kind": "oneOf-in", "provenance": self.provenance(prop)})
            else:
                self.unmapped.append({"construct": str(prop), "kind": "unsupported-range",
                    "reason": "数据属性 range 为匿名非 oneOf 表达式"})

    # ---------- 对象属性 ----------

    def derive_object_properties(self):
        for prop in sorted(self.g.subjects(RDF.type, OWL.ObjectProperty), key=str):
            if not isinstance(prop, URIRef):
                continue
            doms = domain_classes(self.g, prop)
            if not doms:
                self.unmapped.append({"construct": str(prop), "kind": "no-domain",
                    "reason": "对象属性无 rdfs:domain，无法定位 targetClass（MVP）"})
                continue
            rngs = range_classes(self.g, prop)
            functional = (prop, RDF.type, OWL.FunctionalProperty) in self.g
            for cls in doms:
                ps = self.prop_shape(cls, prop)
                self.sg.add((ps, SH.nodeKind, SH.IRI))
                if rngs:
                    self.add_class_constraint(ps, rngs)
                if functional:
                    self.sg.add((ps, SH.maxCount, Literal(1)))
                self.mapped.append({"shape": str(ps), "source_construct": str(prop),
                    "kind": "object_property", "provenance": self.provenance(prop)})
            for char, name in [(OWL.TransitiveProperty, "TransitiveProperty"),
                               (OWL.SymmetricProperty, "SymmetricProperty"),
                               (OWL.AsymmetricProperty, "AsymmetricProperty"),
                               (OWL.IrreflexiveProperty, "IrreflexiveProperty"),
                               (OWL.ReflexiveProperty, "ReflexiveProperty")]:
                if (prop, RDF.type, char) in self.g:
                    self.unmapped.append({"construct": str(prop), "kind": name,
                        "reason": "属性特征 %s 的闭包/语义=推理机职责，SHACL 不承接" % name})

    # ---------- 公理 Restriction ----------

    def derive_restrictions(self):
        for cls in sorted(self.g.subjects(RDF.type, OWL.Class), key=str):
            if not isinstance(cls, URIRef):
                continue
            for r in sorted(self.g.objects(cls, RDFS.subClassOf), key=str):
                if not isinstance(r, BNode):
                    continue
                onprop = self.g.value(r, OWL.onProperty)
                if onprop is None:
                    continue
                self._derive_restriction(cls, r, onprop)

    def _derive_restriction(self, cls, r, onprop):
        ps = self.prop_shape(cls, onprop)
        prov = sorted(set(self.provenance(onprop)) | set(self.provenance(cls)))
        svf = self.g.value(r, OWL.someValuesFrom)
        avf = self.g.value(r, OWL.allValuesFrom)
        mqc = self.g.value(r, OWL.maxQualifiedCardinality)
        miqc = self.g.value(r, OWL.minQualifiedCardinality)
        card = self.g.value(r, OWL.cardinality)
        minc = self.g.value(r, OWL.minCardinality)
        maxc = self.g.value(r, OWL.maxCardinality)
        hv = self.g.value(r, OWL.hasValue)
        if svf is not None:
            self.sg.add((ps, SH.minCount, Literal(1)))
            self._add_value_class(ps, svf, cls)
            kind = "someValuesFrom"
        elif avf is not None:
            self._add_value_class(ps, avf, cls)
            kind = "allValuesFrom"
        elif mqc is not None:
            self.sg.add((ps, SH.qualifiedMaxCount, Literal(int(mqc))))
            self._add_qualified(ps, self.g.value(r, OWL.onClass), cls)
            kind = "maxQualifiedCardinality"
        elif miqc is not None:
            self.sg.add((ps, SH.qualifiedMinCount, Literal(int(miqc))))
            self._add_qualified(ps, self.g.value(r, OWL.onClass), cls)
            kind = "minQualifiedCardinality"
        elif card is not None:
            self.sg.add((ps, SH.minCount, Literal(int(card))))
            self.sg.add((ps, SH.maxCount, Literal(int(card))))
            kind = "cardinality"
        elif minc is not None:
            self.sg.add((ps, SH.minCount, Literal(int(minc))))
            kind = "minCardinality"
        elif maxc is not None:
            self.sg.add((ps, SH.maxCount, Literal(int(maxc))))
            kind = "maxCardinality"
        elif hv is not None:
            self.sg.add((ps, SH.hasValue, hv))
            kind = "hasValue"
        else:
            self.unmapped.append({"construct": str(cls), "kind": "unsupported-restriction",
                "reason": "Restriction onProperty %s 无可映射约束形态" % local_name(onprop)})
            return
        self.mapped.append({"shape": str(ps), "source_construct": str(cls),
            "kind": "restriction-" + kind, "provenance": prov})

    def _add_value_class(self, ps, target, cls):
        if isinstance(target, URIRef):
            is_class = ((target, RDF.type, OWL.Class) in self.g
                        or (target, RDF.type, RDFS.Class) in self.g)
            if is_class:
                self.add_class_constraint(ps, target)
                self.sg.add((ps, SH.nodeKind, SH.IRI))
            elif target in self.facets:
                self.sg.add((ps, SH.nodeKind, SH.Literal))
                base, facets = self.facets[target]
                for p, v in facets:
                    self.sg.add((ps, p, v))
                if base == XSD.string:
                    self.sg.add((ps, SH.datatype, XSD.string))
                elif base not in NUMERIC_TOLERANT:
                    self.sg.add((ps, SH.datatype, base))
            elif str(target).startswith(str(XSD)):
                self.sg.add((ps, SH.nodeKind, SH.Literal))
                if target not in NUMERIC_TOLERANT:
                    self.sg.add((ps, SH.datatype, target))
            else:
                self.add_class_constraint(ps, target)
                self.sg.add((ps, SH.nodeKind, SH.IRI))
        else:
            self.unmapped.append({"construct": "anonymous-value-class@%s" % local_name(cls),
                "kind": "anonymous-value-class",
                "reason": "someValuesFrom/allValuesFrom 匿名类表达式 MVP 不展开"})

    def _add_qualified(self, ps, onclass, cls):
        if onclass is None:
            self.unmapped.append({"construct": str(cls), "kind": "qualified-no-onClass",
                "reason": "qualified cardinality 无 onClass"})
            return
        if not isinstance(onclass, URIRef):
            self.unmapped.append({"construct": "anonymous-onClass@%s" % local_name(cls),
                "kind": "anonymous-onClass",
                "reason": "qualified cardinality onClass 为匿名类表达式，MVP 不展开"})
            return
        qvs = self.expand_defined(onclass, depth=0)
        if qvs is None:
            self.unmapped.append({"construct": str(onclass), "kind": "defined-class-too-deep",
                "reason": "定义类展开深度>3 或含不支持形态"})
            return
        self.sg.add((ps, SH.qualifiedValueShape, qvs))

    # ---------- hasKey ----------

    def derive_haskey(self):
        for cls, keylist in sorted(self.g.subject_objects(OWL.hasKey), key=lambda x: str(x[0])):
            if not isinstance(cls, URIRef):
                continue
            keys = rdf_list_items(self.g, keylist)
            if len(keys) != 1 or not isinstance(keys[0], URIRef):
                self.unmapped.append({"construct": str(cls), "kind": "hasKey-composite",
                    "reason": "复合 hasKey（多键）或非 URIRef 键——MVP 不承接"})
                continue
            key = keys[0]
            sel = self._haskey_sparql(cls, key)
            if sel is None:
                self.unmapped.append({"construct": str(cls), "kind": "hasKey-iri-unsafe",
                    "reason": "键/类 IRI 含不安全字符，无法嵌入 SPARQL"})
                continue
            ns = self.node_shape(cls)
            sc = BNode()
            self.sg.add((ns, SH.sparql, sc))
            self.sg.add((sc, RDF.type, SH.SPARQLConstraint))
            self.sg.add((sc, SH.message,
                         Literal("%s 类内键值重复（owl:hasKey）" % local_name(cls))))
            self.sg.add((sc, SH.select, Literal(sel)))
            self.mapped.append({"shape": str(ns), "source_construct": str(cls),
                "kind": "hasKey-sparql", "provenance": self.provenance(cls)})

    def _haskey_sparql(self, cls, key):
        """类内唯一键 SPARQL（R-c 闭包 UNION：子类类型化个体不漏检）。IRI 机械嵌入+字符守卫。"""
        desc = self.desc.get(cls, [cls])
        iris = [str(key), str(cls)] + [str(d) for d in desc]
        if any(IRI_UNSAFE_RE.search(i) for i in iris):
            return None
        type_patterns = " UNION ".join("{ ?other a <%s> }" % str(d) for d in desc)
        return ("SELECT $this ?key WHERE { $this <%s> ?key . ?other <%s> ?key . "
                "%s . FILTER (?other != $this) }" % (str(key), str(key), type_patterns))

    # ---------- 不承接登记 ----------

    def register_unmapped_constructs(self):
        for imp in sorted(self.g.subjects(RDF.type, SWRL.Imp), key=str):
            self.unmapped.append({"construct": str(imp), "kind": "SWRL-rule",
                "reason": "SWRL 规则前提/结论=推理机职责，非实例数据约束（rules 面不用于实例断言）"})
        for adc in sorted(self.g.subjects(RDF.type, OWL.AllDisjointClasses), key=str):
            members = rdf_list_items(self.g, self.g.value(adc, OWL.members))
            label = "owl:AllDisjointClasses(%s)" % ",".join(
                sorted(local_name(m) for m in members))
            self.unmapped.append({"construct": label, "kind": "AllDisjointClasses",
                "reason": "互斥类多为 derived 结论类，输入侧 E04 禁断言，属推理后校验"})
        for cls in sorted(self.g.subjects(OWL.equivalentClass, None), key=str):
            eq = self.g.value(cls, OWL.equivalentClass)
            if eq is not None and eq not in self._defined_consumed:
                self.unmapped.append({"construct": str(cls), "kind": "unconsumed-equivalentClass",
                    "reason": "定义类等价公理未被 qualified cardinality 消费，MVP 不单独物化"})

    # ---------- 碰撞守卫 ----------

    def check_iri_collision(self):
        source_iris = {s for s in self.g.subjects() if isinstance(s, URIRef)}
        shape_iris = set()
        for t in (SH.NodeShape, SH.PropertyShape):
            shape_iris.update(s for s in self.sg.subjects(RDF.type, t) if isinstance(s, URIRef))
        collide = source_iris & shape_iris
        if collide:
            sys.stderr.write("exit 1: shape IRI 与源图具名 IRI 碰撞：%s\n"
                             % ", ".join(sorted(map(str, collide))))
            sys.exit(1)

    # ---------- 输出 ----------

    def serialize_shapes(self, source_sha):
        """canonical-copy-rebind（incremental_patch.serialize_draft 同算法）+ 无时间戳溯源头。
        序列化前绝不喂 pyshacl（validate 篡改 shapes 图破坏确定性）。"""
        gc = to_canonical_graph(self.sg)
        g = Graph()
        for t in gc:
            g.add(t)
        for prefix, ns in self.sg.namespaces():
            g.bind(prefix, ns)
        body = g.serialize(format="turtle")
        header = (
            "# ============================================================================\n"
            "# R4 SHACL shapes（TTL 机械派生验证契约，非权威·可再生）\n"
            "# source ttl sha256: %s\n"
            "# shapes schema: %s\n"
            "# 派生：derive_shacl.py（TTL-direct；四设计裁定 R-a/R-b/R-c/R-d）\n"
            "# 纪律：源 TTL 不变则 shapes 字节不变；零回写；TTL 是权威，shapes 非权威。\n"
            "# ============================================================================\n"
            % (source_sha[:12], SHAPES_SCHEMA_VERSION)
        )
        return header + body

    def build_report(self, source_sha):
        kind_counts = {}
        for m in self.mapped:
            kind_counts[m["kind"]] = kind_counts.get(m["kind"], 0) + 1
        ns_count = len(set(self.sg.subjects(RDF.type, SH.NodeShape)))
        ps_count = len(set(self.sg.subjects(RDF.type, SH.PropertyShape)))
        mapped = sorted(self.mapped,
                        key=lambda m: (m["shape"], m["kind"], m["source_construct"]))
        unmapped = sorted(self.unmapped, key=lambda u: (u["kind"], u["construct"]))
        return {
            "schema_version": SHAPES_SCHEMA_VERSION,
            "source_ttl": os.path.basename(self.source_path),
            "source_sha256": source_sha,
            "base_ns": self.base,
            "counts": {"node_shapes": ns_count, "property_shapes": ps_count,
                       "mapped": len(mapped), "unmapped": len(unmapped)},
            "kind_counts": dict(sorted(kind_counts.items())),
            "mapped": mapped,
            "unmapped": unmapped,
            "decisions": [
                "R-a 定义类展开：qualified cardinality onClass 定义类展开 equivalentClass"
                "（intersectionOf/hasValue/someValuesFrom，深度≤3，超出→unmapped）",
                "R-b 逆路径：inverseOf 属性 path=sh:alternativePath(p, inversePath(q))"
                "（独立 list 节点+谓词包裹，path 节点本身不可为 rdf:list）",
                "R-c 子类闭包：sh:class 值约束改具名子类闭包 sh:or（对齐 check_instance E06"
                " ancestors）；hasKey SPARQL ?other 类型匹配同用闭包 UNION",
                "R-d 数值 datatype 容忍：decimal/double/float range 不发 sh:datatype"
                "（compile int→xsd:integer），只发 facet+nodeKind Literal",
            ],
        }


# ============================================================ main

def main():
    ap = argparse.ArgumentParser(description="R4 SHACL shapes 派生器（TTL-direct，纯 rdflib）")
    ap.add_argument("ttl", help="ontology.ttl（TBox，派生唯一权威素材源）")
    ap.add_argument("--output-shapes", default=None, help="shapes.ttl 输出（默认 cwd/shapes.ttl）")
    ap.add_argument("--report", default=None, help="derivation-report.json（默认 cwd/derivation-report.json）")
    args = ap.parse_args()

    src = os.path.realpath(args.ttl)
    g = load_ontology(src)          # 先存在性/解析守卫（exit 2），再算 sha（缺文件不崩溃）
    before = file_sha256(src)
    base = base_namespace(g, src)

    out_shapes = args.output_shapes or os.path.join(os.getcwd(), "shapes.ttl")
    out_report = args.report or os.path.join(os.getcwd(), "derivation-report.json")
    for out in (out_shapes, out_report):
        if os.path.realpath(out) == src:
            sys.stderr.write("exit 2: 输出不得等于源 TTL：%s\n" % out)
            sys.exit(2)

    d = Deriver(g, base, src)
    d.derive_data_properties()
    d.derive_object_properties()
    d.derive_restrictions()
    d.derive_haskey()
    d.register_unmapped_constructs()
    d.check_iri_collision()

    shapes_text = d.serialize_shapes(before)
    report = d.build_report(before)

    with open(out_shapes, "w", encoding="utf-8") as fh:
        fh.write(shapes_text)
    with open(out_report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")

    after = file_sha256(src)
    if before != after:
        sys.stderr.write("exit 1: 零回写断言失败——源 TTL 被改动\n")
        sys.exit(1)

    print("派生完成：node_shapes %d / property_shapes %d / mapped %d / unmapped %d" % (
        report["counts"]["node_shapes"], report["counts"]["property_shapes"],
        report["counts"]["mapped"], report["counts"]["unmapped"]))
    print("  shapes → %s" % out_shapes)
    print("  report → %s" % out_report)
    sys.exit(0)


if __name__ == "__main__":
    main()
