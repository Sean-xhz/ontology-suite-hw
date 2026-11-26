#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_common.py —— ontology-model 脚本内共享工具（F33 共享化，消除孪生分叉）。

model 内叶子工具模块（不 import 其他 model 脚本，无循环）；跨 skill 重实现保持不动
（simulate/review 各有本地实现，是「脚本可独立」护栏，不在此共享）。
收敛的工具：file_sha256 / base_namespace / rdf_list_items / local_name。
local_name 取健壮版（None→"?"、非 URIRef→str，原 report_topology 版）。
"""
import hashlib
import re
import sys

from rdflib import BNode, RDF, URIRef


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def base_namespace(g, path):
    """@prefix : 回推 base（TTL-direct 版，compile_instance_ttl 同算法）。"""
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


def local_name(iri):
    """取 IRI 局部名（# 或最后一个 / 之后）；None→"?"，非 URIRef 原样转字符串。"""
    if iri is None:
        return "?"
    if not isinstance(iri, URIRef):
        return str(iri)
    s = str(iri)
    if "#" in s:
        return s.rsplit("#", 1)[-1]
    return s.rsplit("/", 1)[-1]
