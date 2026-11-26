#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""derive_sparql.py —— D3c SPARQL Read 查询模板派生器（TTL-direct，机械 backbone）。

定位
----
从 ontology.ttl（TBox）直接派生 query-templates.json（canonical 模板库）+
query-templates.md（人类目录）+ derivation-report.json（可选覆盖报告）。这是 model
覆盖矩阵「7 CRUD 查询类」SPARQL 扩展位的 **Read 取知形式化激活**：下游 Agent「经
SPARQL 取知」（methodology-core §8.1）的静态交付物。纯 rdflib 内置 SPARQL 1.1
（prepareQuery 语法自检），无 Java、无 LLM、零新增依赖（rdflib 已在核心 tuple）。
与 derive_shacl.py（R4）完全同构：TTL-direct 派生、非权威可再生、零回写、确定性 canonical。

五设计取舍（实证驱动，契约详见 assets/tpl-query-templates.md）
--------------------------------------------------------------------
D-a TTL-direct：直接读 ontology.ttl 本地解析词汇，一步自包含；不改
    extract_signature/parse_ttl/review_extract（避 T4 冻结签名漂移）；facet 值可取。
D-b Read 取知 MVP：只产 7 类 SELECT 模板；C/U/D（SPARQL UPDATE）登记
    extension_slots 不产——ABox 实例 CRUD 与后续 R6 实例化管道重叠，示例 §7.4 删除悬置。
D-c 子类闭包 property path：class-list/derived-query/key-lookup 用 a/rdfs:subClassOf*
    （零或多步，含自身+具名后代，R-c 对齐）——个体仅类型化子类时不漏检，rdflib 1.1 原生。
D-d derived 类分流：SWRL head ClassAtom classPredicate 结论类不产 class-list，改产
    derived-query（derived_flag=true + 需先物化注记）；禁入实例输入（check_instance E04）
    但可查推理结论，联动 ontology-simulate what-if（文档联动，零代码依赖）。
D-e 参数化 + IRI 守卫：标识/枚举值/数值阈值一律 ?var 参数化（实例数据值永不进查询文本，
    受控枚举值域作 params.enum_values 元数据）；嵌入 IRI 过 IRI_UNSAFE_RE（拒空白/引号/
    尖括号，照 derive_shacl L84-85），不安全→gap 不产模板。

纪律（不可绕过）
----------------
- TTL-direct：rdf_list/union/子类闭包/derived 判定/oneOf/facet 算法本地重实现（不 import
  review_extract/simulate，避 model→review/simulate 反向分层，照 derive_shacl L37-39）。
- 模板库非权威·可再生·零回写：源 TTL sha256 前后断言；输出 realpath 碰撞守卫；默认输出
  落 cwd，不进 run 目录、不进 skill 目录。源 TTL 不变则模板字节不变。
- 确定性：JSON sort_keys/ensure_ascii/indent=1 + 尾换行；MD LF；零 now()/datetime/random/
  mtime；templates 按 (kind, template_id) 全排序；FILTER 枚举值排序；prefix header 排序
  固定；template_id 确定性后缀命名（非内容哈希，照 derive_shacl shape IRI 先例）；禁 bnode
  随机标签泄漏（溯源用内容标识非裸 bnode）。library 字段不嵌 rdflib 版本号
  （跨 patch 版本字节稳定，SPARQL 文本不依赖版本）。
- 纯 rdflib 核心：顶层只 import 标准库+rdflib（含 plugins.sparql.prepareQuery）+同目录
  validate_ontology 常量。

复用：validate_ontology.VOCAB_NS/local_name（只读 import）；derive_shacl 守卫序/确定性配方/
      IRI_UNSAFE_RE/子类闭包/facet_datatypes 算法（同构平移）；review_extract.parse_atoms/
      parse_oneof_enum/union_class_members 算法（本地重实现）；extract_signature derived
      判定算法（本地重实现，SWRL head ClassAtom classPredicate 扫描）。

退出码：0=派生成功（gap 登记不阻塞）/ 1=派生阻断（template_id 碰撞/prepareQuery 语法
        自检失败/零回写失败）/ 2=输入错（文件缺失/TTL 解析失败/输出==源/无 base ns）。

