#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_ontology.py —— 本体 TTL 机械校验（L1 语法 + L2 结构矛盾启发式）

用法:
    python3 validate_ontology.py <ontology.ttl> [--json-output <path>]

分层检查:
    L1-PARSE         rdflib turtle 解析（失败即终止，exit 2）
    L1-PREFIX        标准词表前缀 IRI 精确性（rdf/rdfs/owl/xsd/skos/swrl/swrlb 误拼
                     =该前缀下三元组静默脱离标准词表，解析不报错故列 error）
    L2-CYCLE         rdfs:subClassOf 传递闭包循环继承
    L2-PROP-CHAR     属性特征矛盾（Functional+Transitive / Functional+InverseFunctional /
                     Transitive+Irreflexive / Asymmetric+Symmetric / inverseOf 不对称）
    L2-DOMAIN-RANGE  多 domain/range 交集警告 + 悬挂引用
    L2-DISJOINT      disjoint 类之间存在 subClassOf 关联
    L2-DATATYPE      具名枚举 datatype（owl:oneOf）——Pellet 值空间判空/拒跑陷阱
    L2-IMPORTS       owl:imports IRI 格式（不联网解析）
    L2-SWRL          swrl:Imp 结构统计（body/head 存在且非空、谓词/类声明情况）
    L2-SWRL-FORM     SWRL 编译形态启发式（Pellet 2.3.1 限制⑪⑫，2026-11-02 实证）：
                     head 多原子（部分物化，结论静默丢失）+ body 同构（alpha 规范化
                     比对，判重丢弃其一）——均 warning 级，双通道标准形态见 prompt-generator.md

退出码: 2=解析失败 / 1=存在 error 级 finding / 0=零 error
依赖: 仅 rdflib + 标准库（本机无 Java，禁止引入 reasoner/owlready2）
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

from rdflib import BNode, Graph, Literal, Namespace, OWL, RDF, RDFS, URIRef
from rdflib.collection import Collection

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

# 词汇表命名空间（这些命名空间下的 IRI 不视为「本体内声明的类/属性/个体」）
VOCAB_NS = {str(OWL), str(RDF), str(RDFS), str(SWRL),
            "http://www.w3.org/2003/11/swrlb#",
            "http://www.w3.org/2004/02/skos/core#"}

# 属性特征类型 → 标注名
PROP_CHAR_TYPES = [
    (OWL.FunctionalProperty, "Functional"),
    (OWL.InverseFunctionalProperty, "InverseFunctional"),
    (OWL.TransitiveProperty, "Transitive"),
    (OWL.SymmetricProperty, "Symmetric"),
    (OWL.AsymmetricProperty, "Asymmetric"),
    (OWL.IrreflexiveProperty, "Irreflexive"),
    (OWL.ReflexiveProperty, "Reflexive"),
]

# 视为「对象属性特征」的类型（用于 stats 归类）
OBJECT_CHAR_TYPES = {OWL.ObjectProperty} | {t for t, _ in PROP_CHAR_TYPES}

IRI_RE = re.compile(r"^https?://\S+$")

# Turtle @prefix 声明（文本层扫描用——rdflib namespaces() 不回显核心前缀的文件误拼绑定）
PREFIX_DECL_RE = re.compile(r"@prefix\s+([A-Za-z0-9_.-]*)\s*:\s*<([^>]*)>", re.IGNORECASE)

# 标准词表前缀的规范 IRI（L1-PREFIX 检查基准）——前缀名相同但 IRI 误拼
# 会使该前缀下三元组静默脱离标准词表（文件仍可解析，属静默失败类缺陷）
CANONICAL_PREFIXES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "swrl": "http://www.w3.org/2003/11/swrl#",
    "swrlb": "http://www.w3.org/2003/11/swrlb#",
}


def local_name(iri):
    """取 IRI 的局部名（# 或最后一个 / 之后）"""
    s = str(iri)
    if "#" in s:
        return s.rsplit("#", 1)[-1]
    return s.rsplit("/", 1)[-1]


