# 萃取原料包契约（pack schema 2.1 + page-transcribe schema 1.1）

> ontology-ingest「保真进料」产物「萃取原料包」的格式权威 + I2 整页布局感知转录回填契约。
> **架构（LLM 主路径 + 机械护栏）**：**LLM 整页布局感知转录 primary（每个视觉单元必过）+ 机械渲染/完整性 inventory/原生 substrate/交叉校验护栏**。不变量：任何单元都不被静默路由 mechanical-only 跳过 LLM。
> **接缝契约（萃取就绪的保真）**：质量目标=「萃取就绪的保真」——五类 S1 可消费 affordance（形态维 unit_type / 图样保真呈现 / 置信度 verification_status / 个人信息精确位 personal_info_regions / 溯源映射 md_heading）。接口权威=`../../ontology-model/references/s1-handoff-contract.md`（ingest 只读引用，两侧共同遵守）。
> **子协议版本独立登记不联动**（照 model patch schema 1.0 / shapes schema 1.0 先例）：pack schema **2.1** / page-transcribe schema **1.1**（additive 字段向后兼容），不随 skill 版本联动。
> 消费方：`scripts/parse_documents.py`（I1 机械层产准备态包）、ontology-vision-extractor agent（I2 整页转录）、主会话（I2 回填 + 完整性交叉校验）、ontology-model S1（入口 (a) 按 s1-handoff-contract 消费清洁 md + manifest 元数据 + 图样原图）。
> 纪律：本契约只登记格式与判据，零业务内容；配例一律虚构中性（票据贴现示例载体）。

---

## 一、输出结构

默认落 `cwd/萃取原料包/<doc_id>/`（**不进 skill 目录、不覆盖权威、不进 run 目录除非 I0 指定受控 run**）。批量输入时每文档独立包子目录（**同 stem 不同格式会 doc_id 碰撞→再解析守卫 exit 2，批量须 distinct 文件名或 --doc-id**）。

```text
萃取原料包/<doc_id>/
├── <doc_id>.md        # 清洁 markdown（§三）：I1 准备态=substrate/图嵌入脚手架；I2 逐单元转录回填 manifest；I3 机械组装（assemble_pack.py）每源件单一合并 md
├── manifest.json      # canonical 结构化清单（§二，零时间戳，全字段参与确定性断言）
└── attachments/       # 图像二进制同名溯源：PDF 每页渲染 PNG / office 渲染页图（LibreOffice 可选）/ 原图副本 / 内嵌图导出
                       #   每图 sha256 登记入 manifest；渲染/提取失败如实登记（不静默）
```

- `doc_id`：文件名 stem 净化（去路径/去扩展名/空白→下划线）或 `--doc-id` 显式指定。
- **attachments 二进制不进主会话上下文**——vision agent 直接 Read 图文件（二进制不过模型）。
- **机械层三职责**（不再产最终正文）：①渲染（每单元→页图，无静默跳过）②inventory（完整性 ground truth）③substrate（原生结构化精确文本）。最终清洁 md = I2 LLM 逐单元转录（语义层）+ **I3 机械组装**（assemble_pack.py 按 manifest 序拼接每源件单一 `<doc_id>.md`，保证按序/不丢弃，结构层）。**一份源件一份解析文档**（非逐页单拆）。

## 二、manifest schema 2.1（canonical，零时间戳）

