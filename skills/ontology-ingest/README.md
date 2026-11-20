# ontology-ingest：异构文档保真进料前置 skill

> 把 PDF/图片/Excel/Word/PPT 异构业务资料统一转为「萃取原料包」（**清洁保真 MD** + canonical manifest.json + attachments/），喂入 ontology-model S1。**唯一目标=萃取就绪的保真（内容完备性/准确性/结构性）**：还原结构+保真全量内容，不理解内容本身（萃取是 S1 的事）——S1 能消费的保真才是 fitness-for-purpose。
> **架构**：LLM 整页布局感知转录 primary（每个视觉单元必过）+ 机械渲染/完整性 inventory/原生 substrate/交叉校验护栏。
> **接缝契约**：ingest 产物与 model S1 消费按唯一接口权威 `../ontology-model/references/s1-handoff-contract.md` 共同设计（非扔过墙式松耦合），产五类 affordance（形态维 unit_type / 图样保真呈现 / 置信度 verification_status / 个人信息精确位 personal_info_regions / 溯源映射 md_heading）。**图样保真**：流程图/交互图/架构图嵌原图 + 图内文字照录，拓扑解读留 S1 多模态 Read 原图（不文字扁平化）。
> 当前版本见 SKILL.md frontmatter；版本历史见 `CHANGELOG.md`。
> **本文件=人类手册**（三受众拆分：SKILL.md=LLM 执行契约 / README=人类手册 / CHANGELOG=版本历史）。

## 一、解决什么问题

ontology-model 假设输入已是「可阅读文本」，但真实业务资料是异构形态：制度是 Word/PDF、费率是 Excel、流程是 PPT、票据样本是扫描件/图片。缺一个前置引擎把这些原料**保真**转为 S1 可消费的结构化进料。

**设计原则**：机械验证通过 ≠ 业务保真。纯机械提取无法重建视觉布局（图片密集文档易静默丢失内容、结构倾倒、机器锚污染下游），故 LLM 整页布局感知转录为主路径，机械渲染/inventory/substrate 降为完整性护栏。

本 skill 三层架构：

1. **机械层**（I1，确定性 CLI，无 LLM）：①渲染（PDF 每页→PNG / 图片直供 / office LibreOffice 可选页图）②inventory（完整性 ground truth：文本层/单元格/段落/shape 文本）③substrate（原生精确文本：DOCX 结构化 md / XLSX 网格 / PPTX 位置 substrate）。产**准备态包**（不产最终正文）。
2. **LLM 整页转录**（I2，primary，每单元必过）：只读 vision agent 读渲染图（+substrate）→清洁布局保真 md（层级/表格/分组/多列；**图样类嵌原图保真**），零臆造，模糊登记候选读法，水印/高置信装饰剔除；顺手吐 **unit_type 形态标签**（转录副产品）+ md_heading 语义标题 + personal_info_regions 个人信息精确位。
3. **机械组装 + 交叉校验 + 收卷**（I3）：**`assemble_pack.py` 机械组装每源件单一 `<doc_id>.md`**（从 manifest.sections[].text 按序拼接，**机械保证按序/不丢弃/图嵌守恒**，非 LLM 合并——LLM 合并有遗漏/截断/改写风险且全文进上下文不可持续）+ inventory 覆盖断言（防 LLM 漏字）+ 清洁 md 断言 + 图样保真断言 + 接缝 affordance 收卷（unit_type/verification_status/md_heading 节序断言）+ 机械层零触碰 + uncertain 人核 → IG1 停等用户亲自确认保真 → 喂入 model S1（按接缝契约消费）。**合并是确定性机械操作**（铁律 4：脚本做机械操作，LLM 做语义操作）——合并形态「一份资料一份文档」（唯一 H1=doc_id / 单元 H2 起连续层级 / `---` 分页节 / 图嵌裸文件名 / 空单元诚实占位）。

