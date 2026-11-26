#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""incremental_patch.py —— R2 增量 patch 引擎（机械 backbone，短期 CLI 能力增强首项）。

定位
----
消费结构化编辑操作 JSON → rdflib 增量修改产 **draft TTL**（不覆盖权威）→ L1/L2 复检
（零新增 error delta 闸门）+ 可选 L3 + 黄金用例受影响子集回归守护 → 版本 diff + 语义版本号。
R2 是 D4 拖拽编辑的机械 patch 地基；「意见→编辑操作」的语义翻译由外接编排器（LLM/D4 前端）
承担，R2 只机械执行 + 校验 + 回归守护，不做业务裁量、不含 LLM 调用。

纪律（不可绕过）
----------------
- **draft 非权威**：意见单 schema §四.2「意见不改本体文件，一切形式化修改走入口 (c)」零改动。
  R2 产 draft + report，report 携带 entry_c.status=pending_audit；draft→权威仍走入口 (c)
  S4 审计→G2/G3→人工晋升，R2 永不执行晋升。
- **零回写**：baseline TTL + golden JSON + patch 输入三文件 sha256 前后断言；输出 realpath
  碰撞守卫（不得等于任一输入）；默认输出落 cwd，不进 baseline 所在 run 目录。
- **纯 rdflib 核心**：顶层只 import 标准库 + rdflib + 同目录 rdflib-only 复用模块；
  owlready2/推理层经 run_one 函数内延迟导入。
- **bnode 不可寻址**：跨 parse 的 bnode 标签随机（实证 remove no-op），契约禁 `_:` 项；
  SWRL 编辑走规则级 remove_rule/replace_rule（整片段按硬规范 v2），绕开 atom 级 bnode 手术。
- **单 parse 工作图**：baseline parse 一次 → 三元组复制到 draft 图（bnode 对象共享），
  所有操作在同一工作图解析执行；diff 用原图集合差（保 bnode 同一性供锚点回溯），
  report 渲染经 to_canonical_graph 取确定性 cb 标签（确定性纪律）。

契约：assets/tpl-patch-schema.md（patch JSON schema 1.0 + 操作目录 + 项编码）。
复用：validate_ontology.Validator（L1/L2）/ run_golden_cases.run_one+canonicalize_base（回归）
      / check_consistency.strip_swrl（MAJOR 闭包检测）+ subprocess（L3）。
      规则级联删除按 simulate_reason._destroy_list/drop_rule 同算法图级实现（不 import：
      其顶层 import owlready2 破坏 rdflib-only 核心 + model→simulate 反向分层）。

退出码：2=应用前输入错（不产 draft，仅 stderr）/ 0=released / 1=blocked（校验失败/回归检出/
        MAJOR 无守护）。exit 0/1 均产 draft+report（blocked draft 供检视/D4 UI 渲染）。

用法：
  python3 incremental_patch.py <baseline.ttl> <patch.json> [--golden cases.json]
      [--with-l3] [--output-draft PATH] [--report PATH]
      [--bump auto|major|minor|patch] [--strict] [--regression-full] [--cache-dir DIR]
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import deque
from datetime import datetime

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD
from rdflib.collection import Collection
from rdflib.compare import to_canonical_graph

# 同目录复用（rdflib-only 模块，顶层仅标准库/rdflib，不破坏纯 rdflib 核心）
from validate_ontology import (Validator, VOCAB_NS, PREFIX_DECL_RE, local_name)
from run_golden_cases import (run_one, canonicalize_base, _prefix_header,
                              find_java, validate_schema)
from check_consistency import strip_swrl

SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
SWRLB = "http://www.w3.org/2003/11/swrlb#"
SCHEMA_VERSION = "1.0"
OPS = ("add_triple", "remove_triple", "replace_literal", "modify_label",
       "add_class", "add_property", "remove_rule", "replace_rule")
CHANNELS = ("opinion", "d4", "manual")
BUMPS = ("auto", "major", "minor", "patch")
BUMP_RANK = {"patch": 0, "minor": 1, "major": 2}

# 词汇表前缀（这些命名空间下的 IRI 不视为本体声明的类/属性/个体）——VOCAB_NS + XSD
VOCAB_PREFIXES = tuple(VOCAB_NS) + (str(XSD),)

# 注解谓词（变更不触及结构/规则语义；annotation_only 判定另需安全检查）
ANNOTATION_PREDS = {
    RDFS.label, RDFS.comment, RDFS.seeAlso, RDFS.isDefinedBy,
    OWL.versionInfo, OWL.priorVersion, OWL.backwardCompatibleWith, OWL.incompatibleWith,
    SKOS.prefLabel, SKOS.altLabel, SKOS.hiddenLabel, SKOS.definition, SKOS.note,
    SKOS.scopeNote, SKOS.example, SKOS.historyNote, SKOS.editorialNote, SKOS.changeNote,
}
PROP_CHAR_TYPES = (OWL.FunctionalProperty, OWL.InverseFunctionalProperty,
                   OWL.TransitiveProperty, OWL.SymmetricProperty, OWL.AsymmetricProperty,
                   OWL.IrreflexiveProperty, OWL.ReflexiveProperty)


class PatchError(Exception):
    """应用前/应用中输入错（exit 2，不产 draft）。"""


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_vocab(iri):
    return any(str(iri).startswith(ns) for ns in VOCAB_PREFIXES)


# ============================================================ ① 输入契约层

def parse_prefix_map(base_text):
    """从 baseline 文本 @prefix 声明解析前缀映射（与文件书写词条同 convention）。"""
    pmap = {}
    for m in PREFIX_DECL_RE.finditer(base_text):
        pmap[m.group(1)] = m.group(2)
    return pmap


