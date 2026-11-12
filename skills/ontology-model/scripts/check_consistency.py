#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L3 reasoner 一致性检查（owlready2 + Pellet，HermiT 兜底）。

验证层定位：W3C 合规四层验证的 L3——基于 DL reasoner 检测：
  - 类不相交/隐性逻辑矛盾（L2 静态脚本无法覆盖的推理级冲突）
  - SWRL 规则执行后的语义冲突（规则 A 与规则 B 推导出矛盾断言）
L1/L2 由 validate_ontology.py 负责；本脚本失败不阻塞交付（登记 manifest 降级 L2）。

用法:
  python3 check_consistency.py <ontology.ttl> [--json-output path] [--reasoner pellet|hermit]

退出码:
  0 = reasoner 运行成功且本体一致
  1 = reasoner 运行成功但检出不一致（inconsistent classes 非空）
  2 = reasoner 无法运行（Java/owlready2 缺失、解析失败等环境或语法问题）
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime


def find_java():
    """定位 Java 可执行文件：环境变量 > ~/Library 常见路径（版本降序）> 系统 PATH。

    版本降序是硬需求：owlready2 0.51 内置 Pellet 的 Jena 依赖要求 Java ≥25
    （class file 69.0），旧版 JRE 会以 UnsupportedClassVersionError 失败。
    """
    import re

    def _major(path):
        m = re.search(r"[/_-](\d+)", os.path.basename(
            path.split(os.sep + "Contents")[0]))
        return int(m.group(1)) if m else 0

    candidates = [os.environ.get("OWL_JAVA_EXE")]
    home = os.path.expanduser("~")
    candidates += sorted(
        glob.glob(os.path.join(
            home, "Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java")),
        key=_major, reverse=True)
    candidates += sorted(glob.glob(
        os.path.join(home, ".sdkman/candidates/java/*/bin/java")),
        key=_major, reverse=True)
    candidates += ["/usr/bin/java", "/usr/local/bin/java"]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def strip_swrl(g):
    """从 rdflib Graph 剥离 swrl:Imp 规则及其 bnode 闭包，返回删除的三元组数。"""
    import rdflib
    SWRL = "http://www.w3.org/2003/11/swrl#"
    seeds = set()
    for s, p, o in g:
        if str(p).startswith(SWRL):
            if isinstance(s, rdflib.BNode):
                seeds.add(s)
            if isinstance(o, rdflib.BNode):
                seeds.add(o)
        if str(o) == SWRL + "Imp" and isinstance(s, rdflib.BNode):
            seeds.add(s)
    changed = True
    while changed:
        changed = False
        for b in list(seeds):
            for o in g.objects(b, None):
                if isinstance(o, rdflib.BNode) and o not in seeds:
                    seeds.add(o)
                    changed = True
    removed = 0
    for s, p, o in list(g):
        if isinstance(s, rdflib.BNode) and s in seeds:
            g.remove((s, p, o))
            removed += 1
    return removed


