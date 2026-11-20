#!/usr/bin/env python3
"""ontology-ingest I3 机械组装：每源件单一清洁合并 md（assemble_pack）。

定位（机械/LLM 分界，铁律 4）：I2 LLM 逐单元整页转录（语义层）回填 manifest.sections[].text；
本脚本是 I3 **机械组装层**——从 canonical manifest 按 sections 顺序确定性组装每源件单一
`<doc_id>.md`（落 pack 目录，与 attachments/ 同级），**机械保证按序/不丢弃/图嵌守恒**，
不依赖 LLM 合并纪律（LLM 合并有注意力遗漏/上下文截断/顺手改写风险，且全文进上下文不可持续）。

合并形态（一份资料一份解析文档，tpl-extract-pack §三）：
- 唯一 H1 = doc_id（文档标题）；各单元标题层级压实为 H2 起连续（保内部相对结构，去层级跳空，fence 感知）。
- 单元间 `---` 分页节（清洁，非机器锚）；空单元（text 空）诚实占位「## md_heading + （空单元…）」。
- 图嵌规范化：转录中间态 `![[attachments/x]]` → 最终 `![[x]]` 裸文件名（Obsidian 全局解析约定）。
- 机器元数据全在 manifest，md 正文清洁无机器锚。

自校验（机械门禁，exit 1 若任一失败）：唯一 H1 / 无机器锚 / 图嵌计数守恒 / 图嵌全裸文件名 /
逐单元内容完备且按 manifest 序拼接（归一化子串单调游标）/ manifest source.sha 零回写。

用法：
    python3 assemble_pack.py PACK_DIR...          # 一个或多个 pack 目录（各含 manifest.json）
    python3 assemble_pack.py --pack-root DIR      # glob DIR/*/manifest.json 批量
exit 0=组装+自校验全过 / 1=自校验失败 / 2=输入错（缺 manifest/有 prepared 残留未转录/缺 text）。
确定性：同 manifest → 同 md（零时间戳）；合并 md 是从转录层派生的可再生非 canonical 产物，幂等覆盖。
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata

HEAD_RE = re.compile(r"^(#{1,6}) (.*)$")
EMBED_RE = re.compile(r"!\[\[attachments/([^\]]+)\]\]")
ANCHOR_RE = re.compile(
    r"\[s\d{3}\]|<!--\s*(locator|extraction|sensitive)|\btext_sha256\b|"
    r"\bextraction\s*[:=]\s*(prepared|transcribed)|\bsensitive_flags\b"
)


def compact_headings(md):
    """单元内标题层级压实：唯一层级集合 → 从 H2 起连续映射（保内部相对结构）；代码 fence 内不动。"""
    lines = md.splitlines()
    levels = sorted({len(HEAD_RE.match(l).group(1)) for l in lines if HEAD_RE.match(l)})
    mapping = {old: min(2 + i, 6) for i, old in enumerate(levels)}
    out = []
    in_fence = False
    for l in lines:
        if l.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(l)
            continue
        m = HEAD_RE.match(l)
        if m and not in_fence:
            out.append("#" * mapping[len(m.group(1))] + " " + m.group(2))
        else:
            out.append(l)
    return "\n".join(out)


def bare_embeds(md):
    """图嵌中间态 ![[attachments/x]] → 最终裸文件名 ![[x]]（Obsidian 全局解析）。"""
    return EMBED_RE.sub(r"![[\1]]", md)


def norm(md):
    """完备性归一化：去标题 # 标记 / 图嵌 attachments 前缀 / --- 分隔 / 折叠空白（判内容在场非语义）。"""
    md = EMBED_RE.sub(r"![[\1]]", md)
    md = re.sub(r"^#{1,6} ", "", md, flags=re.M)
    md = re.sub(r"^---\s*$", "", md, flags=re.M)
    return re.sub(r"\s+", "", md)


