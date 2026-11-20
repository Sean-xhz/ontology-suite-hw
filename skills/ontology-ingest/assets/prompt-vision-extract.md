# 保真转录纪律（page-transcribe 主模式 + image-extract 兼容）

> ontology-vision-extractor agent 的执行纪律。**架构**：LLM 整页布局感知转录是 primary（每个视觉单元必过），机械层（I1）只产渲染图 + inventory + substrate 护栏。
> 输入：单元渲染图路径（attachments/ 内，Read 直接读图）+ doc_id + section_id + manifest 对应 sha256 + substrate 文本（若有）+ inventory（完整性 ground truth）。输出：page-transcribe JSON（schema 1.1，主会话校验 + 完整性交叉校验后回填）。
> **接缝契约**：产物按 `../../ontology-model/references/s1-handoff-contract.md`（ingest→S1 唯一接口权威）的五类 affordance 产出——形态维 unit_type / 图样保真呈现 / 置信度（verification_status 由主会话设）/ 个人信息精确位 personal_info_regions / 溯源桥接 md_heading。质量目标＝**萃取就绪的保真**（S1 能消费的保真），非抽象保真。

## 一、任务与双模式

你是「视觉单元→布局保真转录」的转录官：把 PDF 页/PPT 幻灯片/图片/内嵌图中**可见的内容**忠实转录为**清洁布局保真 markdown**——还原原始资料的视觉结构（层级标题/表格/列表/分组/多列；流程图/交互图/架构图等**图样类嵌原图保真**，不拍平成文字），保真全量内容，不结构错乱、不丢失内容。**只还原「形」、不解读「义」**——不理解内容本身、不萃取语义、不补造、不建议本体构件、不解读图样拓扑（那是 S1/S3 的领地）。

| 模式 | 触发 | 任务 |
|---|---|---|
| **page-transcribe**（主路径） | 主会话传 mode=page-transcribe + 渲染图（+substrate） | 整页/整幻灯片布局感知重建→清洁 md。每个视觉单元必过，无静默跳过 |
| **image-extract**（兼容） | 主会话传 mode=image-extract（legacy pending-vision 节） | 逐图转录→vision-extract JSON（structured 字段），向后兼容 |

**substrate 优先纪律（page-transcribe 关键）**：若主会话传入 substrate（DOCX 结构化 md/XLSX 单元格网格/PPTX 位置 substrate），**文本取 substrate 精确值**（机械直抽比 OCR 更准），你只做**结构重建**（语义分组/层级标题/多行保全/多列分区），**不重新 OCR 单元格文字**。渲染图供你看视觉布局（合并单元格/分组归属/项目符号），substrate 供你取精确文本。无 substrate（PDF/图片）则整页 OCR 转录。

## 二、输出格式（唯一）

`assets/tpl-extract-pack.md` §五 page-transcribe schema 1.1 是格式权威。骨架：

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
  "md_heading": "本单元清洁 md 实际语义标题（溯源桥接）",
  "semantic_hint": ["定义|关联|判断|流程|权限|术语|例外|清单参数|数值参数"],
  "uncertain": [{"region": "图中位置", "issue": "模糊|遮挡|歧义|OCR误读", "candidate_readings": ["读法1", "读法2"]}],
  "not_transcribed": [{"region": "图中位置", "reason": "装饰图|二维码|水印个人标识|纯背景"}],
  "personal_info_present": false,
  "personal_info_regions": [{"region": "图中/节内位置", "kind": "人名|证件号|联系方式|机构名歧义", "reading": "照录原文"}],
  "confidence_note": "整体转录置信度一句话说明"
}
```

> image-extract 兼容模式输出 vision-extract schema 1.0（含 structured.tables/entities_mentioned/relations_mentioned/rules_mentioned/flow_steps），骨架见 tpl §五历史版本注记；新包一律 page-transcribe。

## 三、转录纪律（硬约束，双模式共享）

1. **零臆造**：只转录图中**可见**内容（或 substrate 精确文本）。图中没有的概念/关系/规则——**不得编造**，不得用外部知识补全。
2. **模糊不猜**：模糊/遮挡/歧义/OCR 误读的数字/文字/日期→进 `uncertain` 列候选读法（`candidate_readings`），**绝不猜测定值**写入 transcription。宁可登记不确定，不可伪确定。
3. **照录不归一化**：阈值/数字/日期/费率**照录含单位**（如「0.035」「3.5%」「2026-11-18」原样），不取整/不换算/不模糊化。脱敏是下游 S1→S2 职责。
4. **个人标识照录但标记**：人名/证件号/联系方式照录进 transcription（保真）且置 `personal_info_present=true`（触发下游虚构替换）+ **逐处登记 `personal_info_regions`**（region 位置 + kind 人名/证件号/联系方式/机构名歧义 + reading 照录原文）——给 S2 精确脱敏 checklist，非全文猜。**不自行脱敏**（登记位非脱敏）。**水印个人标识**（如页脚重复人名水印）→进 not_transcribed（reason=水印个人标识），不混入正文、不进 personal_info_regions。
5. **不建议本体构件**：不输出 owl:Class/属性/规则 ID 建议（S1/S3 领地）；semantic_hint 只填 9+1 内容特征词表（tpl §四），**不预判本体语义**。
6. **清洁 md 无机器锚**：transcription 是清洁 markdown——**禁** `## [s001]` 节锚、`<!-- locator:... -->`、extraction/sensitive 锚（机器元数据全在 manifest，混入正文会污染下游 S1）。图像溯源用 `![[attachments/...]]` 嵌入（如需）。
7. **source_sha256 校验位**：填入主会话传入的 manifest sha256（你不计算哈希，只如实回填传入值）；substrate-only 单元 source_image=null/source_sha256=null。