用法：
  python3 derive_sparql.py <ontology.ttl> [--output-json PATH] [--output-md PATH] [--report PATH]
"""
import argparse
import hashlib
import json
import os
import re
import sys

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD
from rdflib.plugins.sparql import prepareQuery

# 同目录复用（rdflib-only 模块，不破坏纯 rdflib 核心）
from validate_ontology import VOCAB_NS, local_name
from _common import file_sha256, base_namespace, rdf_list_items

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")

QUERY_SCHEMA_VERSION = "1.0"
SCRIPT_VERSION = "1.0"

# 7 kind 渲染分组序（逻辑序：列举→精查→取值→过滤→关联→推理结论）
KIND_ORDER = ["class-list", "key-lookup", "property-get", "enum-filter",
              "facet-filter", "op-join", "derived-query"]
# 数值界 facet 谓词（facet-filter 触发判据；pattern/length 非数值界→gap）
NUMERIC_BOUND_PREDS = {XSD.minExclusive, XSD.minInclusive,
                       XSD.maxExclusive, XSD.maxInclusive}
# 数值容忍 base datatype（facet-filter 参数 datatype 取名用）
NUMERIC_BASES = {XSD.decimal, XSD.double, XSD.float, XSD.integer,
                 XSD.long, XSD.int, XSD.short, XSD.nonNegativeInteger}
# 源句 provenance 提取（rdfs:comment "源 1.3a/2.4" / "源：4.1-R1"，照 derive_shacl）
SOURCE_RE = re.compile(r"源\s*[:：]?\s*([0-9][0-9A-Za-z./\-]*)")
# IRI 注入守卫（嵌入查询前拒空白/引号/尖括号；数据值永不进查询文本，照 derive_shacl L84-85）
IRI_UNSAFE_RE = re.compile(r"""[\s"'<>]""")

# 固定排序 prefix header（每模板自带完整 header，独立可执行；目标 IRI 全量嵌入非前缀化）
STD_PREFIXES = [
    ("", None),  # base，运行时填
    ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
]


# ============================================================ 基础设施


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