def resolve_term(raw, pmap, pos):
    """项编码契约：字符串=IRI 引用（全 IRI/前缀名/裸 localname→默认 ns）；
    dict=字面量{value,lang|datatype}；JSON number/bool 仅 o 位→xsd 类型字面量。
    `_:` 项一律拒绝（bnode 跨 parse 不可寻址）。"""
    if isinstance(raw, dict):
        if "value" not in raw:
            raise PatchError("%s 位字面量 dict 缺 value: %r" % (pos, raw))
        val = raw["value"]
        if raw.get("lang"):
            return Literal(val, lang=raw["lang"])
        if raw.get("datatype"):
            dt = resolve_term(raw["datatype"], pmap, pos + ".datatype")
            if not isinstance(dt, URIRef):
                raise PatchError("%s 位 datatype 须解析为 IRI: %r" % (pos, raw["datatype"]))
            return Literal(val, datatype=dt)
        return Literal(val)
    if isinstance(raw, bool):
        if pos != "o":
            raise PatchError("JSON bool 仅允许 o 位（%s 位: %r）" % (pos, raw))
        return Literal(raw, datatype=XSD.boolean)
    if isinstance(raw, (int, float)):
        if pos != "o":
            raise PatchError("JSON number 仅允许 o 位（%s 位: %r）" % (pos, raw))
        return Literal(raw, datatype=XSD.integer if isinstance(raw, int) else XSD.decimal)
    if not isinstance(raw, str):
        raise PatchError("%s 位项须为字符串(IRI)/dict(字面量)/number/bool: %r" % (pos, raw))
    if raw.startswith("_:"):
        raise PatchError("%s 位禁止 bnode 项 `_:`（跨 parse 不可寻址）: %r" % (pos, raw))
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw) or raw.startswith("urn:"):
        return URIRef(raw)
    if ":" in raw:
        prefix, local = raw.split(":", 1)
        if prefix not in pmap:
            raise PatchError("%s 位未知前缀 %r（baseline 未声明）: %r" % (pos, prefix, raw))
        return URIRef(pmap[prefix] + local)
    # 裸 localname → 默认 ns（: 前缀）
    if "" not in pmap:
        raise PatchError("%s 位裸名 %r 需默认 ns（baseline 无 @prefix : 声明）" % (pos, raw))
    return URIRef(pmap[""] + raw)


def _require(op, idx, *fields):
    for f in fields:
        if f not in op:
            raise PatchError("operations[%d] %s 缺必填字段 %r" % (idx, op.get("op"), f))


def validate_patch(data):
    """schema 层校验（项解析在 apply 阶段）。返回 errs[]。"""
    errs = []
    if not isinstance(data, dict):
        return ["顶层须为 JSON object"]
    if data.get("schema_version") != SCHEMA_VERSION:
        errs.append("schema_version 须为 %s（实际 %r）" % (SCHEMA_VERSION, data.get("schema_version")))
    bl = data.get("baseline")
    if not isinstance(bl, dict) or not bl.get("path"):
        errs.append("baseline.path 缺失")
    sha = (bl or {}).get("sha256", "")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        errs.append("baseline.sha256 须为 64 位十六进制（错配防陈旧 patch）")
    src = data.get("source")
    if not isinstance(src, dict) or src.get("channel") not in CHANNELS:
        errs.append("source.channel 须为 %s 之一" % "/".join(CHANNELS))
    if data.get("bump", "auto") not in BUMPS:
        errs.append("bump 须为 %s 之一" % "/".join(BUMPS))
    ops = data.get("operations")
    if not isinstance(ops, list) or not ops:
        return errs + ["operations 缺失或非非空列表"]
    for i, op in enumerate(ops):
        if not isinstance(op, dict) or op.get("op") not in OPS:
            errs.append("operations[%d].op 须为 %s 之一（实际 %r）" % (i, "/".join(OPS), (op or {}).get("op")))
    return errs


