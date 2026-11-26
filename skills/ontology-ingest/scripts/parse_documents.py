#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parse_documents.py —— ontology-ingest 保真进料机械层（渲染 + 完整性 inventory + 原生 substrate）。

定位
------------------------------------
**LLM 整页布局感知转录 primary（每个视觉单元必过）+ 机械渲染/完整性交叉校验护栏**。
本脚本是机械层，产「准备态原料包」（rendered images + inventory + substrate + canonical
manifest schema 2.1 + 清洁 provisional MD），交 ontology-vision-extractor agent（I2
page-transcribe 模式）做布局保真转录，主会话回填 + 完整性交叉校验。
section 含四类 I2 回填 affordance（unit_type/verification_status/personal_info_regions/
md_heading，准备态 null/[]，机械不裁定），接口权威见
ontology-model/references/s1-handoff-contract.md。机械层无条件保图（fail-safe，分类不承重）。

机械层三职责（不产最终正文）
------------------------------
1. 渲染：PDF 每页→PNG（pypdfium2，BSD/Apache，避 fitz AGPL）；图片直供；office（pptx/docx/xlsx）
   若 LibreOffice 可用→PDF→页图（可选增强，跨平台全视觉保真），否则 substrate-only。
2. inventory（完整性 ground truth，交叉校验防 LLM 漏字）：PDF 文本层 / XLSX 单元格 /
   DOCX 段落+表格 / PPTX shape 文本+备注。
3. substrate（原生结构化精确文本，直抽比 OCR 准）：DOCX 结构化 md（Heading/列表/
   行内加粗斜体/表格合并去重）/ XLSX 单元格网格（合并保留/多行/公式双读）/ PPTX 位置 substrate
   （shape 边界框坐标+文本+类型+分组+图片+表格，按视觉位置排序，供 LLM 布局重建）。

设计取舍（契约详见 assets/tpl-extract-pack.md，边界详见 references/parsing-limits.md）
------------------------------------------------------------------------------------
- 机械/LLM 分界：本脚本不调 LLM，产 canonical 准备态包（extraction=prepared）；
  I2 转录回填后包显式非 canonical（transcribe_meta 带时间戳，只在该层）。
- 不变量：任何单元都不被静默路由 mechanical-only 跳过 LLM——每单元都有 render 或 substrate
  交 I2 转录。
- fitz/PyMuPDF 零代码路径（限制⑨）：AGPL，不 import；PDF 渲染用 pypdfium2。
- 清洁 MD：机器元数据（locator/sha/hint/extraction）全入 manifest，MD 正文清洁 markdown
  （无机器锚污染下游 S1）。
- term_candidates 结构种子（限制⑫）/ semantic_hint 9+1 词表（tpl §四）：保留。

纪律（不可绕过）
----------------
- 零时间戳：canonical 包零 now()/mtime/随机 id；解析时刻由主会话记 run-manifest。
- 零回写：源文档 sha256 前后断言；输出 realpath 碰撞守卫；再解析守卫护转录回填层。
- 照录不脱敏：阈值/数值照录不模糊化（脱敏在 model S1→S2）；解析层只做敏感登记位。
- 确定性：canonical json（sort_keys/ensure_ascii=False/indent=1）+尾换行；MD LF；全排序；
  pack_id 内容哈希。PDF→PNG 渲染双跑字节等（pypdfium2 实证）；office substrate 确定性。
- 懒 import：格式 handler 内导入解析库（顶层只标准库）——缺库时 --help/契约错仍工作。
- py3.9 兼容：禁 match / X|Y 类型联合。

退出码：0=成功（gap 登记不阻塞）/ 1=语义阻断（零回写失败）/ 2=输入错（缺文件/不支持格式/
        坏文件/输出碰撞/再解析守卫/缺库/AES/密码错）。

用法：
  python3 parse_documents.py INPUTS... [--output-dir DIR] [--doc-id ID]
      [--authority 正式制度|专家口述|二手转述] [--sensitivity 真实业务|虚构通用]
      [--password PW] [--render-scale 2.0] [--force]