def facet_datatypes_raw(g):
    """具名 facet datatype（URIRef + onDatatype + withRestrictions）→
    {dt: (base_datatype, [(xsd_pred, Literal)])}。保留原始 xsd 谓词（区分数值界/pattern/
    length），derive_shacl.facet_datatypes 的 xsd 谓词版（SH 映射版供 shapes，此处供 FILTER）。
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
                if str(pred).startswith(str(XSD)):
                    facets.append((pred, obj))
        facets.sort(key=lambda x: (str(x[0]), str(x[1])))
        out[dt] = (base, facets)
    return out


def descendants_closure(g):
    """每个具名类 → 具名后代闭包（含自身，排序）。D-c 用（derive_shacl 同算法）。"""
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


def parse_oneof_enum(g, range_node):
    """数据属性 range 匿名 owl:oneOf bnode → 受控值列表（本地重实现 review_extract）。"""
    if not isinstance(range_node, BNode):
        return None
    oneof = g.value(range_node, OWL.oneOf)
    if oneof is None:
        return None
    return [str(v) for v in rdf_list_items(g, oneof)]


def derived_classes_and_props(g):
    """SWRL head ClassAtom classPredicate → derived 类集；IndividualPropertyAtom
    propertyPredicate → derived 属性集（本地重实现 extract_signature.build_signature
    L64-73 判定算法，直接 rdflib 遍历不经 parse_ttl）。"""
    head_classes, head_props = set(), set()
    for imp in g.subjects(RDF.type, SWRL.Imp):
        head = g.value(imp, SWRL.head)
        for atom in rdf_list_items(g, head):
            if not isinstance(atom, BNode):
                continue
            types = {str(t) for t in g.objects(atom, RDF.type)}
            cp = g.value(atom, SWRL.classPredicate)
            pp = g.value(atom, SWRL.propertyPredicate)
            if str(SWRL.ClassAtom) in types and isinstance(cp, URIRef):
                head_classes.add(cp)
            elif str(SWRL.IndividualPropertyAtom) in types and isinstance(pp, URIRef):
                head_props.add(pp)
    return head_classes, head_props


# ============================================================ 派生器

class QueryDeriver(object):
    def __init__(self, g, base, source_path):
        self.g = g
        self.base = base
        self.source_path = source_path
        self.facets = facet_datatypes_raw(g)
        self.desc = descendants_closure(g)
        self.inv = inverse_map(g)
        self.derived_cls, self.derived_props = derived_classes_and_props(g)
        self.templates = []
        self.gaps = []
        self.unmapped = []
        self.mapped_classes = set()
        self._prefix_header = self._build_prefix_header()

    # ---------- 构造原语 ----------

    def in_base(self, node):
        return isinstance(node, URIRef) and str(node).startswith(self.base)

    def _build_prefix_header(self):
        lines = []
        for prefix, iri in STD_PREFIXES:
            if prefix == "":
                iri = self.base
            lines.append("PREFIX %s: <%s>" % (prefix, iri))
        return "\n".join(lines)

    def safe_iris(self, *iris):
        """IRI 注入守卫（D-e）：任一含空白/引号/尖括号→False。"""
        return not any(IRI_UNSAFE_RE.search(str(i)) for i in iris if i is not None)

    def provenance(self, iri):
        out = set()
        for comment in self.g.objects(iri, RDFS.comment):
            for m in SOURCE_RE.findall(str(comment)):
                out.add(m)
        return sorted(out)

    def gap(self, kind, locator, note):
        self.gaps.append({"gap_id": "gap-%s-%s" % (kind, local_name(locator)),
                          "kind": kind, "locator": str(locator), "note": note})

    def emit(self, kind, title, target_class, target_prop, body, params,
             derived_flag, source_locator, notes):
        """组装一条模板（prefix header + body），登记。template_id 确定性后缀命名。"""
        if target_class is not None and target_prop is not None:
            tid = "q-%s-%s-%s" % (kind, local_name(target_class), local_name(target_prop))
        elif target_class is not None:
            tid = "q-%s-%s" % (kind, local_name(target_class))
        else:
            tid = "q-%s-%s" % (kind, local_name(target_prop))
        sparql = self._prefix_header + "\n" + body
        self.templates.append({
            "template_id": tid,
            "kind": kind,
            "title": title,
            "target": {"class": local_name(target_class) if target_class is not None else None,
                       "property": local_name(target_prop) if target_prop is not None else None},
            "sparql": sparql,
            "params": sorted(params, key=lambda p: p["name"]),
            "derived_flag": derived_flag,
            "source_locator": str(source_locator),
            "provenance": self.provenance(source_locator),
            "notes": notes,
        })
        if target_class is not None:
            self.mapped_classes.add(local_name(target_class))

    def domain_clause(self, prop, var="?s"):
        """单 domain 类→直接类型过滤子句（D-c 闭包仅用于实例列举类模板，属性取值用直接
        domain 上下文）；union/无 domain→空串（调用方登记注记/gap）。返回 (子句, 注记)。"""
        doms = domain_classes(self.g, prop)
        if len(doms) == 1 and self.safe_iris(doms[0]):
            return " . %s a <%s>" % (var, str(doms[0])), ""
        if len(doms) > 1:
            names = ", ".join(local_name(d) for d in doms)
            return "", "domain 联合（%s），裸取值不限定类型" % names
        return "", "无 rdfs:domain，裸取值"

    def range_datatype_name(self, prop):
        """key-lookup ?id 参数 datatype 取名：range facet→base localname；xsd→localname；
        否则 string。"""
        rng = self.g.value(prop, RDFS.range)
        if isinstance(rng, URIRef):
            if rng in self.facets:
                return local_name(self.facets[rng][0])
            return local_name(rng)
        return "string"

    # ---------- class-list / derived-query（D-c 闭包 + D-d 分流） ----------

    def derive_classes(self):
        for cls in sorted(self.g.subjects(RDF.type, OWL.Class), key=str):
            if not self.in_base(cls):
                continue
            if not self.safe_iris(cls):
                self.gap("class-iri-unsafe", cls, "类 IRI 含不安全字符，无法嵌入 SPARQL")
                continue
            ln = local_name(cls)
            if cls in self.derived_cls:
                # D-d：derived 结论类→derived-query（需先物化注记）
                body = "SELECT ?s WHERE { ?s a/rdfs:subClassOf* <%s> }" % str(cls)
                self.emit("derived-query", "查询 %s 推理结论（需先物化）" % ln,
                          cls, None, body, [], True, cls,
                          "需先物化（Pellet）；derived 类禁入实例输入（check_instance E04）"
                          "但可查推理结论；联动 ontology-simulate what-if（物化后执行本模板）")
            else:
                body = "SELECT ?s WHERE { ?s a/rdfs:subClassOf* <%s> }" % str(cls)
                self.emit("class-list", "列举 %s 实例（含子类闭包）" % ln,
                          cls, None, body, [], False, cls,
                          "子类闭包 property path a/rdfs:subClassOf*（含自身+后代，D-c）；"
                          "直接变体 ?s a <%s>（仅本类类型化个体）" % str(cls))

    # ---------- key-lookup（hasKey 单键，D-c 闭包） ----------

    def derive_key_lookup(self):
        for cls, keylist in sorted(self.g.subject_objects(OWL.hasKey), key=lambda x: str(x[0])):
            if not self.in_base(cls):
                continue
            keys = rdf_list_items(self.g, keylist)
            if len(keys) != 1 or not isinstance(keys[0], URIRef):
                self.gap("hasKey-composite", cls,
                         "复合 hasKey（多键）或非 URIRef 键——MVP 只承接单键（照 derive_shacl）")
                continue
            key = keys[0]
            if not self.safe_iris(cls, key):
                self.gap("hasKey-iri-unsafe", cls, "键/类 IRI 含不安全字符，无法嵌入 SPARQL")
                continue
            dt = self.range_datatype_name(key)
            body = ("SELECT ?s WHERE { ?s a/rdfs:subClassOf* <%s> . ?s <%s> ?key . "
                    "FILTER(?key = ?id) }" % (str(cls), str(key)))
            self.emit("key-lookup", "按 %s 标识精查 %s 实例" % (local_name(key), local_name(cls)),
                      cls, key, body,
                      [{"name": "id", "datatype": dt,
                        "note": "标识值（实例数据，参数化绑定，永不进查询文本）"}],
                      False, cls,
                      "标识精查脚手架（票据 §7.2①「给定票号」结构位）；子类闭包 D-c；"
                      "?id 由消费侧绑定具体标识值")

    # ---------- property-get（数据属性基础取值） ----------

    def derive_property_get(self):
        for prop in sorted(self.g.subjects(RDF.type, OWL.DatatypeProperty), key=str):
            if not self.in_base(prop):
                continue
            if not self.safe_iris(prop):
                self.gap("property-iri-unsafe", prop, "属性 IRI 含不安全字符，无法嵌入 SPARQL")
                continue
            clause, dnote = self.domain_clause(prop)
            if not domain_classes(self.g, prop):
                self.gap("no-domain", prop, "数据属性无 rdfs:domain，property-get 降级裸取值")
            body = "SELECT ?s ?v WHERE { ?s <%s> ?v%s }" % (str(prop), clause)
            notes = "字面量取值脚手架；与 enum-filter/facet-filter 互补（基础检索 vs 过滤）"
            if dnote:
                notes += "；" + dnote
            self.emit("property-get", "读取 %s 属性值" % local_name(prop),
                      None, prop, body, [], False, prop, notes)

    # ---------- enum-filter（oneOf 受控值，D-e 参数化） ----------

    def derive_enum_filter(self):
        for prop in sorted(self.g.subjects(RDF.type, OWL.DatatypeProperty), key=str):
            if not self.in_base(prop):
                continue
            rng = self.g.value(prop, RDFS.range)
            enum = parse_oneof_enum(self.g, rng)
            if not enum:
                continue
            if not self.safe_iris(prop):
                continue  # property-iri-unsafe 已由 property-get 登记
            vals = sorted(set(enum))
            clause, dnote = self.domain_clause(prop)
            body = "SELECT ?s WHERE { ?s <%s> ?v%s . FILTER(?v = ?val) }" % (str(prop), clause)
            notes = "受控值过滤脚手架；合法值域见 params.enum_values（TBox 词汇，排序）；?val 参数化绑定"
            if dnote:
                notes += "；" + dnote
            self.emit("enum-filter", "按受控值过滤 %s" % local_name(prop),
                      None, prop, body,
                      [{"name": "val", "datatype": "string",
                        "note": "受控值（实例数据，参数化）", "enum_values": vals}],
                      False, prop, notes)

    # ---------- facet-filter（数值界 facet，D-e 参数化） ----------

    def derive_facet_filter(self):
        for prop in sorted(self.g.subjects(RDF.type, OWL.DatatypeProperty), key=str):
            if not self.in_base(prop):
                continue
            rng = self.g.value(prop, RDFS.range)
            if not isinstance(rng, URIRef) or rng not in self.facets:
                continue
            base, facets = self.facets[rng]
            bounds = [(p, v) for p, v in facets if p in NUMERIC_BOUND_PREDS]
            if not bounds:
                # pattern/length 非数值界→gap（regex/length FILTER 留扩展）
                kinds = sorted({local_name(p) for p, _ in facets})
                self.gap("pattern-facet-no-regex", prop,
                         "range %s facet 为 %s（非数值界），regex/length FILTER 留扩展"
                         "（标识类已由 key-lookup 覆盖）" % (local_name(rng), "/".join(kinds)))
                continue
            if not self.safe_iris(prop):
                continue
            dt = local_name(base) if base in NUMERIC_BASES else local_name(base)
            bound_note = "; ".join("%s %s" % (local_name(p), str(v)) for p, v in bounds)
            clause, dnote = self.domain_clause(prop)
            body = ("SELECT ?s WHERE { ?s <%s> ?v%s . "
                    "FILTER(?v >= ?min && ?v <= ?max) }" % (str(prop), clause))
            notes = ("数值范围脚手架（票据 §7.5 金额阈值结构位，业务阈值主会话绑定）；"
                     "TBox facet 界：%s（含/不含端点消费侧按 exclusive/inclusive 调整）" % bound_note)
            if dnote:
                notes += "；" + dnote
            self.emit("facet-filter", "按数值范围过滤 %s" % local_name(prop),
                      None, prop, body,
                      [{"name": "min", "datatype": dt, "note": "下界（实例阈值，参数化）"},
                       {"name": "max", "datatype": dt, "note": "上界（实例阈值，参数化）"}],
                      False, prop, notes)

    # ---------- op-join（对象属性 domain→range traversal） ----------

    def derive_op_join(self):
        for prop in sorted(self.g.subjects(RDF.type, OWL.ObjectProperty), key=str):
            if not self.in_base(prop):
                continue
            if not self.safe_iris(prop):
                self.gap("property-iri-unsafe", prop, "对象属性 IRI 含不安全字符，无法嵌入 SPARQL")
                continue
            doms = domain_classes(self.g, prop)
            rngs = range_classes(self.g, prop)
            patterns = ["?s <%s> ?o" % str(prop)]
            notes = []
            if len(doms) == 1 and self.safe_iris(doms[0]):
                patterns.append("?s a <%s>" % str(doms[0]))
            elif len(doms) > 1:
                notes.append("domain 联合（%s），裸 traversal" % ", ".join(local_name(d) for d in doms))
            else:
                self.gap("no-domain", prop, "对象属性无 rdfs:domain，op-join 降级裸 traversal")
                notes.append("无 domain，裸 traversal")
            if len(rngs) == 1 and self.safe_iris(rngs[0]):
                patterns.append("?o a <%s>" % str(rngs[0]))
            elif len(rngs) > 1:
                notes.append("range 联合（%s），裸 traversal" % ", ".join(local_name(r) for r in rngs))
            else:
                raw_rng = self.g.value(prop, RDFS.range)
                if isinstance(raw_rng, BNode):
                    self.gap("anonymous-range", prop, "对象属性 range 为匿名类表达式，op-join 降级裸 traversal")
                notes.append("无具名 range，裸 traversal")
            inv = self.inv.get(prop)
            if inv is not None:
                notes.append("inverseOf %s（逆路径查询主会话组合 ^<%s>）" % (local_name(inv), str(inv)))
            if (prop, RDF.type, OWL.TransitiveProperty) in self.g:
                notes.append("TransitiveProperty（传递闭包 ?s <%s>+ ?o 主会话组合）" % str(prop))
            if (prop, RDF.type, OWL.FunctionalProperty) in self.g:
                notes.append("FunctionalProperty（至多一值）")
            body = "SELECT ?s ?o WHERE { %s }" % " . ".join(patterns)
            dname = local_name(doms[0]) if len(doms) == 1 else "多类"
            rname = local_name(rngs[0]) if len(rngs) == 1 else "多类"
            self.emit("op-join", "沿 %s 关联遍历（%s→%s）" % (local_name(prop), dname, rname),
                      None, prop, body, [], False, prop,
                      "domain→range traversal/JOIN 脚手架（背书链结构位）；" + "；".join(notes)
                      if notes else "domain→range traversal/JOIN 脚手架（背书链结构位）")

    # ---------- 不承接登记 ----------

    def register_unmapped(self):
        for imp in sorted(self.g.subjects(RDF.type, SWRL.Imp), key=str):
            self.unmapped.append({"construct": str(imp), "kind": "SWRL-rule-body",
                "note": "规则前提/结论经 derived-query 取知（结论类已分流），body 不直接产模板"})
        for c in sorted(self.g.subjects(RDF.type, Namespace("http://www.w3.org/2004/02/skos/core#").Concept), key=str):
            self.unmapped.append({"construct": str(c), "kind": "SKOS-concept",
                "note": "SKOS 概念词表面（术语对齐），非实例查询对象，MVP 不产模板"})
        for prop in sorted(self.derived_props, key=str):
            self.unmapped.append({"construct": str(prop), "kind": "derived-property",
                "note": "SWRL head 结论属性（推理产物），op-join 取知需先物化，MVP 注记不单独产模板"})

    # ---------- 碰撞守卫 + 语法自检 ----------

    def check_template_id_collision(self):
        seen = {}
        for t in self.templates:
            tid = t["template_id"]
            if tid in seen:
                sys.stderr.write("exit 1: template_id 碰撞：%s\n" % tid)
                sys.exit(1)
            seen[tid] = True

    def prepare_query_selfcheck(self):
        """每模板 sparql 经 prepareQuery 解析（不执行、不篡改图）；失败→exit 1。"""
        for t in sorted(self.templates, key=lambda x: x["template_id"]):
            try:
                prepareQuery(t["sparql"])
            except Exception as exc:
                sys.stderr.write("exit 1: prepareQuery 语法自检失败（%s）：%s\n"
                                 % (t["template_id"], exc))
                sys.exit(1)

    # ---------- 输出 ----------

    def build_library(self, source_sha):
        templates = sorted(self.templates, key=lambda t: (t["kind"], t["template_id"]))
        by_kind = {}
        for t in templates:
            by_kind[t["kind"]] = by_kind.get(t["kind"], 0) + 1
        classes = [c for c in self.g.subjects(RDF.type, OWL.Class) if self.in_base(c)]
        ops = [p for p in self.g.subjects(RDF.type, OWL.ObjectProperty) if self.in_base(p)]
        dps = [p for p in self.g.subjects(RDF.type, OWL.DatatypeProperty) if self.in_base(p)]
        prefixes = {}
        for prefix, iri in STD_PREFIXES:
            prefixes[prefix] = self.base if prefix == "" else iri
        gaps = sorted(self.gaps, key=lambda u: (u["kind"], u["locator"]))
        unmapped = sorted(self.unmapped, key=lambda u: (u["kind"], u["construct"]))
        return {
            "schema_version": QUERY_SCHEMA_VERSION,
            "source_ttl": os.path.basename(self.source_path),
            "ttl_sha": source_sha[:12],
            "base_iri": self.base,
            "prefixes": dict(sorted(prefixes.items())),
            "templates": templates,
            "counts": {
                "classes": len(set(classes)),
                "object_properties": len(set(ops)),
                "data_properties": len(set(dps)),
                "templates_total": len(templates),
                "by_kind": dict(sorted(by_kind.items())),
            },
            "coverage": {
                "mapped_classes": sorted(self.mapped_classes),
                "unmapped_constructs": unmapped,
                "gaps": gaps,
            },
            "extension_slots": {
                "create": "ABox 实例创建留后续 R6 实例化管道（SPARQL UPDATE INSERT，本 MVP 不产）",
                "update": "ABox 实例更新留后续 R6（SPARQL UPDATE DELETE/INSERT，本 MVP 不产）",
                "delete": "票据示例 §7.4 删除悬置须 G1 确认（不补造，本 MVP 不产）",
            },
            "derivation": {
                "script_version": SCRIPT_VERSION,
                "library": "rdflib",
                "source_sha256": source_sha,
            },
        }

    def render_md(self, library):
        """人类目录渲染（按 KIND_ORDER 分组，确定性同源）。LF 换行。"""
        c = library["counts"]
        lines = []
        lines.append("# SPARQL Read 查询模板库（D3c，query-templates schema %s）" % QUERY_SCHEMA_VERSION)
        lines.append("")
        lines.append("> 机械派生自 `%s`（ttl_sha %s）——**非权威·可再生**，源 TTL 变更须重派生。"
                     % (library["source_ttl"], library["ttl_sha"]))
        lines.append("> CLI 只产结构脚手架（7 kind 原子 SELECT）；业务查询意图（组合拼接 + ORDER BY + "
                     "业务阈值绑定）由主会话 md 补写、S6 黄金用例消费。数据值永不进查询文本（?var 参数化）。")
        lines.append("")
        lines.append("## 计数")
        lines.append("")
        lines.append("- 类 %d / 对象属性 %d / 数据属性 %d / 模板总数 %d"
                     % (c["classes"], c["object_properties"], c["data_properties"], c["templates_total"]))
        lines.append("- 按 kind：" + " / ".join("%s %d" % (k, c["by_kind"].get(k, 0)) for k in KIND_ORDER))
        lines.append("")
        by_kind = {}
        for t in library["templates"]:
            by_kind.setdefault(t["kind"], []).append(t)
        for kind in KIND_ORDER:
            ts = by_kind.get(kind, [])
            if not ts:
                continue
            lines.append("## %s（%d）" % (kind, len(ts)))
            lines.append("")
            for t in ts:
                lines.append("### %s" % t["template_id"])
                lines.append("")
                lines.append("**%s**%s" % (t["title"], "（derived，需先物化）" if t["derived_flag"] else ""))
                lines.append("")
                lines.append("```sparql")
                lines.append(t["sparql"])
                lines.append("```")
                lines.append("")
                if t["params"]:
                    lines.append("| 参数 | datatype | 说明 |")
                    lines.append("|---|---|---|")
                    for p in t["params"]:
                        ev = p.get("enum_values")
                        note = p["note"]
                        if ev:
                            note += "；合法值域：" + ", ".join(ev)
                        lines.append("| ?%s | %s | %s |" % (p["name"], p["datatype"], note))
                    lines.append("")
                lines.append("- 溯源：`%s`%s" % (t["source_locator"],
                             "（源句 %s）" % "/".join(t["provenance"]) if t["provenance"] else ""))
                lines.append("- 注记：%s" % t["notes"])
                lines.append("")
        lines.append("## 扩展位（C/U/D 不产，留后续）")
        lines.append("")
        for k in ("create", "update", "delete"):
            lines.append("- **%s**：%s" % (k, library["extension_slots"][k]))
        lines.append("")
        gaps = library["coverage"]["gaps"]
        if gaps:
            lines.append("## gaps（不承接显式登记，%d 条）" % len(gaps))
            lines.append("")
            for u in gaps:
                lines.append("- `%s`（%s）：%s" % (u["kind"], u["locator"], u["note"]))
            lines.append("")
        unmapped = library["coverage"]["unmapped_constructs"]
        if unmapped:
            lines.append("## 不承接构件（%d 条）" % len(unmapped))
            lines.append("")
            for u in unmapped:
                lines.append("- `%s`（%s）：%s" % (u["kind"], u["construct"], u["note"]))
            lines.append("")
        return "\n".join(lines)

    def build_report(self, source_sha):
        library = self.build_library(source_sha)
        return {
            "schema_version": QUERY_SCHEMA_VERSION,
            "source_ttl": os.path.basename(self.source_path),
            "source_sha256": source_sha,
            "base_ns": self.base,
            "counts": library["counts"],
            "kind_counts": library["counts"]["by_kind"],
            "mapped_classes": library["coverage"]["mapped_classes"],
            "gaps": library["coverage"]["gaps"],
            "unmapped": library["coverage"]["unmapped_constructs"],
            "decisions": [
                "D-a TTL-direct：直接读 ontology.ttl 本地解析词汇（不改签名提取，避 T4 漂移）",
                "D-b Read 取知 MVP：7 类 SELECT；C/U/D 登记 extension_slots 留后续 R6",
                "D-c 子类闭包：class-list/derived-query/key-lookup 用 a/rdfs:subClassOf*（R-c 对齐）",
                "D-d derived 分流：SWRL head 结论类→derived-query（需先物化，联动 simulate）",
                "D-e 参数化+IRI 守卫：数据值 ?var 参数化永不进查询文本；嵌入 IRI 过 IRI_UNSAFE_RE",
            ],
        }


# ============================================================ main

def main():
    ap = argparse.ArgumentParser(description="D3c SPARQL Read 查询模板派生器（TTL-direct，纯 rdflib）")
    ap.add_argument("ttl", help="ontology.ttl（TBox，派生唯一权威素材源）")
    ap.add_argument("--output-json", default=None, help="query-templates.json（默认 cwd/query-templates.json）")
    ap.add_argument("--output-md", default=None, help="query-templates.md（默认 cwd/query-templates.md）")
    ap.add_argument("--report", default=None, help="derivation-report.json（默认 cwd/derivation-report.json）")
    args = ap.parse_args()

    src = os.path.realpath(args.ttl)
    g = load_ontology(src)          # 先存在性/解析守卫（exit 2），再算 sha（缺文件不崩溃）
    before = file_sha256(src)
    base = base_namespace(g, src)

    out_json = args.output_json or os.path.join(os.getcwd(), "query-templates.json")
    out_md = args.output_md or os.path.join(os.getcwd(), "query-templates.md")
    out_report = args.report or os.path.join(os.getcwd(), "derivation-report.json")
    for out in (out_json, out_md, out_report):
        if os.path.realpath(out) == src:
            sys.stderr.write("exit 2: 输出不得等于源 TTL：%s\n" % out)
            sys.exit(2)

    d = QueryDeriver(g, base, src)
    d.derive_classes()
    d.derive_key_lookup()
    d.derive_property_get()
    d.derive_enum_filter()
    d.derive_facet_filter()
    d.derive_op_join()
    d.register_unmapped()
    d.check_template_id_collision()
    d.prepare_query_selfcheck()

    library = d.build_library(before)
    md_text = d.render_md(library)
    report = d.build_report(before)

    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(library, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    with open(out_md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(md_text)
    with open(out_report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")

    after = file_sha256(src)
    if before != after:
        sys.stderr.write("exit 1: 零回写断言失败——源 TTL 被改动\n")
        sys.exit(1)

    c = library["counts"]
    print("派生完成：类 %d / 对象属性 %d / 数据属性 %d / 模板 %d（gaps %d）" % (
        c["classes"], c["object_properties"], c["data_properties"],
        c["templates_total"], len(library["coverage"]["gaps"])))
    print("  按 kind：" + " / ".join("%s %d" % (k, c["by_kind"].get(k, 0)) for k in KIND_ORDER))
    print("  json → %s" % out_json)
    print("  md   → %s" % out_md)
    print("  report → %s" % out_report)
    sys.exit(0)


if __name__ == "__main__":
    main()