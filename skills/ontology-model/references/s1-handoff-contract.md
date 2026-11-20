# ingest → S1 接缝契约（萃取就绪的保真）

> **接口权威**：ontology-ingest 产物「萃取原料包」与 ontology-model S1 消费之间的**唯一接缝契约**。ingest 按本契约产出，S1 按本契约消费——两侧共同遵守，避免「ingest 产了 S1 不消费」的扔过墙式松耦合。
> **质量目标**：ingest 的唯一目标不是抽象「保真」，而是「**萃取就绪的保真**」——S1 能消费的保真才是 fitness-for-purpose。一份 S1 消费不了的保真产物价值为零。本契约把「保真」操作化为 S1 可消费的五类 affordance：形态维 / 图样保真呈现 / 置信度元数据 / 个人信息精确位 / 溯源映射。
> **归属与引用方向**：本契约归 model `references/`（与 structured-input-mapping / sensitivity-rules 同侧，S1 消费契约族）；ingest 只读引用（`../../ontology-model/references/s1-handoff-contract.md`），与 ingest 引用 model mapping/sensitivity 方向一致。
> **子协议版本独立登记不联动**：pack schema **2.1** / page-transcribe schema **1.1**（additive 字段，向后兼容）；不随 skill 版本联动。
> **纪律**：本契约只登记接口与判据，零业务内容；配例一律虚构中性（票据贴现示例载体）。

---

## 一、形态维 unit_type（与 semantic_hint 内容特征正交）

ingest 每个视觉单元产出一个**形态标签** `unit_type`，回答「这是什么**形**的载体」；`semantic_hint`（9+1 词表）回答「这是什么**内容特征**」。两维正交：一张流程图 `unit_type=flow-diagram`（形）+ `semantic_hint=流程`（内容特征）。

### 1.1 词表（开放，可扩展）

| unit_type | 形态判据 | 清洁 md 呈现 | S1 萃取分派 |
|---|---|---|---|
| `text-prose` | 正文/段落/叙述文字 | 文本转录，**不嵌原图** | 对象维 / 规则维 |
| `table` | 表格/网格（行列对应） | md 表转录，**不嵌原图** | 规则维 / 参数维（清单参数→数据层） |
| `flow-diagram` | 流程图（节点+箭头/分支/并行/泳道） | **嵌原图 + 图内文字照录** | **Read 原图→任务维**（IOPE+拓扑） |
| `ui-interaction` | 页面交互图/UI 截图（屏幕+状态转移） | **嵌原图 + 图内文字照录** | **Read 原图→任务维**（交互时序） |
| `architecture-diagram` | 架构图/拓扑图/组件关系图 | **嵌原图 + 图内文字照录** | **Read 原图→对象维关联** |
| `chart` | 统计图表（柱/折/饼，数值可视化） | **嵌原图 + 图内文字照录**（轴标签/图例/数值） | 参数维（数值照录，趋势解读留 S1） |
| `decoration` | 纯装饰/logo/纯背景/状态栏图标 | **not_transcribed**（登记 reason） | skip |
| `mixed` | 一页含多形态（正文+流程图等） | 文字部分转录 + 图样部分嵌图 | 按子区域分别分派 |
| `other` | 未识别形态 | **保图保守**（嵌原图 + 可读文字照录） | Read 原图判定 |

### 1.2 fail-safe 分类原则（分类不承重）

**核心不变量：形态分类错误绝不造成不可逆内容丢失。**