"""
import argparse
import datetime
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PACK_SCHEMA_VERSION = "2.1"
SCRIPT_VERSION = "2.1"
DEFAULT_RENDER_SCALE = 2.0

# 扩展名 → source_type 路由（图片以 Pillow 可读为准）
EXT_TYPE = {
    ".pdf": "pdf", ".docx": "word", ".xlsx": "excel", ".xlsm": "excel",
    ".pptx": "ppt", ".png": "image", ".jpg": "image", ".jpeg": "image",
    ".webp": "image", ".bmp": "image", ".gif": "image",
}

# semantic_hint 9+1 词表（tpl §四，对齐 model structured-input-mapping §二第1步）
HINT_ORDER = ["定义", "关联", "判断", "流程", "权限", "术语", "例外", "清单参数", "数值参数", "需识图"]
HINT_KEYWORDS = {
    "定义": ["是指", "定义为", "包括", "分为", "属性", "标识", "编号", "类型", "定义"],
    "关联": ["关联", "属于", "包含", "对应", "基数", "一对多", "上级", "下级", "关系"],
    "判断": ["若", "如果", "则", "须", "不得", "禁止", "阈值", "不低于", "不超过", "条件", "应当"],
    "流程": ["步骤", "流程", "操作", "通道", "环节", "顺序"],
    "权限": ["自主", "确认", "授权", "审批", "权限"],
    "术语": ["又称", "俗称", "同义", "口语", "问答", "简称", "QA"],
    "例外": ["除外", "特殊", "例外", "不适用", "边界"],
    "数值参数": ["费率", "额度", "分值", "利率", "金额", "比例", "价格"],
}
SENSITIVE_BIZ = ["费率", "利率", "金额", "返佣", "价格", "额度", "分值"]
PHONE_RE = re.compile(r"1[3-9]\d{9}")
IDCARD_RE = re.compile(r"\d{17}[\dXx]")
EMU_PER_INCH = 914400


# ============================================================ 基础设施

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def bytes_sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sanitize_doc_id(stem):
    s = re.sub(r"\s+", "_", stem.strip())
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = s.strip(".")  # F18：防纯 .. / 前导点路径穿越
    return s or "doc"


def iso_date(dt):
    if isinstance(dt, datetime.datetime):
        return dt.date().isoformat()
    if isinstance(dt, datetime.date):
        return dt.isoformat()
    return None


def cell_str(v):
    if v is None:
        return ""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return iso_date(v)
    return str(v)


def md_escape(s):
    return str(s).replace("|", "\\|").replace("\n", "<br>").strip()


def md_table(rows):
    rows = [[md_escape(c) for c in r] for r in rows if r is not None]
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |",
           "| " + " | ".join(["---"] * ncol) + " |"]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def classify_hint(text, is_table, table_rows):
    hints = []
    for h in HINT_ORDER:
        if h == "需识图":
            continue
        if h == "清单参数":
            if is_table and table_rows >= 6:
                hints.append(h)
            continue
        if any(k in text for k in HINT_KEYWORDS.get(h, [])):
            hints.append(h)
    return hints


def sensitive_flags(text):
    flags = []
    if any(k in text for k in SENSITIVE_BIZ):
        flags.append("商务参数")
    if PHONE_RE.search(text) or IDCARD_RE.search(text):
        flags.append("个人信息")
    return flags


def locator_str(loc):
    k = loc.get("kind")
    if k == "page":
        return "p.%s" % loc.get("page")
    if k == "sheet":
        return "sheet:%s" % loc.get("sheet")
    if k == "slide":
        return "slide:%s" % loc.get("slide")
    if k == "image":
        return "image"
    return "para"


def emu_in(v):
    try:
        return round(float(v) / EMU_PER_INCH, 2)
    except Exception:
        return None


# ============================================================ 渲染层（pypdfium2 + 可选 LibreOffice）

def render_pdf_to_images(pdf_path, doc_id, prefix, scale):
    """PDF 每页→PNG bytes（pypdfium2，确定性）。返回 [{name, data, page}]。"""
    pdfium = importlib.import_module("pypdfium2")
    doc = pdfium.PdfDocument(pdf_path)
    out = []
    try:
        for i in range(len(doc)):
            bmp = doc[i].render(scale=scale)
            pil = bmp.to_pil()
            import io
            buf = io.BytesIO()
            pil.save(buf, "PNG")
            out.append({"name": "%s_%s%03d.png" % (doc_id, prefix, i + 1),
                        "data": buf.getvalue(), "page": i + 1})
    finally:
        doc.close()
    return out


# office 全视觉渲染开关（--no-office-render 置 False 强制 substrate-only canonical 档；
# LibreOffice 渲染层非 canonical〔limits ⑪〕，此开关供测试环境无关化与用户纯 pip canonical 控制）
OFFICE_RENDER_ENABLED = True


def find_libreoffice():
    """探测 LibreOffice soffice（跨平台 office→PDF 渲染器，可选）。无→None。"""
    for cand in ("soffice", "libreoffice"):
        p = shutil.which(cand)
        if p:
            return p
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    if os.path.isfile(mac):
        return mac
    return None


def office_to_pdf(src, tmp_dir):
    """LibreOffice headless office→PDF（可选增强）。不可用/失败→None（退 substrate-only）。"""
    soffice = find_libreoffice()
    if not soffice:
        return None
    try:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", tmp_dir, src],
                       check=True, capture_output=True, timeout=180)
        stem = os.path.splitext(os.path.basename(src))[0]
        pdf = os.path.join(tmp_dir, stem + ".pdf")
        return pdf if os.path.isfile(pdf) else None
    except Exception:
        return None


def render_office(src, doc_id, prefix, scale):
    """office→PDF→页图（LibreOffice 可用时）。返回 [{name,data,page}] 或 []（substrate-only）。"""
    if not OFFICE_RENDER_ENABLED:
        return []
    tmp = tempfile.mkdtemp(prefix="ingest_render_")
    try:
        pdf = office_to_pdf(src, tmp)
        if not pdf:
            return []
        return render_pdf_to_images(pdf, doc_id, prefix, scale)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ============================================================ substrate 层（原生结构化精确文本）

def _docx_inline(para):
    """行内加粗/斜体按 run 重建。"""
    parts = []
    for run in para.runs:
        t = run.text
        if not t:
            continue
        if run.bold and run.italic:
            t = "***%s***" % t
        elif run.bold:
            t = "**%s**" % t
        elif run.italic:
            t = "*%s*" % t
        parts.append(t)
    return "".join(parts) or para.text


def _docx_list_prefix(para):
    """列表检测：style 名（List Bullet/Number，numPr 常继承自 style 不在段落 pPr）+ numPr 兜底。

    简化 numFmt（bullet「- 」/编号「1. 」），LLM 结构复核可精化中文编号等。
    """
    try:
        style = (para.style.name or "") if para.style is not None else ""
        if "List Bullet" in style:
            return "- "
        if "List Number" in style:
            return "1. "
        pPr = para._p.pPr
        if pPr is not None and pPr.numPr is not None:
            return "- "
    except Exception:
        pass
    return None


def docx_to_substrate(doc):
    """DOCX→清洁结构化 md substrate（Heading→#/列表/行内/表格合并去重）。"""
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    lines = []
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            para = Paragraph(child, doc)
            style = (para.style.name or "") if para.style is not None else ""
            txt = _docx_inline(para).strip()
            if not txt:
                continue
            m = re.match(r"Heading (\d)", style)
            if style == "Title":
                lines.append("# " + txt)
            elif m:
                lines.append("#" * min(int(m.group(1)) + 1, 6) + " " + txt)
            else:
                prefix = _docx_list_prefix(para)
                lines.append((prefix or "") + txt)
        elif isinstance(child, CT_Tbl):
            table = Table(child, doc)
            rows = []
            for row in table.rows:
                cells, prev = [], None
                for c in row.cells:
                    if c._tc is prev:  # 合并单元格去重
                        continue
                    prev = c._tc
                    cells.append(c.text)
                rows.append(cells)
            mt = md_table(rows)
            if mt:
                lines.append(mt)
    return "\n\n".join(lines)