class Validator(object):
    def __init__(self, path):
        self.path = path
        self.graph = Graph()
        self.findings = []
        self.parse_ok = False
        self.exit_code = 0

    # ---------- 基础设施 ----------

    def add(self, check_id, severity, message, location=None):
        self.findings.append({
            "check_id": check_id,
            "severity": severity,
            "message": message,
            "location": str(location) if location is not None else None,
        })

    def subclass_pairs(self):
        """命名类之间的 rdfs:subClassOf 关系对（跳过 bnode/限制）"""
        return set(
            (s, o) for s, o in self.graph.subject_objects(RDFS.subClassOf)
            if isinstance(s, URIRef) and isinstance(o, URIRef)
        )

    def ancestors_of(self, x, pairs_graph):
        """x 的所有严格祖先（subClassOf 传递闭包，不含自身）"""
        seen = set()
        stack = list(pairs_graph.get(x, ()))
        while stack:
            y = stack.pop()
            if y not in seen:
                seen.add(y)
                stack.extend(pairs_graph.get(y, ()))
        return seen

    # ---------- L1 语法 ----------

    def check_l1_parse(self):
        try:
            self.graph.parse(self.path, format="turtle")
            self.parse_ok = True
        except Exception as exc:  # 解析失败即终止
            self.parse_ok = False
            self.add("L1-PARSE", "error",
                     "Turtle 解析失败: %s" % exc, self.path)

    def check_l1_prefix(self):
        """W3C 标准词表前缀的 IRI 精确性——误拼前缀（如 rdf 日期段写成
        连字符 1999-02-22 而非斜杠 1999/02/22）会让该前缀下所有三元组静默脱离
        标准词表：显式 `rdf:type X` 展开成误拼 IRI，reasoner/校验器全部读不到，
        而文件仍能正常解析——属静默失败类缺陷，故列 error。
        **必须文本层扫描 @prefix 声明**：rdflib 7.6 实测 graph.namespaces() 对
        核心前缀返回默认正确绑定（文件误拼声明不回显），但 turtle parser 展开
        词条时用的却是文件声明的误拼 IRI——namespaces() 路径查不出此缺陷。
        仅检查「用了标准前缀名但 IRI 不对」，不要求文件必须声明哪些前缀。"""
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except Exception as exc:
            self.add("L1-PREFIX", "warning",
                     "无法读取源文本做前缀扫描: %s" % exc, self.path)
            return
        seen = set()
        for m in PREFIX_DECL_RE.finditer(text):
            prefix, iri = m.group(1), m.group(2)
            canonical = CANONICAL_PREFIXES.get(prefix)
            if canonical is None or iri == canonical or (prefix, iri) in seen:
                continue
            seen.add((prefix, iri))
            self.add(
                "L1-PREFIX", "error",
                "前缀 %s: 声明为 <%s>，标准 IRI 应为 <%s>"
                "——该前缀下显式引用的三元组将脱离标准词表（解析不报错，静默失败）"
                % (prefix, iri, canonical),
                "@prefix %s:" % prefix)

    # ---------- L2 循环继承 ----------

    def check_l2_cycle(self):
        pairs = self.subclass_pairs()
        graph = defaultdict(set)
        for s, o in pairs:
            graph[s].add(o)
        nodes = set(graph.keys()) | set(o for _, o in pairs)
        color = dict((n, 0) for n in nodes)  # 0=未访问 1=在栈中 2=已完成
        path = []
        cycles = []

        def dfs(u):
            color[u] = 1
            path.append(u)
            for v in sorted(graph.get(u, ())):
                if color.get(v, 0) == 1:
                    i = path.index(v)
                    cyc = path[i:]
                    m = min(cyc)
                    k = cyc.index(m)
                    cyc = cyc[k:] + cyc[:k]  # 规范化去重
                    if cyc not in cycles:
                        cycles.append(cyc)
                elif color.get(v, 0) == 0:
                    dfs(v)
            path.pop()
            color[u] = 2

        for n in sorted(nodes):
            if color[n] == 0:
                dfs(n)

        for cyc in cycles:
            names = " ⊑ ".join(local_name(c) for c in cyc)
            self.add("L2-CYCLE", "error",
                     "检测到循环继承: %s ⊑ %s（传递闭包下该类等价于全部环上类）"
                     % (names, local_name(cyc[0])),
                     cyc[0])

    # ---------- L2 属性特征矛盾 ----------

    def check_l2_prop_char(self):
        g = self.graph
        chars = defaultdict(set)
        for cls, name in PROP_CHAR_TYPES:
            for p in g.subjects(RDF.type, cls):
                chars[p].add(name)

        # 矛盾组合表（error 级）
        conflicts = [
            ({"Functional", "Transitive"},
             "Functional+Transitive 共存：传递性+单值性会推出论域内全部个体相等（全域坍缩）"),
            ({"Transitive", "Irreflexive"},
             "Transitive+Irreflexive 共存：传递闭包下若存在 xPy 且 yPx 即推出 xPx，与反自反矛盾（结构上不可满足风险）"),
            ({"Asymmetric", "Symmetric"},
             "Asymmetric+Symmetric 共存：对称性要求 xPy→yPx，非对称性禁止之，直接矛盾"),
        ]
        # 合法组合降 warning（F+IFP=1:1 编码模式——OWL 语义下仅当属性全域多于一个
        # 个体时才矛盾，业务中「一一对应」声明是合法且常见的编码意图；降级后仍
        # 提示人工确认业务意图）
        soft_conflicts = [
            ({"Functional", "InverseFunctional"},
             "Functional+InverseFunctional 共存：1:1 编码模式（合法用法）——OWL 语义下"
             "仅当该属性全域存在两个不同个体时才构成矛盾；请确认业务意图确为一一对应"),
        ]
        for p, names in sorted(chars.items(), key=lambda kv: str(kv[0])):
            for combo, msg in conflicts:
                if combo.issubset(names):
                    self.add("L2-PROP-CHAR", "error",
                             "属性 %s：%s" % (local_name(p), msg), p)
            for combo, msg in soft_conflicts:
                if combo.issubset(names):
                    self.add("L2-PROP-CHAR", "warning",
                             "属性 %s：%s" % (local_name(p), msg), p)

        # inverseOf 不对称（warning）
        for p, q in g.subject_objects(OWL.inverseOf):
            if (q, OWL.inverseOf, p) not in g:
                self.add("L2-PROP-CHAR", "warning",
                         "owl:inverseOf 不对称：%s inverseOf %s 已声明，但 %s inverseOf %s 缺失"
                         % (local_name(p), local_name(q), local_name(q), local_name(p)),
                         p)

    # ---------- L2 domain/range ----------

    def known_classes(self):
        """本体内可识别的类：声明为 owl:Class/rdfs:Class，或出现在 rdf:type 三元组宾语位"""
        g = self.graph
        ks = set()
        for s in g.subjects(RDF.type, OWL.Class):
            if isinstance(s, URIRef):
                ks.add(s)
        for s in g.subjects(RDF.type, RDFS.Class):
            if isinstance(s, URIRef):
                ks.add(s)
        for o in g.objects(None, RDF.type):
            if isinstance(o, URIRef):
                ks.add(o)
        return ks

    def check_l2_domain_range(self):
        g = self.graph
        # rdfs:Datatype 自定义数据类型（owl:onDatatype+facet）是数据属性 range 的合法目标，
        # 不计悬挂（虚构载体 run 实测误报修复，2026-10-26）
        known = self.known_classes() | set(g.subjects(RDF.type, RDFS.Datatype))
        pairs_graph = defaultdict(set)
        for s, o in self.subclass_pairs():
            pairs_graph[s].add(o)

        for pred, label in ((RDFS.domain, "domain"), (RDFS.range, "range")):
            decl = defaultdict(set)
            for p, v in g.subject_objects(pred):
                decl[p].add(v)
                # 悬挂引用检查（xsd/rdf/rdfs/owl/swrl 词汇表 IRI 除外）
                # 注意：URIRef.__eq__ 不与普通 str 相等，成员判断必须用 URIRef 本体
                if isinstance(v, URIRef) and v not in known:
                    if not any(str(v).startswith(ns) for ns in VOCAB_NS) \
                            and not str(v).startswith(str(XSD)):
                        self.add("L2-DOMAIN-RANGE", "error",
                                 "悬挂引用：属性 %s 的 rdfs:%s 指向 %s，"
                                 "但该 IRI 在本体内既未声明为 owl:Class 也未出现在类型三元组中"
                                 % (local_name(p), label, local_name(v)), p)
            # 多重声明交集警告
            for p, vals in sorted(decl.items(), key=lambda kv: str(kv[0])):
                if len(vals) <= 1:
                    continue
                # 任一声明值为含 owl:unionOf 的 bnode → 视为已用 union 表达，跳过
                has_union = any(
                    isinstance(v, BNode) and g.value(v, OWL.unionOf) is not None
                    for v in vals
                )
                if has_union:
                    continue
                uris = [v for v in vals if isinstance(v, URIRef)
                        and not str(v).startswith(str(XSD))]
                if len(uris) < 2:
                    continue  # bnode 限制等无法机械判定，保守不报
                unrelated = False
                for i in range(len(uris)):
                    for j in range(i + 1, len(uris)):
                        a, b = uris[i], uris[j]
                        if b not in self.ancestors_of(a, pairs_graph) | {a} \
                                and a not in self.ancestors_of(b, pairs_graph) | {b}:
                            unrelated = True
                if unrelated:
                    self.add("L2-DOMAIN-RANGE", "warning",
                             "属性 %s 存在多个 rdfs:%s 声明（%s）且声明类之间无 subClassOf 关联："
                             "OWL 语义下多 domain/range 取交集，可能导致类不可满足"
                             % (local_name(p), label,
                                ", ".join(local_name(u) for u in uris)), p)

    # ---------- L2 不相交矛盾 ----------

    def check_l2_disjoint(self):
        g = self.graph
        pairs_graph = defaultdict(set)
        for s, o in self.subclass_pairs():
            pairs_graph[s].add(o)

        def related(a, b):
            """a 与 b 之间存在 subClassOf 传递关联（含自身相等）"""
            return a == b or b in self.ancestors_of(a, pairs_graph) \
                or a in self.ancestors_of(b, pairs_graph)

        # 二元 owl:disjointWith
        for a, b in g.subject_objects(OWL.disjointWith):
            if isinstance(a, URIRef) and isinstance(b, URIRef) and related(a, b):
                self.add("L2-DISJOINT", "error",
                         "不相交矛盾：%s 与 %s 声明 owl:disjointWith，但二者存在 subClassOf 关联"
                         "（传递闭包下一方为另一方子类，disjoint 将推出该类不可满足）"
                         % (local_name(a), local_name(b)), a)

        # owl:AllDisjointClasses 的 owl:members 列表
        for node in g.subjects(RDF.type, OWL.AllDisjointClasses):
            members_node = g.value(node, OWL.members)
            if members_node is None:
                continue
            try:
                members = [m for m in Collection(g, members_node)
                           if isinstance(m, URIRef)]
            except Exception:
                continue
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    if related(members[i], members[j]):
                        self.add("L2-DISJOINT", "error",
                                 "不相交矛盾：AllDisjointClasses 成员 %s 与 %s 存在 subClassOf 关联"
                                 % (local_name(members[i]), local_name(members[j])),
                                 members[i])

    # ---------- L2 imports ----------

    def check_l2_datatype(self):
        # 具名枚举 datatype 陷阱（2026-10-26 Pellet 三变体实测定案，reasoner-limits 限制⑨）：
        #   rdfs:Datatype + owl:oneOf 具名实体——无 onDatatype：Pellet 值空间判空
        #   （引用它的 owl:hasValue 定义类静默不可满足 ≡⊥，HermiT 掩盖）；
        #   有 onDatatype：Pellet 拒跑（"Trying to use a literal as an individual"）。
        #   唯一兼容形态 = range 内联匿名 oneOf（不声明具名实体）
        g = self.graph
        for dt in sorted(g.subjects(RDF.type, RDFS.Datatype), key=str):
            if not isinstance(dt, URIRef) or g.value(dt, OWL.oneOf) is None:
                continue
            if g.value(dt, OWL.onDatatype) is not None:
                self.add("L2-DATATYPE", "error",
                         "具名枚举 datatype %s 为 onDatatype+oneOf 组合——Pellet 拒绝运行"
                         "（literal as individual）；改用 range 内联匿名 oneOf"
                         % local_name(dt), dt)
            else:
                self.add("L2-DATATYPE", "error",
                         "具名枚举 datatype %s 仅 owl:oneOf 无 onDatatype——Pellet 值空间判空，"
                         "引用它的 owl:hasValue 定义类将静默不可满足；改用 range 内联匿名 oneOf"
                         % local_name(dt), dt)

    def check_l2_imports(self):
        for s, o in self.graph.subject_objects(OWL.imports):
            ok = isinstance(o, URIRef) and IRI_RE.match(str(o)) is not None
            if ok:
                parsed = urlparse(str(o))
                ok = bool(parsed.scheme in ("http", "https") and parsed.netloc)
            if not ok:
                self.add("L2-IMPORTS", "warning",
                         "owl:imports 值不是合法 http(s) IRI 格式：%r（不做联网解析，仅格式校验）"
                         % (o,), s)

    # ---------- L2 SWRL ----------

    def check_l2_swrl(self):
        g = self.graph
        imps = sorted(g.subjects(RDF.type, SWRL.Imp), key=str)
        declared_terms = set(g.subjects(RDF.type, None))  # 有任何 rdf:type 声明的词项

        for idx, imp in enumerate(imps, 1):
            rule_loc = imp if isinstance(imp, URIRef) else "swrl:Imp#%d" % idx
            for part, pname in ((SWRL.body, "swrl:body"), (SWRL.head, "swrl:head")):
                node = g.value(imp, part)
                if node is None:
                    self.add("L2-SWRL", "warning",
                             "SWRL 规则 #%d 缺失 %s" % (idx, pname), rule_loc)
                    continue
                if node == RDF.nil:
                    self.add("L2-SWRL", "warning",
                             "SWRL 规则 #%d 的 %s 为空列表（rdf:nil）" % (idx, pname),
                             rule_loc)
                    continue
                try:
                    items = list(Collection(g, node))
                except Exception as exc:
                    self.add("L2-SWRL", "warning",
                             "SWRL 规则 #%d 的 %s 无法按 rdf:List 解析：%s"
                             % (idx, pname, exc), rule_loc)
                    continue
                if not items:
                    self.add("L2-SWRL", "warning",
                             "SWRL 规则 #%d 的 %s 解析为空列表" % (idx, pname), rule_loc)
                    continue
                # 原子中引用的谓词/类是否在本体声明
                for atom in items:
                    for apred in (SWRL.classPredicate, SWRL.propertyPredicate):
                        ref = g.value(atom, apred)
                        if isinstance(ref, URIRef) and ref not in declared_terms \
                                and not any(str(ref).startswith(ns) for ns in VOCAB_NS):
                            self.add("L2-SWRL", "info",
                                     "SWRL 规则 #%d 引用的谓词/类 %s 未在本体中声明（无 rdf:type）"
                                     % (idx, local_name(ref)), rule_loc)

    # ---------- L2 SWRL 编译形态启发式（Pellet 限制⑪⑫，2026-11-02 实证） ----------

    def _atom_signature(self, atom, var_map):
        """SWRL 原子 → alpha 规范化签名：变量按首次出现序重命名（v0/v1/...），
        字面量与具名个体保留原值——用于同构 body 比对（限制⑫：Pellet 对
        alpha 规范化后句法一致的规则判重丢弃其一，且重排原子顺序无效）"""
        g = self.graph
        cls_pred = g.value(atom, SWRL.classPredicate)
        prop_pred = g.value(atom, SWRL.propertyPredicate)
        kind = "cls" if cls_pred is not None else "prop"
        pred = str(cls_pred if cls_pred is not None else prop_pred)
        args = []
        for ap in (SWRL.argument1, SWRL.argument2):
            a = g.value(atom, ap)
            if a is None:
                args.append(None)
            elif isinstance(a, Literal):
                args.append(("lit", str(a)))
            elif isinstance(a, URIRef) and g.value(a, RDF.type) != SWRL.Variable:
                args.append(("ind", str(a)))
            else:  # 变量（bnode 或 URIRef 形态的 swrl:Variable 均按变量处理）
                if a not in var_map:
                    var_map[a] = "v%d" % len(var_map)
                args.append(("var", var_map[a]))
        return (kind, pred, tuple(args))

    def check_l2_swrl_form(self):
        g = self.graph
        imps = sorted(g.subjects(RDF.type, SWRL.Imp), key=str)
        body_index = {}  # 规范化 body 签名 → 首见规则标识
        for idx, imp in enumerate(imps, 1):
            rule_loc = imp if isinstance(imp, URIRef) else "swrl:Imp#%d" % idx
            rule_tag = local_name(imp) if isinstance(imp, URIRef) else "#%d" % idx
            # 限制⑪：head 多原子 → Pellet 仅部分物化（确定性丢其一，结论静默丢失）
            head_node = g.value(imp, SWRL.head)
            if head_node is not None and head_node != RDF.nil:
                try:
                    head_items = list(Collection(g, head_node))
                except Exception:
                    head_items = []
                if len(head_items) > 1:
                    self.add("L2-SWRL-FORM", "warning",
                             "SWRL 规则 %s head 含 %d 个原子——Pellet 2.3.1 对多原子 head "
                             "仅部分物化（限制⑪，确定性丢失其一，head 内顺序无关）；应拆分为多条"
                             "单 head 规则（双通道标准形态见 prompt-generator.md「SWRL 编译形态约束」）"
                             % (rule_tag, len(head_items)), rule_loc)
            # 限制⑫：同构 body（alpha 规范化后句法一致 → Pellet 判重丢弃其一）
            body_node = g.value(imp, SWRL.body)
            if body_node is not None and body_node != RDF.nil:
                try:
                    body_items = list(Collection(g, body_node))
                except Exception:
                    body_items = []
                if body_items:
                    var_map = {}
                    try:
                        sig = tuple(sorted(
                            self._atom_signature(a, var_map) for a in body_items))
                    except Exception:
                        sig = None
                    if sig is not None:
                        if sig in body_index:
                            self.add("L2-SWRL-FORM", "warning",
                                     "SWRL 规则 %s 与规则 %s body 同构（变量 alpha 规范化后句法一致）"
                                     "——Pellet 2.3.1 判重丢弃其一（限制⑫，静默失效；重排原子顺序、"
                                     "加被 DL 蕴含吸收的哑原子均无效）；双通道拆分时通道二 body 须将"
                                     "定义类原子按等价类定义展开为字面量原子以保句法相异"
                                     % (rule_tag, body_index[sig]), rule_loc)
                        else:
                            body_index[sig] = rule_tag

    # ---------- 统计 ----------

    def build_stats(self):
        g = self.graph
        classes = set(s for s in g.subjects(RDF.type, OWL.Class)
                      if isinstance(s, URIRef))
        dt_props = set(g.subjects(RDF.type, OWL.DatatypeProperty))
        obj_props = set()
        for cls, _ in PROP_CHAR_TYPES:
            obj_props |= set(g.subjects(RDF.type, cls))
        obj_props |= set(g.subjects(RDF.type, OWL.ObjectProperty))
        obj_props -= dt_props
        # 个体：rdf:type 指向非词汇表类的主体（排除类/属性自身声明）
        individuals = set()
        for s, o in g.subject_objects(RDF.type):
            if isinstance(o, URIRef) \
                    and not any(str(o).startswith(ns) for ns in VOCAB_NS) \
                    and str(o) != str(XSD):
                individuals.add(s)
        imps = set(g.subjects(RDF.type, SWRL.Imp))
        return {
            "classes": len(classes),
            "object_properties": len(obj_props),
            "datatype_properties": len(dt_props),
            "individuals": len(individuals),
            "swrl_rules": len(imps),
            "imports": len(list(g.subject_objects(OWL.imports))),
            "axioms_triples": len(g),
        }

    # ---------- 主流程 ----------

    def run(self):
        self.check_l1_parse()
        if self.parse_ok:
            self.check_l1_prefix()
            self.check_l2_cycle()
            self.check_l2_prop_char()
            self.check_l2_domain_range()
            self.check_l2_disjoint()
            self.check_l2_datatype()
            self.check_l2_imports()
            self.check_l2_swrl()
            self.check_l2_swrl_form()
        errors = sum(1 for f in self.findings if f["severity"] == "error")
        self.exit_code = 0 if (self.parse_ok and errors == 0) else (2 if not self.parse_ok else 1)
        return self.to_json_obj()

    def to_json_obj(self):
        summary = {
            "errors": sum(1 for f in self.findings if f["severity"] == "error"),
            "warnings": sum(1 for f in self.findings if f["severity"] == "warning"),
            "infos": sum(1 for f in self.findings if f["severity"] == "info"),
        }
        return {
            "file": self.path,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "parse_ok": self.parse_ok,
            "exit_code": self.exit_code,
            "summary": summary,
            "findings": self.findings,
            "stats": self.build_stats() if self.parse_ok else {},
        }