- **机械层无条件保图**：每个视觉单元渲染图存 `attachments/` + manifest 指针（`rendered_image`/`pictures`），**完全不依赖分类**——图永远在。
  - **保图覆盖范围澄清（O1 边界）**：「无条件保图」覆盖 **raster 载体**（内嵌图原件 pictures + 整页渲染图 rendered_image）。**PPTX 原生矢量图样**（GROUP 组合/矢量箭头，非 raster 内嵌图）在 **substrate-only 档**（无整页渲染，LibreOffice 未装/`--no-office-render`）下**无图片载体**（pictures 只导出 raster，rendered_image=null）——此时「S1 拿原图重解读拓扑」fallback **不可用**。**内容仍不丢**：substrate bbox 承载节点身份/编号/位置（S1 消费 substrate 位置结构重建拓扑，§六.2 联合消费），**IG1 目视源件兜底**。fail-safe 不变量「形态分类错误绝不造成不可逆内容丢失」仍成立（substrate 保内容）；但「原图视觉重解读」承诺对原生矢量 substrate-only 档不闭合，登记为边界（ingest parsing-limits ⑱）。**可选增强**：图样类单元整页渲染兜底（LibreOffice 可用时 render 原生矢量→PNG，恢复 Read 载体）。
- **分类只驱动清洁 md 呈现**（嵌图 vs 纯文本），**不驱动图是否存在**。分类错了天塌不下来：
  - 流程图误判成文字类→清洁 md 拍平了，但原图仍在 attachments，**S1 拿原图重新解读拓扑**，语义没丢。
  - 内容图误判成装饰→进 not_transcribed，但图仍在 attachments，**IG1 人核对照源件兜底**，可恢复。
- **拿不准→保图保守**（`other`/`mixed` 嵌原图 + 照录可读文字 + flag uncertain），永不静默丢。
- **唯一真正剔除的是高置信装饰**（logo/纯背景/状态栏图标），且 not_transcribed 登记 reason 可审计。
- **谁分类**：机械分不了形态（pypdf/openpyxl 只知「有无图/文本密度」，分不清流程图 vs 文字表）——分类是 **LLM 整页转录 pass 的副产品**（vision agent 本就在看整页图做布局重建，顺手吐 unit_type），非额外脆弱机械分类器。

## 二、清洁 md 图样保真呈现规则

**图样保真 vs 文字转录二分**（防流程图转文字扁平化丢拓扑）：

- **图样类**（flow-diagram / ui-interaction / architecture-diagram / chart）：清洁 md = `![[attachments/原图.png]]` **嵌原图** + **「图内文字照录」节**（节点文字/箭头条件/标注/泳道标题/轴标签，带轻量区域归属）+ unit_type 标记。**不做拓扑解读**——不拍平成「有序步骤列表」叙事（那是把「形」加工成「义」，越界 S1）。拓扑语义（分支/并行/泳道/时序）由 S1 Read 原图提炼。
  - 图内文字仍**照录**（节点标签/箭头条件是「内容」，保真转录，也让后续 RAG 可检索）；但文字之间的**拓扑关系不解读**，留 S1 对着原图提炼。
  - 原图取最高保真载体：内嵌图原件（pictures）优先，否则整页渲染图（rendered_image）。
- **文字类**（text-prose / table）：清洁 md = 文本转录（md 表/层级/列表），**不嵌原图**（清洁 md 对 RAG 友好、对 S1 不冗余；原图仍在 attachments 兜底，S1 需要可回看）。
- **装饰**（decoration）：not_transcribed（登记 reason），不混入正文。
- **混合/未知**（mixed / other）：文字部分转录 + 图样部分嵌图；未知形态保图保守。

> **图样语义只在多模态消费可得**：清洁 md 作为文本 artifact（RAG/纯文本消费）只携带图内文字标签，**拓扑语义须 S1 多模态 Read 原图才可得**。下游消费者须知此限制——文本模式拿不到分支/并行结构。

## 三、置信度元数据 verification_status（S1/G1 校准怀疑度）

每单元一个 `verification_status`，描述转录文本的**认识论基础**，I2 回填时设、I3/IG1 确认：