def docx_inventory(doc):
    """DOCX 完整性 inventory：段落文本 + 表格单元格文本。"""
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    items = []
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            t = Paragraph(child, doc).text.strip()
            if t:
                items.append(t)
        elif isinstance(child, CT_Tbl):
            for row in Table(child, doc).rows:
                for c in row.cells:
                    t = c.text.strip()
                    if t:
                        items.append(t)
    return items


def docx_embedded_images(doc, doc_id):
    """导出 word/media 内嵌图（DOCX 内嵌图表路径）。返回 [{name,data}]。"""
    out = []
    try:
        for rel_id, rel in doc.part.rels.items():
            if "image" in rel.reltype:
                try:
                    blob = rel.target_part.blob
                    ext = rel.target_part.content_type.split("/")[-1].replace("jpeg", "jpg")
                    out.append({"name": "%s_media%03d.%s" % (doc_id, len(out) + 1, ext),
                                "data": blob})
                except Exception:
                    pass
    except Exception:
        pass
    return out


def xlsx_sheet_grid(ws, wsf):
    """XLSX sheet→单元格网格 md（合并保留/多行<br>/公式双读）+ inventory cells。"""
    from openpyxl.utils import get_column_letter
    rows = list(ws.iter_rows())
    grid, cells = [], []
    for row in rows:
        line = []
        for cell in row:
            v = cell.value
            try:
                fv = wsf.cell(row=cell.row, column=cell.column).value
            except Exception:
                fv = None
            formula = False
            if v is None and isinstance(fv, str) and fv.startswith("="):
                v = fv
                formula = True
            s = cell_str(v)
            line.append(s)
            if s.strip():
                cells.append(s)
        grid.append(line)
    # 去尾部全空行
    while grid and not any(c.strip() for c in grid[-1]):
        grid.pop()
    mt = md_table(grid)
    note = ""
    if ws.merged_cells.ranges:
        note = "\n\n（合并单元格值归左上，多行单元格以 <br> 保全）"
    return mt + note, cells, grid


def _pptx_para_text(para):
    """段落文本：Wingdings/Symbol 字体引导符号 run→列表前缀「- 」（限制⑥）。

    业务 PPT 的项目符号常是文本框里的字面符号字符（Wingdings 字体 run，非程序化 buChar），
    text_frame.text 直抽会留下乱码字符。run.font.name 机械识别符号字体，引导短符号 run 映射为
    列表前缀（视觉即项目符号，结构重建非臆造）；非符号 run 原样保全。无符号字体时与 p.text 字节等价。
    """
    parts = []
    leading = True
    for r in para.runs:
        t = r.text
        if not t:
            continue
        fn = r.font.name or ""
        if ("Wingdings" in fn or "Symbol" in fn) and leading and len(t.strip()) <= 2:
            parts.append("- ")
            leading = False
            continue
        parts.append(t)
        if t.strip():
            leading = False
    return "".join(parts)