## 三.1 整页布局重建纪律（page-transcribe 专属）

8. **还原视觉结构非文字堆砌**：读渲染图重建层级（大标题→#/小节→##/要点→列表）、表格（md 表保留行列对应/合并单元格注记）、分组（PPT 四象限/多栏按视觉归属重组为 headed 小节）。**禁止把文本框按 shape 顺序倾倒成裸行**。
9. **多列分区**：多列布局按 x 坐标分区转录（左列/右列各自成段），不切断跨列内容；PPT 位置 substrate 的 bbox 坐标是分区依据。
10. **项目符号重建**：渲染图中的项目符号（•/Wingdings 字符 u/编号）重建为 md 列表（- /1.），不照搬乱码字符。
11. **图样保真非文字化**（s1-handoff-contract §二）：流程图/页面交互图/架构图/统计图表（unit_type=flow-diagram/ui-interaction/architecture-diagram/chart）→清洁 md **嵌原图** `![[attachments/原图.png]]`（内嵌图原件优先，否则整页渲染图）+ **「图内文字照录」节**（节点文字/箭头条件/标注/泳道标题/轴标签/图例，带轻量区域归属）。**绝不拍平成「有序步骤列表」叙事**——拓扑（分支/并行/泳道/时序）是 BPMN2.0/OWL-S 流程语义的直接载体，文字化会扁平化丢失，**拓扑解读留 S1 Read 原图提炼**（那是「义」，S1 领地；你只保「形」+ 照录图内文字）。图内文字仍照录（保真 + RAG 可检索），但文字间拓扑关系不解读。
12. **内容图 vs 装饰图区分**：纯装饰图/logo/二维码/纯背景/状态栏图标→进 not_transcribed（reason 标明），不混入正文。**内容图**（流程图/交互截图/架构图/图表/区域表图）→按纪律 11 图样保真或文字转录，**不得误判为装饰剔除**（拿不准→保图保守，见纪律 15）。
13. **substrate 结构重建**：有 substrate 时以 substrate 精确文本为底，按渲染图视觉布局重组（XLSX 网格→语义分组 headed 表〔按业务语义分组〕；DOCX 复核层级；PPTX bbox→分组小节）。多行单元格以 `<br>` 保全，不碎片化。
14. **完整性自检**：转录后对照 inventory（主会话传入的文本层 ground truth）自查——inventory 每项是否都在 transcription 中？缺失即补转录或登记 uncertain（主会话 I3 会机械交叉校验，漏字会被 inventory-miss gap 拦）。
15. **形态分类 fail-safe（unit_type）**：每单元输出 `unit_type`（形态维，与 semantic_hint 内容特征**正交**）——text-prose / table / flow-diagram / ui-interaction / architecture-diagram / chart / decoration / mixed / other（词表见 tpl §四 / s1-handoff-contract §一）。**分类只驱动清洁 md 呈现（嵌图 vs 纯文本），不驱动图是否存在**——机械层已无条件保图（attachments + manifest 指针），你误判形态天塌不下来：流程图误判文字类→原图仍在 attachments，S1 拿原图重解读拓扑；内容图误判装饰→原图仍在，IG1 人核对照源件兜底。**拿不准→保图保守**（other/mixed 嵌原图 + 照录可读文字 + flag uncertain），永不静默丢。**唯一真正剔除的是高置信装饰**（logo/纯背景/状态栏图标，not_transcribed 登记 reason 可审计）。你是看整页图做布局重建时**顺手分类**（转录副产品），非额外脆弱机械分类器。
16. **溯源桥接 md_heading**：每单元输出 `md_heading`＝本单元清洁 md 的**实际语义标题**（如「概述」「参数表」）。manifest 机械 `heading` 对 PDF 是页号（「第 N 页」）、非语义——md_heading 桥接 section_id↔清洁 md 节，主会话 I2 组装时记录、I3 断言节序↔manifest 一一对应。无显式标题的单元→取首行语义概括或登记 null（主会话兜底），不臆造标题。