| 值 | 判据 | 置信度 | S1/G1 处置 |
|---|---|---|---|
| `substrate-exact` | 文本取机械 substrate 精确值（DOCX/XLSX/PPTX），LLM 只结构重建 | 高（机械精确底） | 正常消费 |
| `render-transcribed` | 渲染图 + 文本层 inventory ground truth，LLM 转录有交叉校验 | 中（有 ground truth 护栏） | 正常消费，inventory-miss gap 须核 |
| `image-only-transcribed` | 无文本层 ground truth（inventory.items=[]），LLM 转录仅 IG1 人核兜底 | 须人核 | **G1 更怀疑**，对照源件目视 |

- `uncertain-pending` 与 verification_status **正交**：uncertain 候选读法进 gaps（uncertain-reading），IG1 人核裁定；决议随包传播（清洁 md 识别存疑节注记 + gaps.resolution）。
- **准备态包 verification_status=null**（机械层不裁定转录置信度）；I2 按 substrate_used + inventory.items 设值。
- S1/G1 消费 verification_status 校准怀疑度——**不对所有内容一视同仁**：image-only-transcribed + uncertain 单元须更怀疑。

## 四、个人信息精确位 personal_info_regions（S2 精确脱敏）

`personal_info_present`（单元级 bool）太粗——S2 脱敏得自己在文本里找名字（猜）。增 `personal_info_regions` 给 S2 **精确脱敏 checklist**：

```json
"personal_info_regions": [
  {"region": "图中位置/节内位置", "kind": "人名|证件号|联系方式|机构名歧义", "reading": "照录原文"}
]
```

- **仍是「登记位」非「脱敏」**（照录不脱敏纪律不越界）：reading 照录原文，S1→S2 虚构替换时按 region 精确定位，非全文猜。
- clearly-read 的人名（非 uncertain）也登记 region；uncertain 的人名/机构名歧义同时进 uncertain + personal_info_regions（kind=机构名歧义）。
- 水印个人标识仍进 not_transcribed（不混入正文），不进 personal_info_regions。
- S2 脱敏消费 personal_info_regions 作精确 checklist（个人标识去除为通用红线，sensitivity-rules §四）。

## 五、溯源映射 md_heading + provenance 链（可维护性命门）

**方法论要求溯源**（methodology-core §1.2「事理层知识要求可登记来源与专家复核记录」），本契约把溯源落到字段：

### 5.1 section ↔ 清洁 md 映射

- manifest `section.heading` = **机械标题**（PDF=「第 N 页」页号，DOCX/XLSX/PPTX=substrate 标题）。
- manifest `md_heading` = **LLM 实际清洁 md 标题**（I2 转录产出的语义标题，如「概述」）。准备态=null，I2 回填。
- **I3 机械组装最终清洁 md 时**（ingest `assemble_pack.py`）：按 manifest.sections 顺序逐节**确定性拼接**（每源件单一 `<doc_id>.md`），md_heading 由 I2 回填，**节序与 manifest 一一对应由脚本构造保证**——机械组装非 LLM 合并，无静默错位/拆分风险；按序/不丢弃/图嵌守恒由脚本自校验断言（ingest 铁律 4：脚本做机械操作，LLM 做语义操作）。
- 溯源靠 md_heading↔section_id 映射（非纯 positional）——PDF 机械标题是页号、清洁 md 是语义标题，二者不同，须 md_heading 桥接。

### 5.2 溯源链（source → section → 描述句 → TTL）

```text
source (doc_id + source.sha256)
  → section (section_id + locator{page/sheet/slide/cell} + md_heading)
    → 描述句 (tpl-29-sentences「来源」列：doc_id / section_id / locator)
      → TTL 构件 (annotation：rdfs:isDefinedBy / skos:note 挂源 provenance)
```

- **S1 萃取每条描述句挂来源**（doc_id + section_id + locator）；跨文档合并的描述句挂多来源。
- **S3 编译 TTL 挂 annotation**（`rdfs:isDefinedBy` 指向源文档/节，`skos:note` 登记溯源）——构件可回溯到源单元。
- **消费方**：G1 专家把描述句回溯源页核验；S4 审计缺陷报告引源；S6 黄金用例溯源规则；**产品参数变更时定位受影响 TTL 公理**（可持续维护的基础）。
- 没有溯源，本体就是一堆无法追溯、无法精准更新的断言——与「笔记集合」无本质区别。本链是「可持续维护 wiki/本体系统」的结构性必需。