def print_human(result):
    """打印人类可读摘要"""
    print("=" * 60)
    print("本体机械校验报告: %s" % result["file"])
    print("解析: %s | 生成时间: %s" % (
        "OK" if result["parse_ok"] else "FAILED", result["generated_at"]))
    s = result["summary"]
    print("汇总: errors=%d warnings=%d infos=%d" % (s["errors"], s["warnings"], s["infos"]))
    if result["findings"]:
        print("-" * 60)
        for f in result["findings"]:
            loc = " @ %s" % f["location"] if f["location"] else ""
            print("[%s][%s] %s%s" % (f["severity"].upper(), f["check_id"], f["message"], loc))
    if result["stats"]:
        print("-" * 60)
        st = result["stats"]
        print("统计: 类=%d 对象属性=%d 数据属性=%d 个体=%d SWRL规则=%d imports=%d 三元组=%d"
              % (st["classes"], st["object_properties"], st["datatype_properties"],
                 st["individuals"], st["swrl_rules"], st["imports"], st["axioms_triples"]))
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="本体 TTL 机械校验（L1 语法 + L2 结构矛盾启发式，仅 rdflib，无 Java 依赖）")
    parser.add_argument("ontology", help="待校验的本体 TTL 文件路径")
    parser.add_argument("--json-output", dest="json_output", default=None,
                        help="将 JSON 结果写入指定文件（缺省时 JSON 打印到 stdout）")
    args = parser.parse_args()

    v = Validator(args.ontology)
    result = v.run()
    print_human(result)
    json_text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as fh:
            fh.write(json_text + "\n")
        print("JSON 已写入: %s" % args.json_output)
    else:
        print(json_text)
    sys.exit(v.exit_code)


if __name__ == "__main__":
    main()