```json
{
  "schema_version": "2.1",
  "pack_id": "P-<sha256(canonical({sources:[{name,sha256}]}))[:12]>",
  "doc_id": "<stem 净化|--doc-id>",
  "source": {
    "name": "<basename，禁绝对路径>",
    "source_type": "pdf|image|excel|word|ppt",
    "sha256": "<64hex>",
    "bytes": 0,
    "doc_date": "<ISO|null>",
    "doc_date_source": "metadata|exif|unknown",
    "authority": "正式制度|专家口述|二手转述|未登记"
  },
  "parser": {
    "name": "parse_documents.py", "script_version": "2.0",
    "library": "<主解析库==版本 + pypdfium2==版本（PDF）>",
    "render_scale": 2.0, "libreoffice_render": false
  },
  "coverage": {
    "units_total": 0, "units_prepared": 0, "units_transcribed": 0,
    "locator_range": "p.1-5|sheet:费率表|slide:1-3|image|para"
  },
  "sections": [{
    "section_id": "s001",
    "heading": "…",
    "locator": {"kind": "page|sheet|slide|para|image", "page": 3, "sheet": "费率表", "cell": "A1:B7", "slide": 2},
    "extraction": "prepared|transcribed",
    "rendered_image": {"name": "xxx.png", "sha256": "<64hex>", "bytes": 0},
    "substrate": {"text": "…原生结构化精确文本…", "text_sha256": "<64hex>"},
    "inventory": {"kind": "pdf-text-layer|xlsx-cell|docx-paragraph|pptx-shape|image", "count": 0, "items_sha256": "<64hex>", "items": ["…"]},
    "pictures": [{"name": "xxx.png", "sha256": "<64hex>", "bytes": 0}],
    "semantic_hint": ["定义|关联|判断|流程|权限|术语|例外|清单参数|数值参数|需识图"],
    "sensitive_flags": ["商务参数|个人信息"],
    "unit_type": "text-prose|table|flow-diagram|ui-interaction|architecture-diagram|chart|decoration|mixed|other|null（I2 填）",
    "verification_status": "substrate-exact|render-transcribed|image-only-transcribed|null（I2 填）",
    "personal_info_regions": [{"region": "…", "kind": "人名|证件号|联系方式|机构名歧义", "reading": "照录原文"}],
    "md_heading": "…LLM 实际清洁 md 标题|null（I2 填，溯源桥接）",
    "text": null,
    "text_sha256": null,
    "transcribe_meta": null
  }],
  "term_candidates": [{"term": "…", "freq": 3, "source": "heading|table-header|substrate-heading", "locators": ["s001"]}],
  "gaps": [{
    "gap_id": "g001",
    "kind": "image-only-page|formula-no-cache|embedded-object|embedded-image|encrypted|missing-section|uncertain-reading|inventory-miss",
    "locator": {}, "note": "…", "resolution": "pending|resolved", "resolved_by": null
  }],
  "conflicts": [],
  "attachments": [{"name": "xxx.png", "sha256": "<64hex>", "bytes": 0}],
  "sensitivity": {"level": "真实业务|虚构通用|未登记", "note": "照录不脱敏；脱敏在 S1→S2（sensitivity-rules §四）"}
}
```

> 上例 `rendered_image`/`substrate`/`inventory` 为展示全字段；实际每节按格式取 null 或对象（PDF 页=rendered_image+inventory，substrate=null；DOCX/XLSX/PPTX=substrate+inventory，rendered_image 仅 LibreOffice 可用时非 null；图片=rendered_image，inventory items=[]）。

### 字段裁定