def load_baseline(path, patch):
    if not os.path.isfile(path):
        raise PatchError("baseline 文件不存在: %s" % path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    sha = sha256_text(text)
    want = patch["baseline"]["sha256"]
    if sha != want:
        raise PatchError("baseline sha256 错配（防陈旧 patch）：文件 %s ≠ patch 声明 %s" % (sha[:12], want[:12]))
    g = Graph()
    try:
        g.parse(data=text, format="turtle")
    except Exception as exc:
        raise PatchError("baseline Turtle 解析失败: %s" % exc)
    return text, g, sha


# ============================================================ ② 操作执行层

def _destroy_list(g, node):
    """递归销毁 rdf:List 节点链（含 first 指向的 bnode atom 本体三元组）。
    算法出处：simulate_reason._destroy_list（同算法图级实现，不 import）。"""
    while node is not None and isinstance(node, BNode):
        first = g.value(node, RDF.first)
        rest = g.value(node, RDF.rest)
        if first is not None and isinstance(first, BNode):
            for t in list(g.triples((first, None, None))):
                g.remove(t)
            for t in list(g.triples((None, None, first))):
                g.remove(t)
        for t in list(g.triples((node, None, None))):
            g.remove(t)
        node = rest if isinstance(rest, BNode) else None


def remove_rule_cascade(g, imp):
    """删除一条 swrl:Imp（具名实体 + body/head bnode 链级联 + 孤儿变量清理）。
    算法出处：simulate_reason.drop_rule（同算法图级实现，精确 IRI 匹配非子串）。"""
    for pred in (SWRL.body, SWRL.head):
        lst = g.value(imp, pred)
        if lst is not None:
            _destroy_list(g, lst)
            g.remove((imp, pred, lst))
    for t in list(g.triples((imp, None, None))):
        g.remove(t)
    for var in list(g.subjects(RDF.type, SWRL.Variable)):
        if sum(1 for _ in g.triples((None, None, var))) == 0:
            for t in list(g.triples((var, None, None))):
                g.remove(t)


def parse_rule_fragment(header, frag, imp_iri):
    """replace_rule 片段机械校验（硬规范 v2）：禁前缀声明 / 恰 1 swrl:Imp 且 IRI 匹配 /
    变量全具名（URIRef swrl:Variable，禁 bnode 变量）。返回片段三元组列表。"""
    if re.search(r"@prefix|@base", frag):
        raise PatchError("replace_rule 片段禁含 @prefix/@base 声明（复用 baseline 前缀语境）")
    fg = Graph()
    try:
        fg.parse(data=header + "\n" + frag, format="turtle")
    except Exception as exc:
        raise PatchError("replace_rule 片段 Turtle 解析失败: %s" % exc)
    imps = list(fg.subjects(RDF.type, SWRL.Imp))
    if len(imps) != 1:
        raise PatchError("replace_rule 片段须恰含 1 个 swrl:Imp（实际 %d）" % len(imps))
    if imps[0] != imp_iri:
        raise PatchError("replace_rule 片段 Imp IRI %s 与目标 %s 不匹配" % (imps[0], imp_iri))
    for var in fg.subjects(RDF.type, SWRL.Variable):
        if not isinstance(var, URIRef):
            raise PatchError("replace_rule 片段含 bnode 变量——硬规范 v2 要求变量全具名（swrl:Variable URIRef）")
    return list(fg)


def _add_literal_pred(g, s, pred, value, lang, pmap):
    if value is None:
        return
    lit = Literal(value, lang=lang) if lang else Literal(value)
    g.add((s, pred, lit))


def apply_operations(g_base, ops, pmap, header):
    """单 parse 工作图：复制 baseline 三元组（bnode 对象共享）→ 逐 op 解析执行。
    任一失败 raise PatchError（abort 不产 draft）。返回 (g_draft, op_records)。"""
    g = Graph()
    for t in g_base:
        g.add(t)
    for prefix, ns in g_base.namespaces():
        g.bind(prefix, ns)
    records = []
    for idx, op in enumerate(ops):
        kind = op["op"]
        rec = {"index": idx, "op": kind, "status": "applied", "source": "user", "detail": ""}
        if kind == "add_triple":
            _require(op, idx, "s", "p", "o")
            s = resolve_term(op["s"], pmap, "s"); p = resolve_term(op["p"], pmap, "p")
            o = resolve_term(op["o"], pmap, "o")
            if not isinstance(s, URIRef) or not isinstance(p, URIRef):
                raise PatchError("operations[%d] add_triple s/p 须为 IRI" % idx)
            if (s, p, o) in g:
                rec["status"] = "noop"; rec["detail"] = "三元组已存在（幂等）"
            else:
                g.add((s, p, o))
        elif kind == "remove_triple":
            _require(op, idx, "s", "p", "o")
            s = resolve_term(op["s"], pmap, "s"); p = resolve_term(op["p"], pmap, "p")
            o = resolve_term(op["o"], pmap, "o")
            if (s, p, o) not in g:
                objs = [str(x) for x in g.objects(s, p)]
                raise PatchError("operations[%d] remove_triple 目标不存在 %s %s %s（实际宾语: %s）"
                                 % (idx, s, p, o, objs[:8]))
            g.remove((s, p, o))
        elif kind == "replace_literal":
            _require(op, idx, "p", "old", "new")
            p = resolve_term(op["p"], pmap, "p")
            old = resolve_term(op["old"], pmap, "old"); new = resolve_term(op["new"], pmap, "new")
            s = resolve_term(op["s"], pmap, "s") if op.get("s") else None
            matches = list(g.triples((s, p, old)))
            if len(matches) != 1:
                raise PatchError("operations[%d] replace_literal 匹配 %d 处（须全图唯一，s 省略时按 (None,p,old)）"
                                 % (idx, len(matches)))
            ms, mp, mo = matches[0]
            g.remove((ms, mp, mo)); g.add((ms, mp, new))
            rec["detail"] = "锚点 subject=%s" % ms
        elif kind == "modify_label":
            _require(op, idx, "target", "label")
            target = resolve_term(op["target"], pmap, "target")
            old_labels = list(g.objects(target, RDFS.label))
            lang = op.get("lang")
            if lang is None and old_labels:
                lang = old_labels[0].language if isinstance(old_labels[0], Literal) else None
            for t in list(g.triples((target, RDFS.label, None))):
                g.remove(t)
            g.add((target, RDFS.label, Literal(op["label"], lang=lang) if lang else Literal(op["label"])))
            rec["detail"] = "清旧 label %d 条，单值化" % len(old_labels)
        elif kind == "add_class":
            _require(op, idx, "id")
            cid = resolve_term(op["id"], pmap, "id")
            if (cid, RDF.type, OWL.Class) in g:
                raise PatchError("operations[%d] add_class id %s 已声明" % (idx, cid))
            g.add((cid, RDF.type, OWL.Class))
            _add_literal_pred(g, cid, RDFS.label, op.get("label"), op.get("lang"), pmap)
            _add_literal_pred(g, cid, RDFS.comment, op.get("comment"), None, pmap)
            sup = op.get("subclass_of")
            if sup is not None:
                for s in (sup if isinstance(sup, list) else [sup]):
                    g.add((cid, RDFS.subClassOf, resolve_term(s, pmap, "subclass_of")))
            rec["status"] = "compiled"
        elif kind == "add_property":
            _require(op, idx, "id", "kind")
            pid = resolve_term(op["id"], pmap, "id")
            if op["kind"] not in ("object", "datatype"):
                raise PatchError("operations[%d] add_property.kind 须 object|datatype" % idx)
            ptype = OWL.ObjectProperty if op["kind"] == "object" else OWL.DatatypeProperty
            if (pid, RDF.type, ptype) in g:
                raise PatchError("operations[%d] add_property id %s 已声明" % (idx, pid))
            g.add((pid, RDF.type, ptype))
            if op.get("domain") is not None:
                g.add((pid, RDFS.domain, resolve_term(op["domain"], pmap, "domain")))
            if op.get("range") is not None:
                g.add((pid, RDFS.range, resolve_term(op["range"], pmap, "range")))
            _add_literal_pred(g, pid, RDFS.label, op.get("label"), op.get("lang"), pmap)
            _add_literal_pred(g, pid, RDFS.comment, op.get("comment"), None, pmap)
            for ch in op.get("characteristics", []):
                g.add((pid, RDF.type, resolve_term(ch, pmap, "characteristics")))
            rec["status"] = "compiled"
        elif kind == "remove_rule":
            _require(op, idx, "rule")
            imp = resolve_term(op["rule"], pmap, "rule")
            if (imp, RDF.type, SWRL.Imp) not in g:
                raise PatchError("operations[%d] remove_rule 目标 %s 非 swrl:Imp" % (idx, imp))
            remove_rule_cascade(g, imp)
            rec["detail"] = "级联删除 + 孤儿变量清理"
        elif kind == "replace_rule":
            _require(op, idx, "rule", "ttl")
            imp = resolve_term(op["rule"], pmap, "rule")
            if (imp, RDF.type, SWRL.Imp) not in g:
                raise PatchError("operations[%d] replace_rule 目标 %s 非 swrl:Imp" % (idx, imp))
            frag_triples = parse_rule_fragment(header, op["ttl"], imp)
            remove_rule_cascade(g, imp)
            for t in frag_triples:
                g.add(t)
            rec["detail"] = "旧规则级联删 + 新片段并入（%d 三元组）" % len(frag_triples)
        records.append(rec)
    return g, records


# ============================================================ ③ diff 与版本层

def set_diff(g_base, g_draft):
    """原图集合差（保 bnode 同一性供锚点回溯）。返回 (removed, added) 三元组列表。"""
    base_set = set(g_base)
    draft_set = set(g_draft)
    removed = [t for t in g_base if t not in draft_set]
    added = [t for t in g_draft if t not in base_set]
    return removed, added


def _canonical_nt_lines(triples):
    """diff 三元组 → 确定性 NT 行（to_canonical_graph 重标 bnode 为 cb 哈希标签，
    跨进程确定，report 无随机标签泄漏）。"""
    if not triples:
        return []
    g = Graph()
    for t in triples:
        g.add(t)
    gc = to_canonical_graph(g)
    nt = gc.serialize(format="nt")
    return sorted(l.strip() for l in nt.splitlines() if l.strip())


def render_diff(removed, added):
    return {
        "removed_n": len(removed), "added_n": len(added),
        "removed_triples": _canonical_nt_lines(removed),
        "added_triples": _canonical_nt_lines(added),
    }


def anchor_resolve(g, node):
    """bnode → 反向 BFS 回溯具名 owner（oneOf list cell → 承载属性 IRI）。"""
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


def rule_referenced_iris(g):
    """全部规则 body/head 原子引用的 classPredicate/propertyPredicate IRI（非词汇表）。"""
    refs = set()
    for imp in g.subjects(RDF.type, SWRL.Imp):
        for part in (SWRL.body, SWRL.head):
            node = g.value(imp, part)
            if node is None or node == RDF.nil:
                continue
            try:
                atoms = list(Collection(g, node))
            except Exception:
                continue
            for atom in atoms:
                for ap in (SWRL.classPredicate, SWRL.propertyPredicate):
                    ref = g.value(atom, ap)
                    if isinstance(ref, URIRef) and not is_vocab(ref):
                        refs.add(ref)
    return refs


def declared_property_preds(g):
    preds = set(g.subjects(RDF.type, OWL.ObjectProperty))
    preds |= set(g.subjects(RDF.type, OWL.DatatypeProperty))
    for cls in PROP_CHAR_TYPES:
        preds |= set(g.subjects(RDF.type, cls))
    return preds


def semantic_affected(removed, added, g_base, g_draft):
    """diff → 受影响集。返回 (aff_sem, aff_ann, unanchored, annotation_only)。"""
    aff_sem, aff_ann, unanchored = set(), set(), False
    ann_preds_used = set()
    for t in list(removed) + list(added):
        s, p, o = t
        if p in ANNOTATION_PREDS:
            ann_preds_used.add(p)
            if isinstance(s, URIRef):
                aff_ann.add(s)
            else:
                aff_ann |= anchor_resolve(g_base, s) | anchor_resolve(g_draft, s)
            continue
        for term in t:
            if isinstance(term, URIRef):
                if not is_vocab(term):
                    aff_sem.add(term)
            elif isinstance(term, BNode):
                anchors = anchor_resolve(g_base, term) | anchor_resolve(g_draft, term)
                if anchors:
                    aff_sem |= anchors
                else:
                    unanchored = True
    # annotation_only 安全检查：注解谓词未被规则引用、未声明为 OWL 属性
    union = Graph()
    for t in g_base:
        union.add(t)
    for t in g_draft:
        union.add(t)
    rule_preds = rule_referenced_iris(union)
    prop_preds = declared_property_preds(union)
    safe = all(p not in rule_preds and p not in prop_preds for p in ann_preds_used)
    annotation_only = (not aff_sem) and bool(aff_ann) and safe
    return aff_sem, aff_ann, unanchored, annotation_only


def touches_global(removed, added, g_base, g_draft):
    """diff 触及 owl:imports / Ontology 级公理（versionInfo 除外）→ 强制全集。"""
    onto_subjects = set(g_base.subjects(RDF.type, OWL.Ontology)) | set(g_draft.subjects(RDF.type, OWL.Ontology))
    for s, p, o in list(removed) + list(added):
        if p == OWL.imports:
            return True
        if s in onto_subjects and p != OWL.versionInfo:
            return True
    return False




def rule_closure_triples(g):
    """strip_swrl 剥离的 bnode 闭包三元组集（MAJOR 检测通道②：纯原子重排只动 rdf:first/rest）。"""
    gc = Graph()
    for t in g:
        gc.add(t)
    strip_swrl(gc)
    gc_set = set(gc)
    return set(t for t in g if t not in gc_set)


def detect_rule_touched(removed, added, g_base, g_draft):
    """MAJOR 双通道：① diff p/o 触及 SWRL/SWRLB 词汇或 s 为 swrl:Imp/Variable 类型；
    ② diff 命中规则 bnode 闭包（strip_swrl）。"""
    diff = list(removed) + list(added)
    imp_subjects = set(g_base.subjects(RDF.type, SWRL.Imp)) | set(g_draft.subjects(RDF.type, SWRL.Imp))
    var_subjects = set(g_base.subjects(RDF.type, SWRL.Variable)) | set(g_draft.subjects(RDF.type, SWRL.Variable))
    for s, p, o in diff:
        if str(p).startswith(str(SWRL)) or str(p).startswith(SWRLB):
            return True
        if isinstance(o, URIRef) and (str(o).startswith(str(SWRL)) or str(o).startswith(SWRLB)):
            return True
        if s in imp_subjects or s in var_subjects:
            return True
    closure = rule_closure_triples(g_base) | rule_closure_triples(g_draft)
    if any(t in closure for t in diff):
        return True
    return False


def read_base_version(g):
    """owl:versionInfo（单一 Ontology subject）；缺失→0.0.0；多值→歧义错。"""
    ontos = list(g.subjects(RDF.type, OWL.Ontology))
    vals = []
    for o in ontos:
        vals += [str(v) for v in g.objects(o, OWL.versionInfo)]
    if not vals:
        return "0.0.0", ontos
    if len(set(vals)) > 1:
        raise PatchError("owl:versionInfo 多值歧义: %r" % vals)
    return vals[0], ontos


def bump_version(base, level):
    parts = (base.split(".") + ["0", "0", "0"])[:3]
    try:
        major, minor, patch = (int(p) for p in parts)
    except ValueError:
        major, minor, patch = 0, 0, 0
    if level == "major":
        return "%d.0.0" % (major + 1)
    if level == "minor":
        return "%d.%d.0" % (major, minor + 1)
    return "%d.%d.%d" % (major, minor, patch + 1)


def apply_version_op(g, ontos, newver):
    for o in ontos:
        for t in list(g.triples((o, OWL.versionInfo, None))):
            g.remove(t)
        g.add((o, OWL.versionInfo, Literal(newver)))
    if not ontos:
        # 无 Ontology subject：不写 versionInfo（登记），版本仅在 report 承载
        return False
    return True


# ============================================================ ④ 序列化层

def serialize_draft(g_draft, baseline_sha, patch_id, newver):
    """确定性溯源注释头（无时间戳）+ canonical-copy-rebind turtle（跨 seed 字节稳定）。
    保真边界：rdflib 序列化丢失原文件注释——draft 是机械中间产物，权威注释不动，
    晋升时历史注释合并是编排器/人工职责（report notes 登记）。"""
    gc = to_canonical_graph(g_draft)
    g = Graph()
    for t in gc:
        g.add(t)
    for prefix, ns in g_draft.namespaces():
        g.bind(prefix, ns)
    body = g.serialize(format="turtle")
    header = (
        "# ============================================================================\n"
        "# R2 增量 patch draft（机械中间产物，非权威）\n"
        "# baseline sha256: %s\n"
        "# patch_id: %s ｜ version: %s\n"
        "# 生效通道：入口 (c) S4 审计 → G2/G3 → 人工晋升；R2 永不执行晋升。\n"
        "# 保真边界：rdflib 序列化丢失原文件注释；晋升时历史注释合并由编排器/人工承接。\n"
        "# ============================================================================\n"
        % (baseline_sha[:12], patch_id, newver)
    )
    return header + body


# ============================================================ ⑤ 校验层

def _fkey(f):
    return (f["check_id"], f.get("location"), f["message"])


def run_l1_l2(baseline_path, draft_path, strict):
    rb = Validator(baseline_path).run()
    rd = Validator(draft_path).run()
    base_err = {_fkey(f) for f in rb["findings"] if f["severity"] == "error"}
    draft_err = {_fkey(f) for f in rd["findings"] if f["severity"] == "error"}
    base_warn = {_fkey(f) for f in rb["findings"] if f["severity"] == "warning"}
    draft_warn = {_fkey(f) for f in rd["findings"] if f["severity"] == "warning"}
    new_keys = draft_err - base_err
    new_errors = [f for f in rd["findings"] if f["severity"] == "error" and _fkey(f) in new_keys]
    inherited = [f for f in rd["findings"] if f["severity"] == "error" and _fkey(f) in (draft_err & base_err)]
    resolved = [f for f in rb["findings"] if f["severity"] == "error" and _fkey(f) in (base_err - draft_err)]
    new_warnings = [f for f in rd["findings"] if f["severity"] == "warning" and _fkey(f) in (draft_warn - base_warn)]
    if strict:
        gate = rd["parse_ok"] and rd["summary"]["errors"] == 0
    else:
        gate = rd["parse_ok"] and len(new_errors) == 0
    return {
        "exit_code": rd["exit_code"], "parse_ok": rd["parse_ok"], "summary": rd["summary"],
        "baseline_summary": rb["summary"], "strict": strict, "gate_pass": gate,
        "new_errors": new_errors, "inherited_errors": inherited,
        "resolved_errors": resolved, "new_warnings": new_warnings,
    }


def run_l3(draft_path, tmpdir):
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_consistency.py")
    out = os.path.join(tmpdir, "l3.json")
    proc = subprocess.run([sys.executable, script, draft_path, "--json-output", out],
                          capture_output=True, text=True)
    payload = {}
    if os.path.exists(out):
        try:
            with open(out, encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:
            payload = {}
    return {"exit_code": proc.returncode, "consistent": payload.get("consistent"),
            "inconsistent_classes": payload.get("inconsistent_classes", []),
            "reasoner_used": payload.get("reasoner_used"), "notes": payload.get("notes", [])}


# ============================================================ ⑥ 回归守护层

def case_refs(case, header, pmap):
    """用例引用 IRI 集：case.ttl parse（baseline 前缀头）全 URIRef（词汇过滤）
    + expect 类/属性裸名经默认 ns 展开（个体名跳过——用例局部）。"""
    refs = set()
    cg = Graph()
    try:
        cg.parse(data=header + "\n" + case.get("ttl", ""), format="turtle")
        for t in cg:
            for term in t:
                if isinstance(term, URIRef) and not is_vocab(term):
                    refs.add(term)
    except Exception:
        pass
    default = pmap.get("")
    for exp in case.get("expect", []):
        kind = exp[0]
        if kind in ("in_class", "not_in_class") and len(exp) >= 3 and default:
            refs.add(URIRef(default + exp[2]))
        elif kind in ("prop_value", "no_prop_value") and len(exp) >= 4 and default:
            refs.add(URIRef(default + exp[2]))
    return refs


def select_cases(cases, aff_sem, annotation_only, unanchored, global_change, full, header, pmap):
    """受影响子集选择。返回 (selected[{id,reason}], verdict_hint)。"""
    active = [c for c in cases if not c.get("exempt")]
    if full:
        return [{"id": c["id"], "reason": "forced-full"} for c in active], None
    if annotation_only:
        return [], "skipped(annotation-only)"
    if unanchored or global_change:
        return [{"id": c["id"], "reason": "global-change"} for c in active], None
    selected = []
    for c in active:
        kinds = {e[0] for e in c.get("expect", [])}
        if kinds and kinds <= {"consistent", "inconsistent"}:
            selected.append({"id": c["id"], "reason": "global-guard"})
            continue
        refs = case_refs(c, header, pmap)
        hit = refs & aff_sem
        if hit:
            selected.append({"id": c["id"], "reason": "refs:" + ",".join(sorted(local_name(x) for x in hit))})
    if not selected:
        return [], "skipped(no-intersection)"
    return selected, None


def _canonical_cached(text, cache_dir):
    """canonicalize_base 带缓存（键=text sha256；仿 simulate_reason.canonical_with_cache）。
    默认无缓存=零副作用。canonicalize_base 返回 (nt, n_stripped) 元组。"""
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        key = sha256_text(text)
        cf = os.path.join(cache_dir, "%s.nt" % key)
        if os.path.exists(cf):
            with open(cf, encoding="utf-8") as fh:
                return fh.read()
        nt, _ = canonicalize_base(text)
        with open(cf, "w", encoding="utf-8") as fh:
            fh.write(nt)
        return nt
    nt, _ = canonicalize_base(text)
    return nt


def run_regression(selected, cases, base_text, draft_text, java, cache_dir):
    by_id = {c["id"]: c for c in cases}
    base_nt = _canonical_cached(base_text, cache_dir)
    draft_nt = _canonical_cached(draft_text, cache_dir)
    base_header = _prefix_header(base_text)
    draft_header = _prefix_header(draft_text)
    results = []
    for sel in selected:
        c = by_id[sel["id"]]
        rb = run_one(c, base_nt, java, base_prefixes=base_header)
        rd = run_one(c, draft_nt, java, base_prefixes=draft_header)
        results.append({"id": c["id"], "baseline": rb, "draft": rd})
    total = len(results)
    b_pass = sum(1 for r in results if r["baseline"].get("pass"))
    d_pass = sum(1 for r in results if r["draft"].get("pass"))
    b_err = sum(1 for r in results if r["baseline"].get("error"))
    d_err = sum(1 for r in results if r["draft"].get("error"))
    newly_failed = [r["id"] for r in results if r["baseline"].get("pass") and not r["draft"].get("pass")]
    newly_error = [r["id"] for r in results if r["draft"].get("error") and not r["baseline"].get("error")]
    inherited_fail = [r["id"] for r in results if not r["baseline"].get("pass")]
    rate_b = round(b_pass / total * 100, 1) if total else 0.0
    rate_d = round(d_pass / total * 100, 1) if total else 0.0
    gate = (not newly_failed) and (not newly_error) and (rate_d >= rate_b)
    return {
        "verdict": "pass" if gate else "fail",
        "baseline": {"total": total, "pass": b_pass, "fail": total - b_pass, "error": b_err},
        "draft": {"total": total, "pass": d_pass, "fail": total - d_pass, "error": d_err},
        "newly_failed": newly_failed, "newly_error": newly_error, "inherited_fail": inherited_fail,
        "pass_rate_before": rate_b, "pass_rate_after": rate_d,
        "per_case": [{"id": r["id"], "baseline_pass": r["baseline"].get("pass"),
                      "draft_pass": r["draft"].get("pass"), "draft_error": r["draft"].get("error")} for r in results],
    }


# ============================================================ ⑦ 报告层 + main

def build_report(**kw):
    rep = {
        "schema_version": SCHEMA_VERSION,
        "patch_id": kw["patch_id"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "baseline": kw["baseline"], "draft": kw["draft"], "source": kw["source"],
        "operations": kw["operations"], "diff": kw["diff"], "version": kw["version"],
        "validation": kw["validation"], "regression": kw["regression"],
        "zero_writeback": kw["zero_writeback"],
        "verdict": kw["verdict"], "blocked_reasons": kw["blocked_reasons"],
        "entry_c": {"status": "pending_audit", "authoritative": False,
                    "promotion": "入口(c) S4 审计→G2/G3→人工晋升；R2 永不执行晋升"},
        "notes": kw["notes"],
    }
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description="R2 增量 patch 引擎（机械 backbone，draft 非权威，零回写）")
    ap.add_argument("baseline", help="基底本体 TTL（权威，只读）")
    ap.add_argument("patch", help="编辑操作 JSON（schema 1.0，见 assets/tpl-patch-schema.md）")
    ap.add_argument("--golden", help="黄金用例 JSON（回归守护；MAJOR 硬前提）")
    ap.add_argument("--with-l3", action="store_true", help="附加 L3 推理机一致性复检")
    ap.add_argument("--output-draft", help="draft TTL 输出路径（缺省 cwd/<stem>.draft-<ver>.ttl）")
    ap.add_argument("--report", help="patch-report.json 输出路径（缺省 cwd/<stem>.draft-<ver>.patch-report.json）")
    ap.add_argument("--bump", choices=BUMPS, default="auto", help="版本 bump（缺省 auto 检测）")
    ap.add_argument("--strict", action="store_true", help="L1/L2 绝对零 error 档（缺省 delta 零新增 error）")
    ap.add_argument("--regression-full", action="store_true", help="强制全集回归（D4 提交前终检）")
    ap.add_argument("--cache-dir", help="canonical NT 缓存目录（sha 键，摊销大本体；缺省无缓存零副作用）")
    args = ap.parse_args(argv)

    notes = ["保真边界：rdflib 序列化丢失原文件注释；draft 为机械中间产物，权威注释不动，晋升时历史注释合并由编排器/人工承接。"]

    # ---- 输入契约（exit 2，不产 draft）----
    try:
        with open(args.patch, encoding="utf-8") as fh:
            patch = json.load(fh)
    except Exception as exc:
        sys.stderr.write("patch JSON 读取失败: %s\n" % exc); return 2
    errs = validate_patch(patch)
    if errs:
        sys.stderr.write("patch schema 校验失败（%d 项）:\n" % len(errs))
        for e in errs:
            sys.stderr.write("  - %s\n" % e)
        return 2
    try:
        base_text, g_base, base_sha = load_baseline(args.baseline, patch)
        pmap = parse_prefix_map(base_text)
        header = _prefix_header(base_text)
        # 输出 realpath 碰撞守卫
        inputs_real = {os.path.realpath(args.baseline), os.path.realpath(args.patch)}
        if args.golden:
            inputs_real.add(os.path.realpath(args.golden))
        base_version, ontos = read_base_version(g_base)
        # 预检 bump override 合法性已在 validate；先应用操作
        g_draft, op_records = apply_operations(g_base, patch["operations"], pmap, header)
    except PatchError as exc:
        sys.stderr.write("输入/应用错（不产 draft）: %s\n" % exc); return 2

    # ---- diff（user ops）+ bump 检测 ----
    rem_u, add_u = set_diff(g_base, g_draft)
    aff_sem, aff_ann, unanchored, annotation_only = semantic_affected(rem_u, add_u, g_base, g_draft)
    global_change = touches_global(rem_u, add_u, g_base, g_draft)
    rule_touched = detect_rule_touched(rem_u, add_u, g_base, g_draft)
    union = Graph()
    for t in g_base:
        union.add(t)
    for t in g_draft:
        union.add(t)
    rule_adjacent = bool(aff_sem & rule_referenced_iris(union)) and not rule_touched
    if rule_touched:
        bump_auto = "major"
    elif annotation_only or not rem_u and not add_u:
        bump_auto = "patch"
    else:
        bump_auto = "minor"
    bump_req = patch.get("bump", "auto")
    bump_applied = bump_auto if bump_req == "auto" else bump_req
    version_warnings = []
    if bump_req != "auto" and BUMP_RANK[bump_applied] < BUMP_RANK[bump_auto]:
        version_warnings.append("显式 bump %s 低于 auto 检测 %s（auto 值始终登记）" % (bump_applied, bump_auto))
    newver = bump_version(base_version, bump_applied)
    wrote_ver = apply_version_op(g_draft, ontos, newver)
    if not wrote_ver:
        notes.append("baseline 无 owl:Ontology subject——versionInfo 未写回 draft，版本仅在 report 承载。")
    op_records.append({"index": len(op_records), "op": "set_version", "status": "applied",
                       "source": "engine", "detail": "%s → %s（bump=%s）" % (base_version, newver, bump_applied)})

    # ---- 序列化 draft + 输出路径 ----
    draft_text = serialize_draft(g_draft, base_sha, patch.get("patch_id", "P-adhoc"), newver)
    stem = os.path.splitext(os.path.basename(args.baseline))[0]
    draft_path = args.output_draft or os.path.join(os.getcwd(), "%s.draft-%s.ttl" % (stem, newver))
    report_path = args.report or os.path.join(os.getcwd(), "%s.draft-%s.patch-report.json" % (stem, newver))
    for outp in (draft_path, report_path):
        if os.path.realpath(outp) in inputs_real:
            sys.stderr.write("输出路径碰撞输入文件（零回写守卫）: %s\n" % outp); return 2
    with open(draft_path, "w", encoding="utf-8") as fh:
        fh.write(draft_text)
    draft_sha = sha256_text(draft_text)

    # ---- 校验 ----
    l1l2 = run_l1_l2(args.baseline, draft_path, args.strict)
    blocked_reasons = []
    if not l1l2["gate_pass"]:
        blocked_reasons.append("L1/L2 闸门未过（new_errors=%d，strict=%s）" % (len(l1l2["new_errors"]), args.strict))
    l3 = None
    if args.with_l3:
        with tempfile.TemporaryDirectory(prefix="r2-l3-") as td:
            l3 = run_l3(draft_path, td)
        if l3["exit_code"] == 1:
            blocked_reasons.append("L3 检出不一致（inconsistent_classes=%s）" % l3["inconsistent_classes"])
        elif l3["exit_code"] == 2:
            notes.append("L3 环境不可用（exit 2）——降级登记，凭 L1/L2 + 回归把关。")

    # ---- 回归守护 ----
    golden_data, golden_errs = None, []
    if args.golden:
        if not os.path.isfile(args.golden):
            sys.stderr.write("golden 文件不存在: %s\n" % args.golden); return 2
        with open(args.golden, encoding="utf-8") as fh:
            golden_data = json.load(fh)
        golden_errs = validate_schema(golden_data)
        if golden_errs:
            sys.stderr.write("golden schema 校验失败（%d 项）:\n" % len(golden_errs))
            for e in golden_errs:
                sys.stderr.write("  - %s\n" % e)
            return 2
    java = find_java()
    regression = {"verdict": "not-requested", "selected": []}
    is_major = bump_applied == "major"
    if not l1l2["gate_pass"]:
        # L1/L2 闸门已失败 → 回归短路（结构非法 draft 的回归无决策价值，省 JVM 成本）
        regression["verdict"] = "skipped(l1l2-blocked)"
        notes.append("L1/L2 闸门已失败——回归短路（blocked draft 供检视，修复后重跑）。")
    elif args.golden and golden_data:
        cases = golden_data["cases"]
        selected, hint = select_cases(cases, aff_sem, annotation_only, unanchored,
                                      global_change, args.regression_full, header, pmap)
        regression["selected"] = selected
        if hint:
            regression["verdict"] = hint
            if hint == "skipped(no-intersection)":
                notes.append("语义 patch 但无用例引用任何受影响项——子集空，凭 L1/L2 放行（warning 登记）。")
        elif not selected:
            regression["verdict"] = "skipped(no-intersection)"
        elif not java:
            if is_major:
                regression["verdict"] = "blocked"
                blocked_reasons.append("MAJOR 规则变更但无 Java——回归不可跑，转入口 (c) 全量审计。")
            else:
                regression["verdict"] = "downgraded"
                notes.append("无 Java——回归降级登记，凭 L1/L2 放行（MINOR/PATCH，套件 L3 降级同口径）。")
        else:
            reg = run_regression(selected, cases, base_text, draft_text, java, args.cache_dir)
            regression.update(reg)
            if reg["verdict"] == "fail":
                blocked_reasons.append("回归守护检出（newly_failed=%s newly_error=%s 通过率 %s→%s）"
                                       % (reg["newly_failed"], reg["newly_error"],
                                          reg["pass_rate_before"], reg["pass_rate_after"]))
    elif is_major:
        regression["verdict"] = "blocked"
        blocked_reasons.append("MAJOR 规则变更无 --golden——回归守护硬前提缺失，转入口 (c) 全量审计。")
    elif args.regression_full:
        notes.append("--regression-full 但无 --golden——无从跑全集，登记。")

    # ---- 零回写断言 ----
    before = {"baseline": base_sha, "patch": sha256_file(args.patch)}
    if args.golden:
        before["golden"] = sha256_file(args.golden)
    after = {"baseline": sha256_file(args.baseline), "patch": sha256_file(args.patch)}
    if args.golden:
        after["golden"] = sha256_file(args.golden)
    zw_ok = before == after
    if not zw_ok:
        blocked_reasons.append("零回写断言失败——输入文件被改动（运行期完整性）。")
    zero_writeback = {"before": before, "after": after, "assert_ok": zw_ok}

    # ---- 报告 + verdict ----
    rem_f, add_f = set_diff(g_base, g_draft)
    diff_block = render_diff(rem_f, add_f)
    diff_block["named_summary"] = [
        {"op": r["op"], "status": r["status"], "source": r["source"], "detail": r["detail"]}
        for r in op_records]
    version_block = {"base": base_version, "new": newver, "bump_auto": bump_auto,
                     "bump_applied": bump_applied, "rule_touched": rule_touched,
                     "rule_adjacent": rule_adjacent, "warnings": version_warnings,
                     "reason": ("规则编码变更" if rule_touched else
                                "annotation-only" if annotation_only else "结构变更")}
    if rule_adjacent:
        notes.append("rule_adjacent：diff 触及规则引用项但规则编码未动——MINOR + 建议 L3（--with-l3）。")
    verdict = "released" if not blocked_reasons else "blocked"
    report = build_report(
        patch_id=patch.get("patch_id", "P-adhoc"),
        baseline={"path": args.baseline, "sha256": base_sha, "version": base_version},
        draft={"path": draft_path, "sha256": draft_sha, "version": newver},
        source=patch.get("source", {}), operations=op_records, diff=diff_block,
        version=version_block, validation={"l1_l2": l1l2, "l3": l3},
        regression=regression, zero_writeback=zero_writeback,
        verdict=verdict, blocked_reasons=blocked_reasons, notes=notes)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # ---- 人类可读摘要 ----
    print("=" * 60)
    print("R2 增量 patch: %s → %s（bump %s/%s）" % (base_version, newver, bump_applied, bump_auto))
    print("操作 %d（user %d / engine 1）｜diff +%d/-%d" % (
        len(op_records), len(op_records) - 1, diff_block["added_n"], diff_block["removed_n"]))
    print("L1/L2: %s（new_errors=%d inherited=%d）｜L3: %s" % (
        "PASS" if l1l2["gate_pass"] else "FAIL", len(l1l2["new_errors"]),
        len(l1l2["inherited_errors"]), (l3["exit_code"] if l3 else "未请求")))
    print("回归: %s（选中 %d）｜零回写: %s" % (
        regression["verdict"], len(regression.get("selected", [])), "✓" if zw_ok else "✗"))
    print("verdict: %s" % verdict.upper())
    for r in blocked_reasons:
        print("  blocked: %s" % r)
    print("draft: %s\nreport: %s" % (draft_path, report_path))
    print("生效通道: 入口 (c) S4 审计 → G2/G3 → 人工晋升（R2 永不执行晋升）")
    print("=" * 60)
    return 0 if verdict == "released" else 1


if __name__ == "__main__":
    sys.exit(main())