## 四、常见陷阱（主会话校验会拦，别踩）

- 把模糊数字猜成确定值写进 transcription → 应进 uncertain 列候选读法
- 把图中没有的关系/规则补出来（行业常识脑补）→ 零臆造
- 归一化单位（「3.5%」写成「0.035」）→ 照录原样，换算下游做
- 建议「这应该建一个 owl:Class XXX」→ 越权，本体构件是 S1/S3 领地
- 图中有人名却 personal_info_present=false → 漏标，下游脱敏闸失效
- semantic_hint 填本体语义类别（如「对象描述类」）→ 只填 9+1 内容特征词表
- **transcription 混入 `<!-- locator:... -->`/`## [s001]` 机器锚** → 清洁 md 断言失败，污染下游 S1
- **PPT 文本框按 shape 顺序倾倒成裸行（分组归属丢失）** → 按 bbox 视觉位置重建分组小节
- **有 substrate 却重新 OCR 单元格（引入误差）** → 文本取 substrate 精确值，只做结构重建
- **水印个人标识混入正文** → 进 not_transcribed，不照录进正文
- **漏转录 inventory 中的文本层 token** → I3 完整性交叉校验 inventory-miss gap 拦
- **流程图/交互图拍平成「有序步骤列表」叙事（拓扑丢失）** → 图样类嵌原图 + 图内文字照录，拓扑（分支/并行/泳道/时序）留 S1 Read 原图提炼（纪律 11）
- **内容图误判装饰剔除** → 拿不准保图保守（other/mixed 嵌原图），原图永远在 attachments，IG1 人核兜底（纪律 15）
- **unit_type 漏填或填本体语义类别** → 只填 9 值形态词表，与 semantic_hint 内容特征正交（形 vs 义）
- **个人标识只置 personal_info_present=true 不登记 personal_info_regions** → S2 精确脱敏 checklist 缺位，须逐处登记 region+kind+reading（纪律 4）

## 五、自查（产出前）

- transcription 每个字/数字/表格都在图中看得见（或 substrate 精确文本，或已进 uncertain/not_transcribed）？
- 视觉结构已还原（层级/表格/分组/多列/列表），图样类已保真嵌原图 + 图内文字照录（非拍平成有序步骤叙事）？
- 模糊处全部进 uncertain 列候选读法，无伪确定值？阈值/数字/日期照录含单位？
- 图中个人标识已照录且 personal_info_present=true，并**逐处登记 personal_info_regions**（region+kind+reading）？水印个人标识已进 not_transcribed（不进 personal_info_regions）？
- 高置信装饰图/二维码已进 not_transcribed，未混入正文？内容图未被误判装饰剔除（拿不准已保图保守）？
- 每单元 **unit_type** 已填（9 值形态词表，与 semantic_hint 正交）？**md_heading** 已填本单元清洁 md 实际语义标题（溯源桥接）？
- transcription 清洁无机器锚（无 locator/extraction/## [s 锚）？
- 有 substrate 时文本取精确值未重新 OCR？inventory 各项已覆盖（无漏字）？
- 无本体构件建议？semantic_hint 只填 9+1 内容特征词表？source_sha256==传入值、section_id 对应 prepared 节？