def emit(payload, args, exit_code):
    payload["exit_code"] = exit_code
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def main():
    ap = argparse.ArgumentParser(description="L3 reasoner 一致性检查")
    ap.add_argument("ttl", help="本体 Turtle 文件路径")
    ap.add_argument("--json-output", help="JSON 报告输出路径")
    ap.add_argument("--reasoner", choices=["pellet", "hermit"], default="pellet",
                    help="pellet=默认（支持 SWRL）；hermit=兜底（纯 DL，不执行 SWRL）")
    args = ap.parse_args()

    result = {
        "file": args.ttl,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "layer": "L3",
        "reasoner_requested": args.reasoner,
        "reasoner_used": None,
        "java_exe": None,
        "consistent": None,
        "inconsistent_classes": [],
        "swrl_rules": None,
        # SWRL 验证档位：pellet=完整验证 / hermit-partial=ClassAtom 型规则被消费 /
        # false=SWRL 已剥离未验证（DL 层 only）/ null=reasoner 未跑成
        "swrl_verified": None,
        "notes": [],
    }

    if not os.path.isfile(args.ttl):
        result["notes"].append(f"文件不存在: {args.ttl}")
        emit(result, args, 2)

    try:
        import owlready2
    except ImportError:
        result["notes"].append("owlready2 未安装（pip3 install --user owlready2）；降级 L2")
        emit(result, args, 2)

    java = find_java()
    if not java:
        result["notes"].append("未找到 Java 可执行文件；L3 不可用，降级 L2（登记 manifest）")
        emit(result, args, 2)
    owlready2.JAVA_EXE = java
    result["java_exe"] = java

    world = owlready2.World()
    # owlready2 原生解析器只认 RDF/XML、N-Triples、OWL/XML——不支持 Turtle
    # （_guess_format 对非 "<" 开头内容一律误判 ntriples）。统一先用 rdflib
    # 解析源文件并转 RDF/XML 临时文件再喂 owlready2（SWRL 三元组随转随存）。
    import tempfile
    tmp_path = None
    try:
        import rdflib
        g = rdflib.Graph()
        g.parse(args.ttl)  # rdflib 按后缀自动猜格式（ttl/xml/nt 均可）
        # L3 不联网解析 owl:imports（MVP 纪律；IRI 格式由 L2 检查）。
        # 不剥离会导致 owlready2 尝试下载远程 imports 而失败。
        _imports = rdflib.URIRef("http://www.w3.org/2002/07/owl#imports")
        n_imports = len(list(g.triples((None, _imports, None))))
        if n_imports:
            g.remove((None, _imports, None))
            result["notes"].append(
                f"已剥离 {n_imports} 条 owl:imports 声明（L3 不联网解析；格式检查见 L2）")
        fd, tmp_path = tempfile.mkstemp(suffix=".rdf")
        import atexit
        atexit.register(lambda p=tmp_path: os.path.exists(p) and os.unlink(p))
        with os.fdopen(fd, "wb") as fh:
            g.serialize(destination=fh, format="xml")
        onto = world.get_ontology(tmp_path).load()
    except Exception as e:
        result["notes"].append(f"本体加载失败: {e.__class__.__name__}: {e}")
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        emit(result, args, 2)

    result["swrl_rules"] = len(list(onto.rules()))

    # ---- reasoner 三级降级链 ----
    # 本机实测的引擎限制（owlready2 0.51 + Temurin 25）：
    #   ① Pellet 内置 Jena 对 SWRL Variable bnode 渲染报 "is not a URI node"
    #      → Pellet 仅对无 SWRL 本体可靠
    #   ② HermiT（老版 OWLAPI）不支持 swrl:ObjectPropertyAtom（翻译失败），
    #      但可消费 ClassAtom 形态规则并检出「规则→disjoint 类冲突」型不一致
    #   ③ HermiT 遇部分 xsd datatype 需 ignore_unsupported_datatypes=True
    def _run(o, rname):
        # owlready2 0.51 签名：sync_reasoner_*(x=None, ...)，x 位置传 World
        if rname == "pellet":
            with o:
                owlready2.sync_reasoner_pellet(
                    o.world, infer_data_property_values=True)
        else:
            with o:
                owlready2.sync_reasoner_hermit(
                    o.world, infer_property_values=True,
                    ignore_unsupported_datatypes=True)

    used = None
    inconsistent_detected = False
    order = ([args.reasoner, "hermit"] if args.reasoner == "pellet"
             else [args.reasoner])
    for rname in order:
        try:
            _run(onto, rname)
            used = rname
            result["swrl_verified"] = "pellet" if rname == "pellet" else "hermit-partial"
            break
        except owlready2.base.OwlReadyInconsistentOntologyError as e:
            # 三用途异常：空消息 = 检出不一致（正向结果）；
            # "Java error message is:...Ontology is inconsistent..." = Pellet 检出不一致
            #   （2026-10-26 具名 SWRL 变量修复后实测：Pellet 以 Java error 形态报不一致，
            #    须判阳性检出而非降级）；
            # 其他 "Java error message is:..." = JVM 运行失败（降级下一档）
            msg = str(e)
            if msg.startswith("Java error"):
                if "Ontology is inconsistent" in msg:
                    used = rname
                    inconsistent_detected = True
                    result["swrl_verified"] = "pellet" if rname == "pellet" else "hermit-partial"
                    result["notes"].append(
                        f"reasoner {rname} 判定本体不一致（全局矛盾）——Pellet 消息形态")
                    break
                result["notes"].append(f"reasoner {rname} 运行失败: {msg[:400]}")
                continue
            used = rname
            inconsistent_detected = True
            result["swrl_verified"] = "pellet" if rname == "pellet" else "hermit-partial"
            break
        except Exception as e:
            result["notes"].append(
                f"reasoner {rname} 运行失败: {e.__class__.__name__}: {str(e)[:400]}")

    if used is None and result["swrl_rules"]:
        # 降级档：剥离 SWRL 后重试 HermiT——DL 层一致性仍验证，
        # SWRL 语义冲突未验证（转交 S4 双模型审计，登记 manifest）
        g2 = rdflib.Graph()
        g2.parse(args.ttl)
        g2.remove((None, rdflib.URIRef("http://www.w3.org/2002/07/owl#imports"), None))
        n_stripped = strip_swrl(g2)
        tmp2 = None
        try:
            fd2, tmp2 = tempfile.mkstemp(suffix=".rdf")
            with os.fdopen(fd2, "wb") as fh2:
                g2.serialize(destination=fh2, format="xml")
            world2 = owlready2.World()
            onto2 = world2.get_ontology(tmp2).load()
            try:
                _run(onto2, "hermit")
                used = "hermit(swrl-stripped)"
                result["swrl_verified"] = False
                result["notes"].append(
                    f"降级：已剥离 SWRL 规则（{n_stripped} 三元组）仅做 DL 一致性验证；"
                    "SWRL 语义冲突未验证——由 S4 双模型审计承接并登记 manifest")
            except owlready2.base.OwlReadyInconsistentOntologyError as e:
                if str(e).startswith("Java error"):
                    raise
                used = "hermit(swrl-stripped)"
                inconsistent_detected = True
                result["swrl_verified"] = False
                onto = onto2  # 供 inconsistent_classes 查询
        except Exception as e:
            result["notes"].append(
                f"SWRL 剥离降级档亦失败: {e.__class__.__name__}: {str(e)[:300]}")
        finally:
            if tmp2 and os.path.exists(tmp2):
                os.unlink(tmp2)

    if used is None:
        result["notes"].append("全部 reasoner 档位不可用；降级 L2（登记 manifest）")
        emit(result, args, 2)
    result["reasoner_used"] = used

    if inconsistent_detected:
        result["consistent"] = False
        try:
            result["inconsistent_classes"] = [
                str(c) for c in onto.inconsistent_classes()]
        except Exception:
            pass
        result["notes"].append(
            "reasoner 判定本体不一致（全局矛盾）——disjoint 冲突或规则推导出"
            "矛盾断言；inconsistent_classes 为空时以本条全局判定为准")
    else:
        inconsistent = [str(c) for c in onto.inconsistent_classes()]
        result["inconsistent_classes"] = inconsistent
        result["consistent"] = (len(inconsistent) == 0)
        if not result["consistent"]:
            result["notes"].append(
                f"检出 {len(inconsistent)} 个不一致类——本体存在逻辑矛盾")
    emit(result, args, 0 if result["consistent"] else 1)


if __name__ == "__main__":
    main()