**不变量**：任何视觉单元都不被静默路由 mechanical-only 跳过 LLM。**通用性红线**：不依赖本地专有工具/知识——pip 解析渲染库 + 可选 LibreOffice 子进程 + 通用多模态 LLM（编排外接）；无 Java、无系统 OCR 二进制、无本地 VLM、无专有 DB 连接器。**非禁用多模态/LLM**——整页转录是通用多模态能力。

**图样保真与形态分类 fail-safe**：解析目的是为建模萃取服务——流程图/页面交互图/架构图的**拓扑**（分支/并行/泳道/时序）是 BPMN2.0/OWL-S 流程语义的直接载体，拍平成「有序步骤列表」文字会扁平化丢失。故图样类清洁 md **嵌原图 + 图内文字照录**（节点文字/箭头条件/标注），拓扑解读留 S1 Read 原图提炼（ingest 只保「形」不解读「义」）；纯文字类（正文/表格）不嵌原图（清洁 md 对 RAG 友好，原图仍在 attachments 兜底）。**形态分类不承重**：机械层无条件保图（attachments+manifest 指针完全不依赖分类），unit_type 只驱动清洁 md 呈现不驱动图是否存在——误判可恢复（流程图误判文字类→S1 拿原图重解读；内容图误判装饰→IG1 人核兜底），拿不准保图保守，唯一剔除高置信装饰。分类是 LLM 看整页图做布局重建时顺手产出（机械分不了形态）。

## 二、快速上手

```bash
# 1. 机械层（五格式批量，每文档独立包子目录；默认落 cwd/萃取原料包/<doc_id>/）
python3 <skill根>/scripts/parse_documents.py 制度.docx 费率表.xlsx 流程.pptx 票据样本.png \
    --output-dir <run>/萃取原料包 --authority 正式制度 --sensitivity 虚构通用 [--render-scale 2.0] [--no-office-render]
#    → 准备态包：渲染图 + inventory + substrate + manifest schema 2.1（extraction=prepared，接缝 affordance null/[]）
# 2. 整页转录（primary，每个 prepared 单元必过）：委托 ontology-vision-extractor agent（page-transcribe）
#    （传渲染图路径+doc_id+section_id+sha+substrate+inventory+prompt-vision-extract.md）→ page-transcribe JSON
#    → 主会话校验回填（schema+sha 匹配，机械层 sha 零触碰，inventory 覆盖交叉校验，uncertain 进 gaps）
# 3. 机械组装（I3，每源件单一合并 md，机械保证按序/不丢弃）：
python3 <skill根>/scripts/assemble_pack.py --pack-root <run>/萃取原料包   # 或 PACK_DIR... 逐个
#    → 每源件 <doc_id>.md（H1=doc_id / 单元 H2 起连续 / --- 分页 / 图嵌裸文件名 / 空单元占位）
#    → 自校验 exit 0/1/2：唯一 H1 / 无机器锚 / 图嵌守恒 / 逐单元完备按序 / source.sha 零回写
# 4. 收卷：I3 交叉校验 + 清洁 md 断言 → IG1 呈覆盖/gaps/uncertain/inventory-miss/转录计数
#    → 用户亲自确认保真（目视复核 image-only 页 + uncertain）→ 喂入 ontology-model S1（入口 (a)）
```

`<skill根>`=本 skill 根目录（Claude Code 环境=`.claude/skills/ontology-ingest/`；独立套件=`skills/ontology-ingest/`）。统一 CLI 门面：`python3 scripts/ontology_cli.py ingest parse ...`（套件级，透传 exit 码）。

**闸门**：IG1（原料包保真确认：覆盖/gaps/uncertain/inventory-miss/转录计数 + 目视复核）——停等用户，**不代签**。LLM 转录须人核保真（机械交叉校验是护栏非权威）。

**exit 三态**：0=准备成功（gap 登记不阻塞）/ 1=零回写断言失败 / 2=输入错（缺文件/不支持格式/坏文件/输出碰撞/再解析守卫/同 stem 碰撞/缺库/AES/密码错）。

## 三、萃取原料包与五格式路由