| 字段 | 裁定 |
|---|---|
| `pack_id` | 内容哈希（T13 patch_id 先例）：`P-`+sha256(canonical({sources:[{name,sha256}]}))[:12]。同源同参→同 id→双跑字节等 |
| `source.name` | **basename**（禁绝对路径）；`source.sha256` 全 64 位（零回写基准） |
| `source.doc_date` | 取文档元数据（docx core_properties / PDF metadata / 图片 EXIF），标 `doc_date_source`；**模板默认值警示**（docx 默认 2013 假日期→gap 登记可信度低）；无→null+unknown |
| `source.authority` | 来自 `--authority` flag（默认「未登记」）。可信源硬要求由 model S0 登记 + G1 强制，**包只承载登记位不裁定权威** |
| `parser.library` | 该文档主解析库==实证版本（PDF 含 pypdfium2 渲染库）；版本敏感（升级须重跑双跑确定性） |
| `parser.render_scale` | PDF 渲染 scale（默认 2.0≈144DPI）；`libreoffice_render`=是否探测到 soffice（office 全视觉渲染增强开关，false=substrate-only） |
| `coverage.units_prepared` | 机械层就绪单元（render 或 substrate 备好，extraction=prepared）；`units_transcribed`=I2 LLM 转录完成单元（extraction=transcribed）。**准备态包 units_transcribed=0** |
| `sections[].extraction` | `prepared`（机械层就绪，待 I2 转录）/ `transcribed`（I2 回填后）。**canonical 断言只约束准备态包**（全 prepared）；transcribed 回填后包显式非 canonical。**无 mechanical-only 终态——每单元都待 LLM 转录** |
| `sections[].rendered_image` | 该单元渲染页图（PDF 每页/office LibreOffice 页图/图片原图）：name/sha256/bytes，引用 attachments/。无渲染（DOCX/XLSX/PPTX substrate-only）=null |
| `sections[].substrate` | 原生结构化精确文本（DOCX 结构化 md/XLSX 单元格网格/PPTX 位置 substrate）：text+text_sha256。**直抽比 OCR 更准**——LLM 在此做结构重建非重新 OCR。无 substrate（PDF/图片）=null |
| `sections[].inventory` | 完整性 ground truth（交叉校验防 LLM 漏字）：kind/count/items_sha256/items。PDF 文本层行/XLSX 非空单元格/DOCX 段落+表格/PPTX shape 文本+备注。**image-only 页 items=[]（诚实边界：机械无法比对图内容漏转录，靠整页渲染呈现+IG1 目视）** |
| `sections[].pictures` | 该单元内嵌图导出（DOCX word/media/PPTX 图片/XLSX 嵌入图）：name/sha256/bytes，需 I2 转录。无=[] |
| `sections[].text` | I2 前=null；I2 后=LLM 清洁布局保真转录 md。`text_sha256`=sha256(text)（转录锚）；null 节 text_sha256=null |
| `sections[].transcribe_meta` | I2 回填后=`{agent, model_alias, backfilled_at, transcribe_sha256}`；回填前=null。**时间戳只在此层出现**（canonical 包零时间戳） |
| `sections[].unit_type` | **形态维**（s1-handoff-contract §一）：text-prose/table/flow-diagram/ui-interaction/architecture-diagram/chart/decoration/mixed/other。与 semantic_hint（内容特征）**正交**。I2 LLM 转录副产品（机械分不了形态）；准备态=null。**fail-safe**：分类只驱动清洁 md 呈现，机械无条件保图，误判不丢内容（§1.2） |
| `sections[].verification_status` | **置信度元数据**（s1-handoff-contract §三）：substrate-exact（机械精确底）/render-transcribed（渲染+inventory 交叉校验）/image-only-transcribed（无 ground truth，IG1 人核兜底）。I2 按 substrate_used+inventory.items 设；准备态=null。S1/G1 消费校准怀疑度 |
| `sections[].personal_info_regions` | **个人信息精确位**（s1-handoff-contract §四）：[{region, kind, reading}]，照录不脱敏（登记位非脱敏），S2 精确脱敏 checklist。准备态=[]；水印个人标识进 not_transcribed 不进此字段 |
| `sections[].md_heading` | **溯源桥接**（s1-handoff-contract §五）：LLM 实际清洁 md 语义标题（区别于机械 heading，PDF 机械 heading=页号）。I2 填；准备态=null。I3 机械组装（assemble_pack.py）按 sections 序拼接，节序↔manifest 一一对应由脚本构造保证 |
| `term_candidates` | **结构种子**（§四）：章节标题串+表格首行单元格串+substrate ATX 标题串，freq=全包精确匹配计数，source 标来源。**不做中文分词**（S1「≥3 次名词强制登记」是主会话职责，脚本不越权萃取） |
| `gaps` | gap 是产物不是失败（exit 0 仍登记）；kind 枚举见上；`uncertain-reading`=I2 识别存疑候选读法（IG1 人核）；`inventory-miss`=完整性交叉校验缺失项；resolution pending→resolved |
| `conflicts` | **保留空位**：跨文档冲突是 S1 主会话职责，单文档解析不可检出 |
| `attachments` | 图像二进制溯源清单（按 name 排序）：name/sha256/bytes。渲染页图+内嵌图+原图副本；sha256 是 I2 source_sha256 校验依据 |
| `sensitivity.level` | 来自 `--sensitivity` flag（默认「未登记」）；**照录不脱敏**（§七纪律） |