def pptx_positional_substrate(slide, doc_id, slide_idx, pictures):
    """PPTX slide→位置 substrate（shape 按视觉位置 top,left 排序，bbox+文本+类型+表格+图片引用）。

    供 LLM 布局重建（按视觉位置排序防结构崩塌）。文本经 _pptx_para_text 段落级提取
    （Wingdings/Symbol 引导符号→列表前缀「- 」，限制⑥）。返回 (substrate_text, inventory_items)。
    """
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    shapes = []

    def collect(shp, depth=0):
        try:
            st = shp.shape_type
        except Exception:
            st = None
        bbox = (emu_in(shp.left), emu_in(shp.top), emu_in(shp.width), emu_in(shp.height))
        entry = {"bbox": bbox, "type": str(st).split(".")[-1] if st else "SHAPE",
                 "text": "", "table": "", "pic": None, "depth": depth}
        try:
            if shp.has_text_frame:
                txt = "\n".join(_pptx_para_text(p) for p in shp.text_frame.paragraphs).strip()
                if txt:
                    entry["text"] = txt
        except Exception:
            pass
        try:
            if shp.has_table:
                rows = [[c.text for c in row.cells] for row in shp.table.rows]
                entry["table"] = md_table(rows)
        except Exception:
            pass
        try:
            if st == MSO_SHAPE_TYPE.PICTURE:
                img = shp.image
                name = "%s_slide%d_img%03d.%s" % (doc_id, slide_idx, len(pictures) + 1, img.ext)
                pictures.append({"name": name, "data": img.blob})
                entry["pic"] = name
        except Exception:
            pass
        shapes.append(entry)
        # 递归组合 shape（一层）
        try:
            if st == MSO_SHAPE_TYPE.GROUP:
                for sub in shp.shapes:
                    collect(sub, depth + 1)
        except Exception:
            pass

    for shp in slide.shapes:
        collect(shp)
    # 按视觉位置排序（top 优先，再 left；None 坐标排末）
    shapes.sort(key=lambda e: (e["bbox"][1] if e["bbox"][1] is not None else 1e9,
                               e["bbox"][0] if e["bbox"][0] is not None else 1e9))
    lines = ["[幻灯片位置 substrate — shape 按视觉位置(top,left)排序，bbox 单位英寸(x,y,w,h)，供布局重建]"]
    inventory = []
    for i, e in enumerate(shapes):
        x, y, w, h = e["bbox"]
        head = "shape#%d type=%s bbox=(%s,%s,%s,%s)" % (i + 1, e["type"], x, y, w, h)
        if e["pic"]:
            lines.append(head + " [图片] image=attachments/" + e["pic"])
        elif e["table"]:
            lines.append(head + " [表格]\n" + e["table"])
        elif e["text"]:
            lines.append(head + " text=" + repr(e["text"]))
            inventory.append(e["text"])
        else:
            lines.append(head + " [无文本图形]")
    # 备注（专家口述权威信号）
    try:
        if slide.has_notes_slide:
            ntxt = slide.notes_slide.notes_text_frame.text.strip()
            if ntxt:
                lines.append("[备注] " + ntxt)
                inventory.append(ntxt)
    except Exception:
        pass
    return "\n".join(lines), inventory


# ============================================================ 格式 handler（懒 import，产准备态单元）

def parse_pdf(path, password, doc_id, scale):
    pypdf = importlib.import_module("pypdf")
    reader = pypdf.PdfReader(path)
    if reader.is_encrypted:
        try:
            res = reader.decrypt(password or "")
        except Exception as exc:
            sys.stderr.write("exit 2: PDF 解密失败（AES 需 pip install pypdf[crypto]，或密码错）：%s\n" % exc)
            sys.exit(2)
        if res == 0:
            sys.stderr.write("exit 2: PDF 密码错（未解密）\n")
            sys.exit(2)
    titles = {}

    def walk(items):
        for it in items:
            if isinstance(it, list):
                walk(it)
            else:
                try:
                    titles.setdefault(reader.get_destination_page_number(it), it.title)
                except Exception:
                    pass
    try:
        walk(reader.outline)
    except Exception:
        pass
    # 渲染每一页（不变量：无静默跳过）
    renders = render_pdf_to_images(path, doc_id, "p", scale)
    units, gaps = [], []
    npages = len(reader.pages)
    for i in range(npages):
        try:
            text = reader.pages[i].extract_text() or ""
        except Exception:
            text = ""
        heading = titles.get(i) or ("第 %d 页" % (i + 1))
        loc = {"kind": "page", "page": i + 1}
        inv_items = [ln.strip() for ln in text.splitlines() if ln.strip()]
        render = renders[i] if i < len(renders) else None
        units.append({"heading": heading, "locator": loc,
                      "render": render, "substrate": None,
                      "inventory": {"kind": "pdf-text-layer", "items": inv_items},
                      "pictures": [], "is_table": False, "table_rows": 0, "table_headers": []})
        if not inv_items:
            gaps.append({"kind": "image-only-page", "locator": loc,
                         "note": "无文本层（图片型页），完整性靠整页渲染呈现 + IG1 目视复核"})
    doc_date, dsrc = None, "unknown"
    try:
        md = reader.metadata
        if md is not None:
            doc_date = iso_date(md.creation_date)
            if doc_date:
                dsrc = "metadata"
    except Exception:
        pass
    return {"units": units, "gaps": gaps, "doc_date": doc_date, "doc_date_source": dsrc,
            "library": "pypdf==%s + pypdfium2==%s" % (
                pypdf.__version__, importlib.metadata.version("pypdfium2")),
            "units_total": npages}