```text
萃取原料包/<doc_id>/
├── <doc_id>.md      # 清洁 markdown（无机器锚）：I1 准备态=substrate/图嵌入脚手架；I2 逐单元转录回填 manifest；I3 机械组装（assemble_pack.py）每源件单一合并 md（「一份资料一份文档」形态）
├── manifest.json    # canonical（schema 2.1，零时间戳，机器元数据 + 接缝 affordance 全在此）
└── attachments/     # 图像二进制同名溯源：PDF 渲染页图/office 页图/原图副本/内嵌图；sha256 入 manifest
```

| 格式 | 渲染（机械） | LLM 转录（primary） | substrate / inventory（护栏） |
|---|---|---|---|
| PDF | pypdfium2 渲染**每一页**→PNG | 整页布局感知→清洁 md（层级/表格；流程图等图样类嵌原图保真） | pypdf 文本层＝inventory（防漏字）；RC4 纯 pip 可解、AES 需 pypdf[crypto] |
| PPTX | LibreOffice 可选→幻灯片 PNG（增强，非必需） | 整幻灯片分组重建（据 bbox + 机械列表前缀） | python-pptx **位置 substrate**（bbox+文本+类型+分组，按视觉位置排序；**Wingdings 项目符号机械映射「- 」**）+备注 inventory |
| 图片 | 原图直供（PIL 元数据） | 整图布局感知（多列分区/水印剔除/误读核对） | inventory items=[]（image-only 诚实边界，靠 IG1 目视） |
| DOCX | LibreOffice 可选页图 + word/media 内嵌图导出 | 内嵌图转录 + 正文结构复核 | python-docx **结构化 substrate**（Heading/列表/行内/表格合并去重）+段落 inventory |
| XLSX | LibreOffice 可选 sheet 图 | **语义重组为 headed 表**（结构重建非 OCR） | openpyxl **单元格 substrate**（合并保留/`<br>` 多行/公式双读）+单元格 inventory |

**substrate 优先理由**：机械直抽对原生结构化文本近无损且**比 OCR 更准**——LLM 在此做结构重建（语义分组/层级/多行保全），不重新 OCR 单元格。格式契约（manifest schema 2.1 全字段/清洁 MD/图样保真呈现规则/page-transcribe schema 1.1/接缝 affordance/完整性交叉校验/hint 9+1 词表/term 种子）见 `assets/tpl-extract-pack.md`；解析边界与许可见 `references/parsing-limits.md`（①-⑱编号稳定）；**ingest→S1 接缝契约唯一接口权威**见 `../ontology-model/references/s1-handoff-contract.md`（五类 affordance + S1 消费协议）。

## 四、环境与目录约定

**依赖**：python3（3.9+）+ pypdf + **pypdfium2** + python-docx + openpyxl + python-pptx + Pillow（见套件 `requirements.txt`，精确钉住——输出字节稳定性版本敏感，升级须重跑双跑确定性）。**pypdfium2 安装须 `--only-binary=:all:`**（旧 pip 选 sdist 会触发 GitHub 下载 pdfium 二进制超时；wheel 自带二进制）。**LibreOffice 可选**（office→PDF 全视觉渲染增强，`brew install --cask libreoffice`，~700MB；无则 office 退 substrate-only 纯 pip 主路径仍工作）。`--no-office-render` 即使装了 LibreOffice 也强制 office substrate-only canonical 档（纯 pip 确定性，渲染层非 canonical〔limits ⑪〕；验收电池 T14 用此档保证环境无关）。**懒 import**：缺库时 `--help`/契约错仍可用，`ingest parse` 缺所需库 exit2+pip 提示，不阻塞 model/review/simulate。无 Java/node 硬依赖。