## 三、清洁 MD 规范（机器元数据全入 manifest，正文无机器锚）

**核心纪律**：机器元数据（locator/extraction/sha/hint/sensitive）**全部移入 manifest.json**，md 正文＝**清洁 markdown**，下游 S1 消费无机器锚污染。

- **I1 准备态 md（脚手架，非最终）**：每单元 substrate（若有，DOCX/XLSX/PPTX 精确文本）+ 渲染图嵌入 `![[attachments/xxx.png]]`（若有）+ 内嵌图嵌入。**无 `## [s001]` 锚、无 `<!-- locator:... -->`、无 extraction/sensitive 锚**。
- **I2 后最终 md（I3 机械脚本 `assemble_pack.py` 从 manifest.sections[].text 按序组装，非 LLM 合并）**：每源件单一 `<doc_id>.md`（落 pack 目录，与 attachments/ 同级），清洁布局保真 markdown——层级标题/md 表格/编号列表/`<br>` 多行单元格/多列分区/识别存疑节注记。**合并形态**（一份资料一份文档）：
  - **唯一 H1 = doc_id**（文档标题）；各单元标题层级**压实为 H2 起连续**（单元内唯一层级集合→从 H2 连续映射，保内部相对结构、去层级跳空，代码 fence 内不动）。
  - 单元间 **`---` 分页节**（清洁分隔，非机器锚）；**空单元**（text 空）诚实占位「`## md_heading` + （空单元：无视觉内容，未转录）」。
  - **图嵌规范化**：转录中间态 `![[attachments/x]]` → 最终 **`![[x]]` 裸文件名**（Obsidian 全局文件名解析约定；附件名含 doc_id 前缀全局唯一）。
  - **机械保证**（脚本自校验 exit 1 若失败）：逐单元内容完备且按 manifest 序拼接（归一化子串单调游标，不丢弃）/ 图嵌计数守恒 / 清洁无机器锚 / source.sha 零回写。**按序/不丢弃是机械断言保证，不靠 LLM 合并纪律**（铁律 4）。
- **图样保真呈现规则**（s1-handoff-contract §二，按 unit_type 分派）：
  - **图样类**（flow-diagram/ui-interaction/architecture-diagram/chart）＝`![[attachments/原图.png]]` **嵌原图** + **「图内文字照录」节**（节点/箭头条件/标注/泳道标题/轴标签，带轻量区域归属）。**不做拓扑解读**（不拍平成有序步骤叙事——拓扑语义留 S1 Read 原图提炼）。原图取最高保真载体（内嵌图原件优先，否则整页渲染图）。
  - **文字类**（text-prose/table）＝文本转录，**不嵌原图**（清洁 md 对 RAG 友好；原图仍在 attachments 兜底，S1 需要可回看）。
  - **装饰**（decoration）＝not_transcribed（登记 reason），不混入正文。
  - **混合/未知**（mixed/other）＝文字部分转录 + 图样部分嵌图；未知保图保守。
  - 图样拓扑语义只在 S1 多模态 Read 原图可得，纯文本/RAG 消费只拿图内文字标签（下游须知）。
- **阈值/数值照录不模糊化不取整**（mapping §二第3步）；商务参数/个人信息**只在 manifest.sensitive_flags + personal_info_regions 登记**，md 正文不标机器锚。
- 换行 LF；**section↔md 映射靠 md_heading↔section_id**（s1-handoff-contract §五）：I2 回填时每节 md_heading（LLM 语义标题，区别于 PDF 机械 heading=页号）落 manifest；**I3 机械组装按 manifest sections 序拼接，节序↔manifest 一一对应由脚本构造保证**（非 LLM 合并，无静默错位/拆分风险）。
- **清洁 md 断言**（I3 机械组装脚本自校验）：正文 grep `locator:|extraction:|## \[s|<!--|text_sha256|sensitive_flags` 零命中（图嵌入 `![[…]]` 除外——最终态为裸文件名）。

## 四、semantic_hint 词表（9 类内容特征 + 需识图，对齐 model structured-input-mapping §二第1步）