## 六、S1 消费协议（model 侧实现判据）

S1 消费萃取原料包时按本契约执行（落地见 model SKILL.md S1 + structured-input-mapping）：

1. **形态分派**：读 manifest 每节 unit_type，按 §1.1 表分派萃取维——table→规则/参数维；flow-diagram/ui-interaction/architecture-diagram→**Read 嵌入原图**→任务维（IOPE+拓扑）/对象维关联；text-prose→对象/规则维；decoration→skip；mixed/other→按子区域分别 / Read 原图判定。
2. **图样多模态消费**：图样类单元 S1 **Read 清洁 md 嵌入的原图**（attachments/），从视觉提炼任务维语义（步骤/时序/分支/并行/泳道/IOPE），**不依赖扁平文字**。清洁 md 图内文字照录节作辅助（标签核对），拓扑以原图为准。
   - **联合消费条款（O2 边界）**：当 `verification_status=substrate-exact` 且内嵌原图**不含节点文字/编号**（仅关系 glyphs：箭头/连接符/节点形态，节点标签与编号在原生 shape substrate）时，**纯 Read 原图不足以独立重建拓扑**——S1 须**联合消费**：Read 原图（拓扑关系/方向/节点形态/分支并行泳道）+ substrate bbox/文本（节点身份/编号/标签照录，**节点身份权威**）。原图给「关系」，substrate 给「身份」，二者对齐（bbox 坐标 × 视觉位置）重建完整拓扑。清洁 md「图内文字照录」节此时可能只含关系 glyphs 注记而无节点标签（标签在 substrate），S1 不得因照录节无标签而误判节点缺失。典型载体：PPTX 流程图页（pictures 仅箭头/连接符，节点标签/编号在 shape substrate）。
3. **context 预算**（methodology-core §4.6「Token 超长三对策」落地）：S1 **选择性 Read 图样单元原图**（非全量页图）；图样密集文档（大规模文档集）可**委托 vision agent 做「图样→任务维结构化」**（复用 ingest 的 ontology-vision-extractor agent 模式，主会话只消费结构化结果），避免主会话 context 爆炸。委托与否登记 manifest。
4. **溯源携带**：每条描述句挂来源（§5.2）；S3 编译 TTL 挂 annotation。
5. **置信度消费**：读 verification_status + gaps（uncertain-reading / inventory-miss / image-only-page），G1 对 image-only-transcribed + uncertain 单元更怀疑（§三）；uncertain 决议须核。
6. **个人信息精确脱敏**：S1→S2 按 personal_info_regions 精确虚构替换（§四），非全文猜。
7. **hint 不替代识别**：semantic_hint（内容特征）+ unit_type（形态）只是加速底稿，S1 逐节复核，不替代三维萃取判断（ingest 铁律 7 同源）。
8. **场景相关性裁剪归 S1（ingest 不预过滤）**：ingest 保真全量产出（含对某建模场景无关的页），**不做场景相关性过滤/预加工**——那需要建模场景知识，是定制化语义判断，属 S0 准入裁剪 + S1 萃取职责。S1 按**建模场景 + affordance**（unit_type/hint/md_heading）做相关性 triage：对建模无对象-任务-规则贡献的单元（如纯 UI 展示页）轻萃取/skip，**噪音在 S1 过滤而非进料层**。保真全量是不可逆丢失护栏（场景可能变，进料层丢弃不可逆）；affordance 是通用桥，不预判场景相关性。通用 skill ≠ 通用 output：场景定制经 S0/S1 输入进入，不经 ingest。

## 七、ingest 产出契约（ingest 侧实现判据）

ingest 按本契约产出五类 affordance（落地见 ingest tpl-extract-pack / prompt-vision-extract / SKILL）：