**许可纯净**：六直行 pip 依赖全 MIT/BSD/Apache（pypdf BSD-3 / pypdfium2 BSD-3 OR Apache-2.0 / docx MIT / openpyxl MIT / pptx MIT / Pillow MIT-CMU），传递依赖全链无 copyleft；LibreOffice MPL-2.0 独立子进程不感染 MIT（见套件 `THIRD-PARTY-LICENSES.md`）。**fitz/PyMuPDF 零代码路径**（AGPL/Artifex 商业双许可，pypdfium2 替代渲染）；poppler/tesseract/本地 VLM（MinerU AGPL/Marker GPL）不引入。

**工作目录**：默认 `cwd/萃取原料包/<doc_id>/`（不进 skill 目录、不覆盖权威）；真实业务资料必须落受控 run 目录（I0 确认）。**批量 doc_id 碰撞**：同 stem 不同格式会碰撞→exit2，须 distinct 文件名或逐文件 --doc-id。

**敏感双轨**（对齐 ontology-model `references/sensitivity-rules.md`）：

| 轨道 | 前提 | 产物去向 |
|---|---|---|
| 真实业务（受控） | 输出只写受控目录（不进版本控制/不进入对外分发通道）；产物不外发 | 仅 run 目录受控区内部流转 |
| 虚构通用 | 配例一律虚构中性 | 对外分发产物（examples/demo）一律用此轨 |

**照录不脱敏**：解析层保真转录（阈值照录），脱敏在 model S1→S2；本层只做登记位（sensitivity.level + 节级商务参数/个人信息 flag）。**attachments 二进制不进主会话上下文**（vision agent 直接 Read 图文件）。

**确定性**：canonical 准备态包零时间戳/零随机 id/全排序；PDF→PNG 渲染双跑字节等（pypdfium2 实证）；源 sha256 前后断言；realpath 碰撞守卫；再解析守卫护转录层。契约=同源字节→同包字节（Office 保存字节跨次不稳是源件属性非解析器缺陷）。LibreOffice 渲染若启用可能嵌时间戳→登记非 canonical 中间层。

**成本（质量优先 tradeoff）**：每视觉单元一次 LLM 整页转录，成本高于纯机械提取（质量优先取舍）；批处理优化为后续项。

## 五、边界（不做）

- 本体建模（ontology-model 管；本 skill 只产进料，hint 加速 S1 不替代萃取判断）
- 语义理解/萃取（S1 管；本层只还原结构+保真内容，不理解内容本身）
- 审阅批注（ontology-review 管）/ 模拟验证（ontology-simulate 管）
- 脱敏（model S1→S2 管；本层照录不脱敏）
- 完整四通道（talk ASR/code SQL DDL/diagram/专有 DB 连接器）= 后续扩展位（见 parsing-limits §六，无排期承诺）

## 六、目录结构（skill 根）

```
ontology-ingest/
├── SKILL.md                  # I0-I3 执行契约 + IG1 + 铁律（LLM 编排入口）
├── README.md                 # 本文件（人类手册）
├── CHANGELOG.md              # 版本历史（执行不依赖）
├── references/               # parsing-limits.md（解析边界①-⑱/许可/确定性/image-only 边界/成本/图样保真+接缝元数据+原生矢量边界，迭代唯一入口）
├── assets/                   # tpl-extract-pack.md（pack schema 2.1 + page-transcribe schema 1.1 + 清洁 MD + 图样保真 + 接缝 affordance + 交叉校验）
│                             # / prompt-vision-extract.md（page-transcribe 主模式 + image-extract 兼容）
└── scripts/                  # parse_documents.py（I1 机械层 CLI：渲染+inventory+substrate，懒 import）
                              # / assemble_pack.py（I3 机械组装 CLI：manifest 按序→每源件单一合并 md，保证按序/不丢弃，自校验）
```

配套 agent（Claude Code 形态，部署于 `.claude/agents/`）：ontology-vision-extractor（I2，只读，无 model 字段，平台中立模型由编排指定，page-transcribe 双模式）。平台中立纪律与适配说明见套件 `agents/README.md`。

## 七、姊妹 skill