> **hint 只提示内容特征，不预判本体语义**；机械关键词启发式多标签、可为空 []、永不权威。S1' 第1步逐节复核，hint 不替代识别。本表是对照副本，权威在 model `references/structured-input-mapping.md` §二第1步。
> **unit_type 形态维与 semantic_hint 正交**（s1-handoff-contract §一）：semantic_hint 回答「什么内容特征」（流程/规则/参数…），unit_type 回答「什么视觉形态」（流程图/表格/正文…）。一张流程图 unit_type=flow-diagram + semantic_hint=流程。unit_type 由 I2 LLM 转录产出（机械只产 semantic_hint 启发式），词表与 fail-safe 分类原则见 s1-handoff-contract §一。S1 按 unit_type 分派萃取维（图样类 Read 原图→任务维）。

| hint | 内容特征判据（机械启发式关键词示例） | mapping 语义类别 → 描述集目标分节 |
|---|---|---|
| 定义 | 「是指/定义为/包括/分为/属性/标识/编号/类型」 | 对象与概念 → 1 对象描述类 |
| 关联 | 「关联/属于/包含/对应/方向/基数/一对多/上级/下级」 | 对象关系 → 1 对象描述类（1.3 关联位） |
| 判断 | 「若/如果/则/须/不得/禁止/阈值/不低于/不超过/条件」 | 控制规则 → 4 控制规则类（主战场） |
| 流程 | 「步骤/流程/先…后/操作/通道/环节/顺序」 | 任务与流程 → 5 流程活动类【扩展位】 |
| 权限 | 「可自主/须确认/授权/审批/权限/禁止操作」 | 权限管控 → 6 权限管控类【扩展位】 |
| 术语 | 「又称/俗称/同义/口语/QA/问答/简称」 | 术语 → 3 术语类 |
| 例外 | 「除外/特殊/例外/不适用/边界/跨…口径」 | 例外与边界 → 2 分层约束类 / 4 控制规则类 |
| 清单参数 | 大批量枚举值/区域列表/日期表（表格多行枚举） | 数据层候选 → **不进本体**（登记接口契约） |
| 数值参数 | 「费率/额度/分值/利率/金额/比例」+数值 | 敏感登记 → 只登记属性位与结构语义 |
| 需识图 | 图片/扫描页（rendered_image 非 null，待 I2 整页转录） | I2 转录后再判内容特征 |

**term_candidates 结构种子算法**：收集所有 section.heading 串 + 所有表格首行单元格串 + 所有 substrate ATX 标题串（`^#{1,6} ` 行，DOCX 标题在 substrate）→ 去重 → 对每串计「全包精确匹配出现次数」（freq）→ 标 source（heading|table-header|substrate-heading）+ locators（出现节 id）。高频标题/表头是高信号名词短语候选，纯机械零 NLP；候选只是 S1 核对底稿不是裁定。

## 五、page-transcribe schema 1.1（I2 agent 整页布局感知转录，主会话校验后回填）

> **模式**：page-transcribe **1.1**（整页/整幻灯片布局感知；含 unit_type 形态维 + personal_info_regions 精确位 + md_heading 溯源桥接，s1-handoff-contract）。agent 双模式兼容（image-extract 模式保留向后兼容，page-transcribe 为主路径）。

```json
{
  "schema_version": "1.1",
  "mode": "page-transcribe",
  "doc_id": "…",
  "section_id": "s001",
  "source_image": "attachments/xxx.png|null（substrate-only 单元无渲染图）",
  "source_sha256": "<64hex，须==manifest 对应 rendered_image/pictures sha>|null",
  "substrate_used": true,
  "transcription": "清洁布局保真 md（层级标题/md 表格/编号列表/<br>多行/多列分区；图样类嵌原图+图内文字照录；阈值照录含单位；无机器锚）",
  "unit_type": "text-prose|table|flow-diagram|ui-interaction|architecture-diagram|chart|decoration|mixed|other",
  "md_heading": "…本单元清洁 md 实际语义标题（溯源桥接，s1-handoff-contract §五）",
  "semantic_hint": ["…9+1 词表"],
  "uncertain": [{"region": "…", "issue": "模糊|遮挡|歧义|OCR误读", "candidate_readings": ["候选读法1", "候选读法2"]}],
  "not_transcribed": [{"region": "…", "reason": "装饰图|二维码|水印个人标识|纯背景"}],
  "personal_info_present": false,
  "personal_info_regions": [{"region": "…", "kind": "人名|证件号|联系方式|机构名歧义", "reading": "照录原文"}],
  "confidence_note": "…"
}
```