- manifest section 增 `unit_type`（I2 填）/ `verification_status`（I2 填）/ `personal_info_regions`（I2 填）/ `md_heading`（I2 填）；准备态均 null/[]。
- page-transcribe schema 1.1 agent 输出增 `unit_type` / `personal_info_regions` / `md_heading`；verification_status 由主会话 I2 按 substrate_used+inventory 设（agent 不裁定置信度）。
- 清洁 md 按 §二图样保真呈现规则在**转录层**落实；机械层无条件保图（§1.2 fail-safe）。**最终每源件单一合并 md 由 I3 机械组装**（`assemble_pack.py` 按 manifest 序拼接；图嵌中间态 `![[attachments/x]]`→最终裸文件名 `![[x]]`）。
- I3 收卷断言（assemble_pack.py 自校验 + 主会话收卷）：节序↔manifest 一一对应（脚本构造保证）+ 逐单元内容完备按序 + 图嵌守恒 + md_heading 落位 + verification_status 汇总 + personal_info_regions 齐 + 清洁 md 无机器锚 + source.sha 零回写。

## 八、虚构配例（票据贴现示例载体，中性）

- 流程图页 `贴现流程.png`：unit_type=flow-diagram，清洁 md=`![[attachments/贴现流程.png]]` + 「图内文字照录：节点『贴现申请』『背书核验』『放款登记』；箭头条件『背书连续』」+ semantic_hint=[流程]；verification_status=image-only-transcribed（无文本层）；拓扑（并行/分支）留 S1 Read 原图。
- S1 消费：Read 贴现流程.png→任务维描述句「步骤『背书核验』前提=背书连续；效果=申请状态→待放款」，来源列=`票据贴现制度 / s003 / image`；S3 编译 TTL 挂 `rdfs:isDefinedBy` 源节。
- 表格页 `费率表.xlsx`：unit_type=table，清洁 md=md 表（不嵌原图），verification_status=substrate-exact；S1 规则维/参数维消费，清单参数→数据层。
- 含联系人页：personal_info_regions=[{region:"摘要表·招标联系人行", kind:"人名", reading:"某先生"}]；S2 按 region 虚构替换。

## 九、限制登记

- 形态分类非 100% 准（艺术化流程图/混合页尤甚），fail-safe 保证误判不丢内容（§1.2）+ IG1 人核兜底 + S1 有 raster 原图可重解读（**原生矢量 substrate-only 档例外**：无图片载体，substrate bbox 兜底，见 O1）。
- 图样拓扑语义只在多模态消费可得（§二），纯文本/RAG 消费拿不到分支/并行结构——下游须知。
- **O1 原生矢量保图边界**：PPTX 原生矢量图样（GROUP/矢量箭头）substrate-only 档无图片载体（pictures 只导出 raster，rendered_image=null），「原图视觉重解读」fallback 不闭合；内容不丢（substrate bbox 承载身份/位置），S1 消费 substrate 位置结构 + IG1 目视源件兜底；可选整页渲染增强（LibreOffice 可用时）。详见 §1.2 澄清 + ingest parsing-limits ⑱。
- **O2 联合消费边界**：substrate-exact 图样类原图仅含关系 glyphs（无节点文字/编号）时，纯 Read 原图不足以独立重建拓扑，须 Read 原图（关系）+ substrate bbox/文本（身份）联合消费（§六.2 联合消费条款）。
- **图样保真增量载体依赖**：连接符/方向/节点形态级拓扑增量可在线性流程图验证；分支/并行/泳道/循环级增量须含此类绘制结构的载体才能验证（线性流程载体无此类结构可证，非设计缺陷）。
- BPMN2.0/OWL-S 形式化仍为 model 扩展位（MVP 降级 md 结构化描述）；本契约的图样保真向前兼容——无论 S1 现在降级 md 还是将来编译 BPMN，原图保真都对。
- 质量回流（下游→ingest 重转录）暂缓，本契约不含回流入口；待后续批次。