- **ontology-model**：下游消费原料包（S1 入口 (a)）；**接缝契约唯一接口权威=`references/s1-handoff-contract.md`**（五类 affordance + S1 消费协议）、hint 词表对照=`references/structured-input-mapping.md`、敏感口径=`references/sensitivity-rules.md`（只读不改）
- **ontology-review** / **ontology-simulate**：同套件审阅层 / 模拟层（进料→建模→审阅→模拟管线序）

## English Summary

**ontology-ingest** is the heterogeneous-document fidelity intake front-end for the ontology suite: it turns PDF / image / Excel / Word / PPT business materials into a unified "extraction feed pack" (clean faithful Markdown + canonical `manifest.json` + `attachments/`) consumable by ontology-model S1. Its sole goal is **parsing quality (completeness / accuracy / structure)** — reconstruct the original layout and preserve all content faithfully, without interpreting the content itself (semantic extraction belongs to S1). **Architecture**: LLM whole-page layout-aware transcription is primary (every visual unit must pass), with mechanical rendering / completeness inventory / native substrate / cross-check as guardrails. The mechanical layer (I1, deterministic pure-pip CLI: pypdf / pypdfium2 / python-docx / openpyxl / python-pptx / Pillow, optional LibreOffice subprocess) renders each page to PNG, builds a completeness inventory (text-layer / cells / paragraphs / shape text), and extracts a precise native substrate (DOCX structured md / XLSX cell grid / PPTX positional substrate with bounding boxes) — it produces a *prepared* pack, not final prose. The read-only `ontology-vision-extractor` agent (I2, page-transcribe mode) reconstructs clean layout-faithful markdown from each rendered image (using substrate text verbatim where available, never re-OCRing cells), with zero fabrication (ambiguous regions register candidate readings), watermark/decoration removal, and multi-column partitioning. The main session (I3) runs mechanical cross-checks (inventory coverage to catch dropped text, clean-md assertion, mechanical-field sha untouched) and registers uncertain readings for human review. The invariant: **no unit is silently routed mechanical-only past the LLM**. Canonical prepared packs carry zero timestamps and are byte-deterministic (PDF→PNG render double-run verified); transcription back-fill is explicitly non-canonical. Iron rules: zero write-back (source sha256 asserted), transcribe-don't-redact (redaction at S1→S2), fitz/PyMuPDF zero code path (pypdfium2 replaces it; AGPL contamination risk for the MIT suite), clean md (machine metadata lives only in the manifest). IG1 human gate personally confirms fidelity (visual review of image-only pages + uncertain readings) before feeding model S1. **Seam contract**: the quality goal is **extraction-ready fidelity** — fidelity that S1 can actually consume. ingest output and model S1 consumption are co-designed against a single interface authority (`ontology-model/references/s1-handoff-contract.md`), producing five affordances: a form dimension `unit_type` (orthogonal to the content-feature `semantic_hint`), diagram-faithful presentation (flow/UI/architecture diagrams embed the original image + verbatim in-image text, leaving topology interpretation to S1 multimodal Read rather than flattening to prose), confidence metadata `verification_status` (substrate-exact / render-transcribed / image-only-transcribed), precise personal-info regions `personal_info_regions` (an S2 redaction checklist, still register-don't-redact), and provenance bridging `md_heading` (source→section→sentence→TTL annotation chain). Form classification is **fail-safe**: the mechanical layer unconditionally preserves every image, so `unit_type` drives only clean-md presentation, never image existence — a misclassification never causes irreversible content loss. **Mechanical assembly**: the final clean Markdown is assembled by a deterministic script (`assemble_pack.py`, I3) — one merged `<doc_id>.md` per source document ("one document, one parsed file" form), concatenated in manifest section order with mechanical guarantees of order-preservation / no-content-loss / image-embed conservation (asserted by self-checks, not by LLM merge discipline, which risks attention drop / context truncation / silent rewriting and does not scale to large document sets). Merging is a deterministic structural operation (iron rule 4: scripts do mechanical work, LLMs do semantic work); the LLM transcribes each unit, the script assembles. Execution contract: `SKILL.md`.