**转录纪律**（prompt-vision-extract.md page-transcribe 模式权威）：整页布局感知（读渲染图重建视觉结构，非逐字堆砌）；substrate 存在时**文本取 substrate 精确值**（避免 OCR 误差），LLM 只做结构重建（语义分组/层级/多行保全）；多列按 x 坐标分区；水印/装饰/二维码识别不转录（not_transcribed）；模糊处登记候选读法**绝不猜测定值**（uncertain）；个人标识照录但标记（personal_info_present + personal_info_regions 精确位，脱敏在 S1→S2）；**形态分类 fail-safe**（unit_type 只驱动呈现，拿不准保图保守，s1-handoff-contract §1.2）；**图样保真**（flow-diagram/ui-interaction/architecture-diagram/chart 嵌原图+图内文字照录，拓扑解读留 S1，不拍平成有序步骤）。

**主会话回填序列**（I2，SKILL.md 登记）：
1. 校验 schema_version==1.1 + mode==page-transcribe + section_id 存在且 extraction=="prepared" + source_sha256 匹配 manifest rendered_image/pictures sha（substrate-only 单元 source_image=null 跳过 sha 校验）+ unit_type ∈ 词表（s1-handoff-contract §1.1）。
2. text=transcription（清洁 md）、extraction="transcribed"、transcribe_meta 落位（agent/model_alias/backfilled_at/transcribe_sha256）、text_sha256=sha256(text)；**unit_type/md_heading/personal_info_regions 落位**（agent 产出）；**verification_status 主会话设**（substrate_used→substrate-exact；render+inventory.items 非空→render-transcribed；inventory.items=[]→image-only-transcribed）。
3. **完整性交叉校验**（§五.1）：inventory.items 逐项归一化后须出现在 transcription；缺失→gap（kind=inventory-miss，pending IG1）或重转录。substrate 单元另核 substrate.text 关键 token 覆盖。
4. **机械层零触碰**——rendered_image/substrate/inventory/pictures 的 sha 锚复核未被改动（LLM 只填 text/transcribe_meta，不改机械字段）。
5. uncertain 保留进 gaps（kind=uncertain-reading，note 挂候选读法），IG1 呈报人核。
6. not_transcribed 登记（装饰/水印剔除留痕）；personal_info_present=true→sensitive_flags 追加「个人信息」+ **personal_info_regions 落位**（S2 精确脱敏 checklist，s1-handoff-contract §四）。
7. 回填计数如实呈报（失败退占位+如实报计数）；**回填后包显式非 canonical**；I2 只逐单元回填 manifest.sections[].text + md_heading，**最终清洁合并 md 由 I3 机械脚本 `assemble_pack.py` 按 manifest sections 序组装**（§三合并形态；节序↔manifest 一一对应、按序/不丢弃由脚本构造+自校验机械保证，非 LLM 合并）。

### 五.1 完整性交叉校验断言（机械，防 LLM 漏字）