def assemble_one(pack_dir):
    """组装单个 pack → (out_path, checks, embed_count)。输入错抛 ValueError（exit 2）。"""
    mf = os.path.join(pack_dir, "manifest.json")
    if not os.path.exists(mf):
        raise ValueError("缺 manifest.json：" + pack_dir)
    m = json.load(open(mf, encoding="utf-8"))
    doc = m["doc_id"]
    secs = m["sections"]
    if not secs:
        raise ValueError("manifest.sections 为空：" + doc)
    prepared = [s["section_id"] for s in secs if s.get("extraction") != "transcribed"]
    if prepared:
        raise ValueError("有未转录单元（extraction!=transcribed），组装过早：" + doc + " " + ",".join(prepared))
    src_sha = m["source"]["sha256"]

    parts = ["# " + doc]
    embed_before = 0
    embed_after = 0
    for s in secs:
        heading = s.get("md_heading") or s.get("heading") or s["section_id"]
        text = s.get("text") or ""
        if not text.strip():
            parts.append("## " + heading + "\n\n（空单元：无视觉内容，未转录）")
            continue
        embed_before += len(EMBED_RE.findall(text))
        body = bare_embeds(compact_headings(text)).rstrip()
        first_line = body.splitlines()[0] if body.splitlines() else ""
        if not HEAD_RE.match(first_line):
            body = "## " + heading + "\n\n" + body
        embed_after += len(re.findall(r"!\[\[", body))
        parts.append(body)
    merged = "\n\n---\n\n".join(parts) + "\n"
    out_p = os.path.join(pack_dir, doc + ".md")
    with open(out_p, "w", encoding="utf-8") as f:
        f.write(merged)

    checks = []

    def chk(name, cond):
        checks.append((name, bool(cond)))

    chk("唯一 H1 文档标题", sum(1 for l in merged.splitlines() if re.match(r"^# ", l)) == 1)
    chk("清洁 md 无机器锚", not ANCHOR_RE.search(merged))
    chk("图嵌计数守恒（裸文件名转换不丢图）", embed_before == embed_after)
    chk("图嵌全裸文件名（无 ![[attachments/ 残留）", "![[attachments/" not in merged)
    merged_norm = norm(merged)
    cursor = 0
    missing = []
    for s in secs:
        text = s.get("text") or ""
        if not text.strip():
            continue
        un = norm(text)
        if not un:
            continue
        idx = merged_norm.find(un, cursor)
        if idx < 0:
            missing.append(s["section_id"])
        else:
            cursor = idx + len(un)
    chk("逐单元内容完备且按 manifest 序拼接", not missing)
    m2 = json.load(open(mf, encoding="utf-8"))
    chk("manifest source.sha 零回写", m2["source"]["sha256"] == src_sha)
    return out_p, checks, embed_after, missing


def main():
    ap = argparse.ArgumentParser(description="ontology-ingest I3 机械组装：每源件单一清洁合并 md（保证按序/不丢弃）")
    ap.add_argument("pack_dirs", nargs="*", help="pack 目录（各含 manifest.json）")
    ap.add_argument("--pack-root", help="批量：glob DIR/*/manifest.json")
    args = ap.parse_args()

    packs = list(args.pack_dirs)
    if args.pack_root:
        packs += [os.path.dirname(p) for p in sorted(glob.glob(os.path.join(args.pack_root, "*", "manifest.json")))]
    packs = sorted(set(packs))
    if not packs:
        print("输入错：未指定 pack 目录（PACK_DIR... 或 --pack-root DIR）", file=sys.stderr)
        return 2

    all_ok = True
    total_embed = 0
    for pd in packs:
        try:
            out_p, checks, embed, missing = assemble_one(pd)
        except ValueError as e:
            print("[输入错] " + str(e), file=sys.stderr)
            return 2
        ok = all(c for _, c in checks)
        all_ok = all_ok and ok
        total_embed += embed
        fails = [n for n, c in checks if not c]
        print("[" + ("OK" if ok else "FAIL") + "] " + os.path.basename(out_p) + " | 图嵌 " + str(embed) +
              ((" | 缺失单元 " + ",".join(missing)) if missing else "") +
              ((" | " + "; ".join(fails)) if fails else ""))
    print("机械组装：" + ("ALL_OK" if all_ok else "FAIL") + "｜pack " + str(len(packs)) + "｜图嵌守恒合计 " + str(total_embed))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