def parse_word(path, password, doc_id, scale):
    docx = importlib.import_module("docx")
    d = docx.Document(path)
    substrate = docx_to_substrate(d)
    inventory = docx_inventory(d)
    pictures = docx_embedded_images(d, doc_id)
    renders = render_office(path, doc_id, "p", scale)  # 可选 LibreOffice 布局参照
    units, gaps = [], []
    # DOCX 以 substrate 为精确文本主路径；按页渲染（若有）或整体一节
    if renders:
        for r in renders:
            units.append({"heading": "第 %d 页" % r["page"], "locator": {"kind": "page", "page": r["page"]},
                          "render": r, "substrate": None,
                          "inventory": {"kind": "docx-render-page", "items": []},
                          "pictures": [], "is_table": False, "table_rows": 0, "table_headers": []})
        # substrate 作为整体参照节
        units.append({"heading": "正文结构化 substrate", "locator": {"kind": "para"},
                      "render": None, "substrate": substrate,
                      "inventory": {"kind": "docx-paragraph", "items": inventory},
                      "pictures": pictures, "is_table": False, "table_rows": 0, "table_headers": []})
    else:
        units.append({"heading": d.core_properties.title or "正文", "locator": {"kind": "para"},
                      "render": None, "substrate": substrate,
                      "inventory": {"kind": "docx-paragraph", "items": inventory},
                      "pictures": pictures, "is_table": False, "table_rows": 0, "table_headers": []})
    if pictures:
        gaps.append({"kind": "embedded-image", "locator": {"kind": "para"},
                     "note": "%d 张内嵌图导出 attachments，需 I2 转录（DOCX 内嵌图表路径）" % len(pictures)})
    doc_date, dsrc = None, "unknown"
    try:
        doc_date = iso_date(d.core_properties.created)
        if doc_date:
            dsrc = "metadata"
            if doc_date.startswith("2013"):
                gaps.append({"kind": "missing-section", "locator": {},
                             "note": "doc_date 为模板默认值（2013），可信度低，待确认"})
    except Exception:
        pass
    return {"units": units, "gaps": gaps, "doc_date": doc_date, "doc_date_source": dsrc,
            "library": "python-docx==" + docx.__version__, "units_total": len(units)}