- **inventory 覆盖**：对每节 inventory.items 每项，归一化后检查是否为 transcription 归一化文本的子串；缺失项→gap（inventory-miss，locator 挂节，note 挂缺失 token）。**归一化配方（成文，防误剥致伪报）**：NFKC + 小写 → **只剥已知 HTML 标签**（`<br>` 换行 + 内联 `b|i|u|em|strong|sub|sup|p|span`，标签剥但内容留）→ 保留 `数字 / 拉丁字母 / 中文 / % / 小数点`（剥其余标点空白）。**禁用宽泛 `<[^>]+>` 剥标签**——PDF 内容性比较运算符（如 `<50万` 的 `<`）会被误剥致伪报缺失。保留拉丁字母比纯 CJK+数字更严（能抓漏掉的产品代码/英文词）。**判内容完备性非语义准确**（运算符对错/读法歧义留 IG1 人核，inventory 覆盖只判 token 在场）。
- **substrate 覆盖**（DOCX/XLSX/PPTX）：substrate.text 的段落/单元格关键 token 同法核对（substrate 是精确文本 ground truth，LLM 结构重建不得丢内容）。
- **诚实边界**：image-only 页（inventory.items=[]）机械无法比对图内容漏转录——保证＝**整页渲染图必呈现给 LLM（无静默跳过，主修复）+ IG1 用户目视复核**（对照源件）。可选 macOS Vision OCR 提供图文字 inventory assist（平台特定，OCR 有误读，非硬保证，登记为 assist 非 ground truth）。
- 交叉校验是**护栏非权威**：缺失登记 gap 供人核，不自动改 LLM 转录（避免机械误判覆盖正确转录）；IG1 用户裁定。

## 六、exit 三态（parse_documents.py）

| exit | 含义 | 触发 |
|---|---|---|
| **0** | 全部准备成功 | gap 登记不阻塞（gap 是产物不是失败）；image-only 页/内嵌图正常登记待 I2 |
| **1** | 语义阻断（integrity） | 零回写断言失败（源 sha before≠after） |
| **2** | 输入错 | 缺文件/不支持扩展名/坏文件解析异常/输出==源 realpath/已有非空包目录无 --force（含同 stem 碰撞）/缺解析渲染库（懒 import ImportError→pip 提示）/AES DependencyError/密码错 |

## 七、纪律（不可绕过）

1. **零时间戳**：canonical 准备态包（MD+manifest）内任何 now()/mtime/随机 id 都是确定性漏洞；解析时刻由主会话记 run-manifest（I0 开卷带日期）。时间戳只在 transcribe_meta（回填后非 canonical 层）。
2. **零回写**：源文档 sha256 前后断言（before==after，否则 exit 1）；输出 realpath 碰撞守卫（输出不得等于任何输入，exit 2）。
3. **再解析守卫**：输出子目录已存在且非空→exit 2（护 I2 转录回填层不被重解析冲掉）；`--force` 显式覆盖。
4. **照录不脱敏**：解析层保真转录（阈值照录不模糊化），脱敏在 model S1→S2（sensitivity-rules §四）；解析层只做登记位（sensitivity.level + 节级 sensitive_flags）。真实业务包必须受控 run 目录（I0 确认）。
5. **机械/LLM 分界反转但纪律保留**：I1 机械 CLI **不调 LLM**（产 canonical 准备态包）；I2 LLM 经**只读 agent** 整页转录（零臆造，模糊登记候选读法）；I3 交叉校验**机械**（inventory 覆盖断言）。分界不塌陷——机械不产最终正文，LLM 不改机械字段。
6. **不变量：无静默跳过**——任何视觉单元（PDF 页/幻灯片/图片/内嵌图）都渲染成图或备 substrate 交 I2 转录。**无 mechanical-only 误路由分支**（薄文本层+大图页不得静默丢失）。
7. **懒 import**：格式 handler 内导入解析/渲染库（顶层只标准库）——缺库时 --help/契约错仍工作，ingest parse 缺所需库 exit 2+pip 提示，不阻塞 model/review/simulate。
8. **确定性配方**：`json.dump(sort_keys=True, ensure_ascii=False, indent=1)`+尾换行；MD LF；sections/gaps/term_candidates/attachments 全排序；pack_id 内容哈希。**PDF→PNG 渲染双跑字节等**（pypdfium2 实证）；office substrate 确定性。**契约=同源字节→同包字节**（Office 保存字节跨次不稳是源件属性非解析器缺陷，fixture 一次生成解析两次）。LibreOffice 渲染若启用可能嵌时间戳→登记为非 canonical 中间层（渲染图 sha 登记，canonical 断言 scope 机械 inventory/substrate/manifest）。`--no-office-render` 强制 office substrate-only（禁 LibreOffice 渲染，parser.libreoffice_render=false）——纯 pip canonical 档，供测试环境无关化（CI 装 LibreOffice 亦同）与用户确定性控制。
9. **fitz/PyMuPDF 零代码路径**：PDF 渲染用 **pypdfium2**（BSD-3/Apache-2.0，MIT 兼容）；**不 import fitz**（AGPL-3.0/商业双许可，MIT 套件污染风险，详见 references/parsing-limits.md ⑨）。纯 pip 放宽为「pip + LibreOffice 子进程渲染（可选），质量优先」。
10. **清洁 md**：机器元数据全入 manifest，md 正文清洁 markdown（§三）；下游 S1 无机器锚污染。
11. **py3.9 兼容**：禁 match 语句 / `X|Y` 类型联合（CI 3.9 矩阵）。

## 八、虚构配例（票据贴现示例载体，中性）

输入 `票据贴现制度.docx`（虚构）→ 准备态包：
- manifest：schema_version=2.1，source_type=word，parser.libreoffice_render=false，sections=[{section_id:s001, heading:"票据定义", locator:{kind:para}, extraction:"prepared", rendered_image:null, substrate:{text:"# 票据定义\n\n票据是指…", text_sha256:…}, inventory:{kind:"docx-paragraph", items:["票据是指…"], count:1}, pictures:[], semantic_hint:["定义"], unit_type:null, verification_status:null, personal_info_regions:[], md_heading:null, text:null, transcribe_meta:null}]，term_candidates=[{term:"票据", freq:5, source:"heading"}]，gaps=[]。
- 准备态 MD（清洁脚手架）：`# 票据定义` + substrate 保真文本（无机器锚）。
- I2 整页转录（page-transcribe）→ transcription 清洁 md（LLM 复核结构）、extraction:"transcribed"、transcribe_meta 落位；unit_type:"text-prose"、md_heading:"票据定义"、personal_info_regions:[]（agent 产出），verification_status:"substrate-exact"（主会话按 substrate_used 设）；完整性交叉校验 inventory.items 覆盖 ✓。
- 扫描页 `票据样本.png` → sections=[{s001, heading:"票据样本", locator:{kind:image}, extraction:"prepared", rendered_image:{name:"票据样本.png", sha256:…}, substrate:null, inventory:{kind:"image", items:[], count:0}, semantic_hint:["需识图"], text:null}]，attachments/票据样本.png（sha 登记），gaps=[{kind:"image-only-page", note:"无文本层，靠整页渲染+IG1 目视"}]。I2 整页转录→extraction:"transcribed"，uncertain 候选读法进 gaps（uncertain-reading，IG1 人核）。
- **流程图页 `贴现流程.png`（图样保真，s1-handoff-contract §二/八）**：I2 转录→unit_type:"flow-diagram"，transcription=`![[attachments/贴现流程.png]]` + 「图内文字照录：节点『贴现申请』『背书核验』『放款登记』；箭头条件『背书连续』」（**不拍平成有序步骤**，拓扑留 S1 Read 原图）；verification_status:"image-only-transcribed"，md_heading:"贴现流程"，semantic_hint:["流程"]。S1 消费 Read 原图→任务维描述句（来源列挂 s003/image），S3 编译 TTL 挂 rdfs:isDefinedBy 源节。
- **含联系人页（个人信息精确位）**：personal_info_present:true，personal_info_regions:[{region:"摘要表·招标联系人行", kind:"人名", reading:"某先生"}]；S2 按 region 精确虚构替换（非全文猜）。

## 九、限制登记

格式解析边界、许可登记（pypdfium2/LibreOffice）、渲染确定性、image-only 完备性诚实边界、AES 加密、LLM 转录成本、图样保真二分与形态分类 fail-safe、接缝元数据等 → `references/parsing-limits.md`（编号稳定，迭代在该 reference 内发生，本契约不叠加条款）。

**ingest→S1 接缝契约**（形态维 unit_type / 图样保真呈现 / 置信度 verification_status / 个人信息精确位 personal_info_regions / 溯源映射 md_heading + S1 消费协议）→ `../../ontology-model/references/s1-handoff-contract.md`（接口权威，两侧共同遵守，ingest 只读引用）。