def parse_excel(path, password, doc_id, scale):
    openpyxl = importlib.import_module("openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True)
    wbf = openpyxl.load_workbook(path, data_only=False)
    renders = render_office(path, doc_id, "sheet", scale)  # 可选 LibreOffice 布局参照
    render_by_idx = {r["page"]: r for r in renders}
    units, gaps = [], []
    for idx, ws in enumerate(wb.worksheets):
        wsf = wbf[ws.title]
        grid_md, cells, grid = xlsx_sheet_grid(ws, wsf)
        from openpyxl.utils import get_column_letter
        cell_range = "%s%d:%s%d" % (get_column_letter(ws.min_column or 1), ws.min_row or 1,
                                    get_column_letter(ws.max_column or 1), ws.max_row or 1)
        loc = {"kind": "sheet", "sheet": ws.title, "cell": cell_range}
        header = grid[0] if grid else []
        formula_found = any(c.startswith("=") for row in grid for c in row)
        if formula_found:
            gaps.append({"kind": "formula-no-cache", "locator": loc,
                         "note": "公式无缓存值（从未在 Excel 计算），录公式文本"})
        pictures = []
        for im in getattr(ws, "_images", []):
            try:
                blob = im._data()
                pictures.append({"name": "%s_sheet%d_img%03d.png" % (doc_id, idx + 1, len(pictures) + 1),
                                 "data": blob})
            except Exception:
                pass
        if getattr(ws, "_charts", None):
            gaps.append({"kind": "embedded-object", "locator": loc, "note": "图表未解析（需 I2 识图）"})
        units.append({"heading": ws.title, "locator": loc,
                      "render": render_by_idx.get(idx + 1), "substrate": grid_md,
                      "inventory": {"kind": "xlsx-cell", "items": cells},
                      "pictures": pictures, "is_table": True,
                      "table_rows": max(0, len(grid) - 1),
                      "table_headers": [h for h in header if h and h.strip()]})
    doc_date, dsrc = None, "unknown"
    try:
        doc_date = iso_date(wb.properties.created)
        if doc_date:
            dsrc = "metadata"
    except Exception:
        pass
    return {"units": units, "gaps": gaps, "doc_date": doc_date, "doc_date_source": dsrc,
            "library": "openpyxl==" + openpyxl.__version__, "units_total": len(wb.worksheets)}


def parse_ppt(path, password, doc_id, scale):
    pptx = importlib.import_module("pptx")
    prs = pptx.Presentation(path)
    renders = render_office(path, doc_id, "slide", scale)  # 可选 LibreOffice 全视觉保真
    render_by_idx = {r["page"]: r for r in renders}
    units, gaps = [], []
    for idx, slide in enumerate(prs.slides):
        title = ""
        try:
            if slide.shapes.title is not None:
                title = (slide.shapes.title.text or "").strip()
        except Exception:
            title = ""
        title = title or ("幻灯片 %d" % (idx + 1))
        loc = {"kind": "slide", "slide": idx + 1}
        pictures = []
        substrate, inventory = pptx_positional_substrate(slide, doc_id, idx + 1, pictures)
        units.append({"heading": title, "locator": loc,
                      "render": render_by_idx.get(idx + 1), "substrate": substrate,
                      "inventory": {"kind": "pptx-shape", "items": inventory},
                      "pictures": pictures, "is_table": False, "table_rows": 0, "table_headers": []})
        try:
            for shape in slide.shapes:
                if getattr(shape, "has_chart", False) and shape.has_chart:
                    gaps.append({"kind": "embedded-object", "locator": loc, "note": "chart 未解析"})
                    break
        except Exception:
            pass
    doc_date, dsrc = None, "unknown"
    try:
        doc_date = iso_date(prs.core_properties.created)
        if doc_date:
            dsrc = "metadata"
    except Exception:
        pass
    return {"units": units, "gaps": gaps, "doc_date": doc_date, "doc_date_source": dsrc,
            "library": "python-pptx==" + pptx.__version__, "units_total": len(prs.slides._sldIdLst)}


def parse_image(path, password, doc_id, scale):
    PIL = importlib.import_module("PIL.Image")
    im = PIL.open(path)
    fmt = (im.format or "png").lower()
    with open(path, "rb") as fh:
        data = fh.read()
    name = "%s.%s" % (doc_id, fmt)
    doc_date, dsrc = None, "unknown"
    try:
        exif = im.getexif()
        dt = exif.get(36867) or exif.get(306)
        if dt:
            m = re.match(r"(\d{4}):(\d{2}):(\d{2})", str(dt))
            if m:
                doc_date = "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))
                dsrc = "exif"
    except Exception:
        pass
    units = [{"heading": doc_id, "locator": {"kind": "image"},
              "render": {"name": name, "data": data, "page": 1}, "substrate": None,
              "inventory": {"kind": "image", "items": []},
              "pictures": [], "is_table": False, "table_rows": 0, "table_headers": []}]
    return {"units": units, "gaps": [], "doc_date": doc_date, "doc_date_source": dsrc,
            "library": "Pillow==" + PIL.__version__, "units_total": 1}


HANDLERS = {"pdf": parse_pdf, "word": parse_word, "excel": parse_excel,
            "ppt": parse_ppt, "image": parse_image}


# ============================================================ 组装（manifest schema 2.0 + 清洁 provisional MD）

def build_md_provisional(sections, units):
    """清洁 provisional MD（无机器锚）：substrate 优先，render/图片嵌入溯源。最终 MD 由 I2 转录重建。"""
    lines = []
    for sec, u in zip(sections, units):
        if u.get("substrate"):
            lines.append(u["substrate"])
        if u.get("render"):
            lines.append("![[attachments/%s]]" % u["render"]["name"])
        for pic in u.get("pictures", []):
            lines.append("![[attachments/%s]]" % pic["name"])
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def build_pack(doc_id, basename, src_sha, src_size, res, authority, sensitivity,
               scale=DEFAULT_RENDER_SCALE):
    units = res["units"]
    sections, all_images, seeds, full_parts = [], [], [], []
    for i, u in enumerate(units):
        sid = "s%03d" % (i + 1)
        render = u.get("render")
        rendered_image = None
        if render:
            rendered_image = {"name": render["name"], "sha256": bytes_sha256(render["data"]),
                              "bytes": len(render["data"])}
            all_images.append(render)
        substrate = u.get("substrate")
        substrate_obj = None
        if substrate:
            substrate_obj = {"text": substrate, "text_sha256": bytes_sha256(substrate.encode("utf-8"))}
            full_parts.append(substrate)
        inv = u.get("inventory")
        inventory_obj = None
        if inv is not None:
            items = inv.get("items", [])
            inventory_obj = {"kind": inv["kind"], "count": len(items),
                             "items_sha256": bytes_sha256(canonical_json(items).encode("utf-8")),
                             "items": items}
        pics = []
        for pic in u.get("pictures", []):
            pics.append({"name": pic["name"], "sha256": bytes_sha256(pic["data"]),
                         "bytes": len(pic["data"])})
            all_images.append(pic)
        hint_text = substrate or " ".join(inv.get("items", [])) if inv else (substrate or "")
        hint = classify_hint(hint_text or "", u.get("is_table", False), u.get("table_rows", 0))
        flags = sensitive_flags(hint_text or "")
        sections.append({"section_id": sid, "heading": u["heading"], "locator": u["locator"],
                         "extraction": "prepared", "rendered_image": rendered_image,
                         "substrate": substrate_obj, "inventory": inventory_obj, "pictures": pics,
                         "semantic_hint": hint, "sensitive_flags": flags,
                         # 接缝契约 affordance（s1-handoff-contract §一/三/四/五）：I2 回填，准备态 null/[]
                         "unit_type": None, "verification_status": None,
                         "personal_info_regions": [], "md_heading": None,
                         "text": None, "text_sha256": None, "transcribe_meta": None})
        if u["heading"]:
            full_parts.append(u["heading"])
            seeds.append((u["heading"], "heading"))
        for h in u.get("table_headers", []):
            if h and h.strip():
                seeds.append((h.strip(), "table-header"))
        if substrate:
            # 2.0 单节化后 DOCX 标题移入 substrate，ATX 标题补取为结构种子（限制⑫，恢复切节期覆盖）
            for hm in re.finditer(r"(?m)^#{1,6}[ \t]+(.+?)[ \t]*$", substrate):
                ht = hm.group(1).strip()
                if ht:
                    seeds.append((ht, "substrate-heading"))
    full_text = "\n".join(full_parts)
    term_map = {}
    for term, source in seeds:
        term = term.strip()
        if not term:
            continue
        if term not in term_map:
            term_map[term] = {"term": term, "freq": full_text.count(term),
                              "source": source, "locators": []}
    for term, info in term_map.items():
        info["locators"] = sorted([sec["section_id"] for sec in sections
                                   if (sec["substrate"] and term in sec["substrate"]["text"])
                                   or term in sec["heading"]])
    term_candidates = sorted(term_map.values(), key=lambda x: (-x["freq"], x["term"]))

    gaps = []
    for i, g in enumerate(res["gaps"]):
        gaps.append({"gap_id": "g%03d" % (i + 1), "kind": g["kind"],
                     "locator": g.get("locator", {}), "note": g["note"],
                     "resolution": "pending", "resolved_by": None})
    gaps.sort(key=lambda x: x["gap_id"])

    atts = [{"name": a["name"], "sha256": bytes_sha256(a["data"]), "bytes": len(a["data"])}
            for a in all_images]
    atts.sort(key=lambda x: x["name"])

    pack_id = "P-" + bytes_sha256(canonical_json(
        {"sources": [{"name": basename, "sha256": src_sha}]}).encode("utf-8"))[:12]
    stype = res["source_type"]
    if stype == "pdf":
        pages = [s["locator"].get("page") for s in sections if s["locator"].get("kind") == "page"]
        locator_range = "p.%d-%d" % (min(pages), max(pages)) if pages else ""
    elif stype == "excel":
        sheets = sorted(set(s["locator"].get("sheet", "") for s in sections
                            if s["locator"].get("kind") == "sheet"))
        locator_range = "sheet:" + "|".join(sheets)
    elif stype == "ppt":
        slides = [s["locator"].get("slide") for s in sections if s["locator"].get("kind") == "slide"]
        locator_range = "slide:%d-%d" % (min(slides), max(slides)) if slides else ""
    elif stype == "image":
        locator_range = "image"
    else:
        locator_range = "para"
    manifest = {
        "schema_version": PACK_SCHEMA_VERSION,
        "pack_id": pack_id,
        "doc_id": doc_id,
        "source": {"name": basename, "source_type": stype, "sha256": src_sha,
                   "bytes": src_size, "doc_date": res["doc_date"],
                   "doc_date_source": res["doc_date_source"], "authority": authority},
        "parser": {"name": "parse_documents.py", "script_version": SCRIPT_VERSION,
                   "library": res["library"], "render_scale": scale,  # F35：记实际 args.render_scale（防元数据漂移）
                   "libreoffice_render": bool(find_libreoffice()) and OFFICE_RENDER_ENABLED},
        "coverage": {"units_total": res["units_total"],
                     "units_prepared": sum(1 for s in sections if s["extraction"] == "prepared"),
                     "units_transcribed": sum(1 for s in sections if s["extraction"] == "transcribed"),
                     "locator_range": locator_range},
        "sections": sections,
        "term_candidates": term_candidates,
        "gaps": gaps,
        "conflicts": [],
        "attachments": atts,
        "sensitivity": {"level": sensitivity,
                        "note": "照录不脱敏；脱敏在 S1→S2（sensitivity-rules §四）"},
    }
    md = build_md_provisional(sections, units)
    return manifest, md, all_images


# ============================================================ main

def main():
    ap = argparse.ArgumentParser(description="ontology-ingest 保真进料机械层（渲染+inventory+substrate，无 LLM）")
    ap.add_argument("inputs", nargs="+", help="输入文档（pdf/docx/xlsx/pptx/图片）")
    ap.add_argument("--output-dir", default=None, help="输出根（默认 cwd/萃取原料包）")
    ap.add_argument("--doc-id", default=None, help="显式 doc_id（仅单文档）")
    ap.add_argument("--authority", default="未登记",
                    choices=["正式制度", "专家口述", "二手转述", "未登记"])
    ap.add_argument("--sensitivity", default="未登记", choices=["真实业务", "虚构通用", "未登记"])
    ap.add_argument("--password", default=None, help="PDF 解密密码")
    ap.add_argument("--render-scale", type=float, default=DEFAULT_RENDER_SCALE, help="PDF 渲染 scale（默认 2.0≈144DPI）")
    ap.add_argument("--no-office-render", action="store_true",
                    help="禁用 LibreOffice office 全视觉渲染，强制 substrate-only canonical 档（纯 pip 确定性，limits ⑪）")
    ap.add_argument("--force", action="store_true", help="覆盖已有非空包目录（再解析守卫）")
    args = ap.parse_args()

    global OFFICE_RENDER_ENABLED
    if args.no_office_render:
        OFFICE_RENDER_ENABLED = False

    if args.doc_id and len(args.inputs) > 1:
        sys.stderr.write("exit 2: --doc-id 仅适用单文档输入\n")
        sys.exit(2)
    for p in args.inputs:
        if not os.path.isfile(p):
            sys.stderr.write("exit 2: 文件不存在：%s\n" % p)
            sys.exit(2)
        ext = os.path.splitext(p)[1].lower()
        if ext not in EXT_TYPE:
            sys.stderr.write("exit 2: 不支持的格式：%s（支持 pdf/docx/xlsx/pptx/图片）\n" % ext)
            sys.exit(2)

    out_root = args.output_dir or os.path.join(os.getcwd(), "萃取原料包")
    ok = 0
    for p in args.inputs:
        src = os.path.realpath(p)
        ext = os.path.splitext(p)[1].lower()
        stype = EXT_TYPE[ext]
        before = file_sha256(src)
        src_size = os.path.getsize(src)
        basename = os.path.basename(src)
        doc_id = sanitize_doc_id(args.doc_id) if args.doc_id else sanitize_doc_id(os.path.splitext(basename)[0])
        pack_dir = os.path.join(out_root, doc_id)
        # F18：包目录包含守卫——doc_id 净化后 realpath 仍须落在 out_root 内（防路径穿越）
        _pack_real = os.path.realpath(pack_dir)
        _root_real = os.path.realpath(out_root)
        if not (_pack_real == _root_real or _pack_real.startswith(_root_real + os.sep)):
            sys.stderr.write("exit 2: 包目录越界（doc-id 路径净化守卫）：%s\n" % pack_dir)
            sys.exit(2)
        if os.path.realpath(pack_dir) == src:
            sys.stderr.write("exit 2: 输出不得等于源文档：%s\n" % pack_dir)
            sys.exit(2)
        if os.path.isdir(pack_dir) and os.listdir(pack_dir) and not args.force:
            sys.stderr.write("exit 2: 包目录已存在且非空（再解析守卫，护转录回填层）：%s；--force 覆盖\n" % pack_dir)
            sys.exit(2)
        handler = HANDLERS[stype]
        try:
            res = handler(src, args.password, doc_id, args.render_scale)
        except ImportError as exc:
            sys.stderr.write("exit 2: 缺解析/渲染库（%s）；pip install pypdf pypdfium2 python-docx openpyxl python-pptx Pillow\n" % exc)
            sys.exit(2)
        except SystemExit:
            raise
        except Exception as exc:
            sys.stderr.write("exit 2: 文件解析异常（%s）：%s\n" % (basename, exc))
            sys.exit(2)
        res["source_type"] = stype
        manifest, md, images = build_pack(doc_id, basename, before, src_size, res,
                                          args.authority, args.sensitivity,
                                          scale=args.render_scale)
        os.makedirs(pack_dir, exist_ok=True)
        att_dir = os.path.join(pack_dir, "attachments")
        if images:
            os.makedirs(att_dir, exist_ok=True)
            for a in images:
                with open(os.path.join(att_dir, a["name"]), "wb") as fh:
                    fh.write(a["data"])
        with open(os.path.join(pack_dir, doc_id + ".md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(md)
        with open(os.path.join(pack_dir, "manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
        after = file_sha256(src)
        if before != after:
            sys.stderr.write("exit 1: 零回写断言失败——源文档被改动：%s\n" % basename)
            sys.exit(1)
        ok += 1
        n_render = sum(1 for s in manifest["sections"] if s["rendered_image"])
        n_sub = sum(1 for s in manifest["sections"] if s["substrate"])
        print("准备完成：%s → %s（units %d / render %d / substrate %d / gaps %d / attachments %d）" % (
            basename, pack_dir, len(manifest["sections"]), n_render, n_sub,
            len(manifest["gaps"]), len(manifest["attachments"])))
    print("共 %d 文档准备成功（exit 0；待 I2 整页转录 + 完整性交叉校验）" % ok)
    sys.exit(0)


if __name__ == "__main__":
    main()
