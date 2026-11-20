---
name: ontology-ingest
metadata:
  version: 2.2.1
description: 异构文档保真进料前置——把 PDF/图片/Excel/Word/PPT 业务资料统一转为「萃取原料包」（清洁保真 MD + canonical manifest + attachments），喂入 ontology-model S1。唯一目标=萃取就绪的保真（内容完备性/准确性/结构性，S1 能消费的保真），还原结构+保真全量内容，不理解内容本身（萃取是 S1 的事）。架构=LLM 整页布局感知转录 primary（每个视觉单元必过）+ 机械渲染/完整性 inventory/原生 substrate/交叉校验护栏；图样类（流程图/交互图/架构图）嵌原图保真交 S1 多模态萃取流程语义不文字扁平化；产物按 ingest→S1 接缝契约（s1-handoff-contract）产五类 affordance（形态维 unit_type/图样保真/置信度 verification_status/个人信息精确位/溯源映射 md_heading）。当用户要求把异构业务资料（PDF/扫描件/Excel/Word/PPT/图片）接入本体建模、做文档解析进料、产萃取原料包、或提到「文档解析」「进料」「萃取原料包」「异构资料接入」「PDF 转结构化」时使用本 skill。即使用户只说「帮我把这份 PDF 资料建模」，进料前置也应先经本 skill。
---

# ontology-ingest：异构文档保真进料前置

## 定位与边界

ontology-model 从 S0 准入直接进 S1 萃取，假设输入已是「可阅读文本」。实际业务资料是 PDF/图片/Excel/Word/PPT 异构形态——本 skill 是**保真进料前置引擎**，把异构原料统一转为 S1 可消费的「萃取原料包」（**清洁保真 MD** + canonical manifest.json + attachments/），**唯一目标=萃取就绪的保真（内容完备性/准确性/结构性）**：还原原始资料结构 + 保真全量内容，不结构错乱、不丢失内容，**不理解内容本身**（语义萃取是 S1 的事），加速 S1' 第1步语义识别（hint 对照），**不替代 S1 萃取判断**。

- **架构（LLM 主路径 + 机械护栏）**：**LLM 整页布局感知转录 primary（每个视觉单元必过）+ 机械渲染/完整性 inventory/原生 substrate/交叉校验护栏**。**不变量：任何单元都不被静默路由 mechanical-only 跳过 LLM**。
- **接缝契约（萃取就绪的保真）**：质量目标=「**萃取就绪的保真**」——S1 能消费的保真才是 fitness-for-purpose，ingest 与 S1 在契约层共同设计（非「ingest 产 md、S1 读 md」扔过墙式松耦合）。唯一接口权威=`../../ontology-model/references/s1-handoff-contract.md`（归 model references/，ingest 只读引用），五类 affordance：形态维 unit_type / 图样保真呈现 / 置信度 verification_status / 个人信息精确位 personal_info_regions / 溯源映射 md_heading。**图样保真**：流程图/交互图/架构图嵌原图 + 图内文字照录，拓扑解读留 S1 多模态 Read 原图（不文字扁平化）；**形态分类 fail-safe**：机械无条件保图，unit_type 只驱动呈现不驱动图存在，误判不丢内容（parsing-limits ⑯⑰）。
- **机械/LLM 分界（反转但纪律保留）**：I1 确定性 CLI（不调 LLM）产 canonical **准备态包**（渲染图+inventory+substrate，extraction=prepared）；I2 整页转录由只读 vision agent 外接（primary），回填后包**显式非 canonical**（transcribe_meta 带时间戳，只在此层）；I3 交叉校验机械（inventory 覆盖断言）。
- **不做**：本体建模（ontology-model 管）、审阅批注（ontology-review 管）、模拟验证（ontology-simulate 管）、脱敏（S1→S2 管，本层照录不脱敏只做登记位）、语义理解/萃取（S1 管）、**场景相关性过滤/预加工**（S0 准入裁剪 + S1 萃取管——按建模场景过滤无关/预加工相关需场景知识，是定制化语义判断；ingest 守通用保真全量，场景定制经 S0/S1 输入进入不经 ingest）。
- **通用保真 vs 场景裁剪分层**：ingest = **通用保真进料 + 通用 affordance**，不做场景相关性过滤。**保真全量 = 不可逆丢失护栏**——今天某建模场景的噪音页（如纯 UI 展示页），明天另一场景（流程/风控建模）可能正是语义来源，进料层一旦丢弃不可逆。**affordance（unit_type/hint/md_heading）= 通用桥**：让 S1 按建模场景做相关性 triage（噪音页轻萃取/skip），ingest 自身永远不知场景。「萃取就绪」= **通用 S1 可消费性**（格式清洁 + affordance 导航 + 溯源链），非特定场景定制。**通用 skill ≠ 通用 output**：ingest/model 皆通用 skill，场景定制经 S0 准入 + S1 萃取输入进入（run/input 层），不在 skill 层。详见接缝契约 §六.8。
- **路径约定**：脚本调用以 `<skill根>` 指本 skill 根（Claude Code=`.claude/skills/ontology-ingest/`；独立套件=`skills/ontology-ingest/`）；跨 skill 只读引用 ontology-model `references/s1-handoff-contract.md`（**ingest→S1 接缝契约唯一接口权威**）/`structured-input-mapping.md`（hint 词表对照）/`sensitivity-rules.md`（敏感口径），相对路径 `../../ontology-model/references/`，四 skill 同级部署。
- 版本历史=`CHANGELOG.md`（执行不依赖）；人类手册=`README.md`；格式契约=`assets/tpl-extract-pack.md`（pack schema 2.1 + page-transcribe 1.1）；解析边界=`references/parsing-limits.md`（编号稳定 ①-⑱，迭代在此）。

## I0 准入与敏感判定

1. 确认输入清单（pdf/docx/xlsx/pptx/图片）与 run 目录受控归属：**真实业务资料→萃取原料包必须落受控目录**（不进版本控制/不进入对外分发通道，对齐 ontology-model `references/sensitivity-rules.md`）；虚构资料→可入版本控制目录。
2. 敏感级登记（`--sensitivity 真实业务|虚构通用`）+ 权威度登记（`--authority 正式制度|专家口述|二手转述`）——包只承载登记位，可信源硬要求由 model S0 登记 + G1 强制。
3. manifest 开卷：解析时刻由主会话记 run-manifest（**canonical 包零时间戳**，I0 带日期）；登记输入清单/轨道/敏感级/渲染后端（LibreOffice 可用否）。
4. **批量 doc_id 碰撞预检**：同 stem 不同格式（如 x.pdf/x.pptx）会 doc_id 碰撞→再解析守卫 exit 2；批量须 distinct 文件名或逐文件 --doc-id。

## I1 机械层（确定性 CLI：渲染 + inventory + substrate，无 LLM）

```bash
python3 <skill根>/scripts/parse_documents.py INPUTS... [--output-dir DIR] [--doc-id ID] \
    [--authority 正式制度|专家口述|二手转述] [--sensitivity 真实业务|虚构通用] [--password PW] \
    [--render-scale 2.0] [--no-office-render] [--force]
```

机械层三职责（**不再产最终正文**，产准备态护栏）：
- **渲染**：PDF 每页→PNG（pypdfium2，BSD/Apache，避 fitz AGPL）；图片原图直供；office（pptx/docx/xlsx）LibreOffice 可用→PDF→页图（可选增强），否则 substrate-only。**每单元都有 render 或 substrate，无静默跳过**。`--no-office-render` 强制 office substrate-only canonical 档（纯 pip 确定性，LibreOffice 渲染层非 canonical〔limits ⑪〕；测试环境无关化与用户 canonical 控制用）。
- **inventory**（完整性 ground truth，I3 交叉校验防 LLM 漏字）：PDF 文本层行 / XLSX 非空单元格 / DOCX 段落+表格 / PPTX shape 文本+备注。image-only 页 items=[]（⑬ 诚实边界）。
- **substrate**（原生结构化精确文本，直抽比 OCR 更准）：DOCX 结构化 md（Heading/列表/行内加粗斜体/表格合并去重）/ XLSX 单元格网格（合并保留/`<br>` 多行/公式双读）/ PPTX 位置 substrate（bbox 坐标+文本+类型+分组+图片+表格，按视觉位置排序，供 LLM 布局重建）。
- 内嵌图导出 attachments/（DOCX word/media / PPTX 图片 / XLSX 嵌入图）→I2 转录。
- 扩展名路由 pdf/docx/xlsx/pptx/png|jpg|jpeg|webp|bmp|gif；批量每文档独立包子目录（默认 `cwd/萃取原料包/<doc_id>/`，**不进 skill 目录、不覆盖权威**）。
- gap 如实登记不阻塞（gap 是产物不是失败）；exit 0=准备成功 / 1=零回写断言失败 / 2=输入错（缺文件/不支持/坏文件/碰撞/再解析守卫/缺库/AES/密码错）。
- 缺解析/渲染库→exit 2+pip 提示（懒 import，不阻塞 model/review/simulate）；**fitz/PyMuPDF 零代码路径**（AGPL，pypdfium2 替代，详见 parsing-limits ⑨）。
- 格式契约（manifest schema 2.1 / 清洁 MD / hint 9+1 词表 / term 结构种子 / exit 三态 / 接缝 affordance 准备态 null）=`assets/tpl-extract-pack.md`；解析边界与许可=`references/parsing-limits.md`。
- **机械层无条件保图（fail-safe，⑯）**：每单元渲染图/内嵌图存 attachments/ + manifest 指针（rendered_image/pictures），**完全不依赖形态分类**——图永远在，I2 误判 unit_type 不造成不可逆内容丢失。机械只产 semantic_hint（内容特征启发式），**unit_type 形态维由 I2 LLM 填**（机械分不了形态）。接缝 affordance（unit_type/verification_status/personal_info_regions/md_heading）准备态 null/[]，I2 回填。

## I2 整页布局感知转录（primary，每个视觉单元必过）

**每个 extraction=="prepared" 单元都交 LLM 整页转录**（PDF 页/幻灯片/图片/内嵌图），无静默跳过。

1. 委托 **ontology-vision-extractor**（只读 agent，无 model 字段——平台中立，模型由编排指定）：传单元渲染图路径（agent 用 Read 直接读图，**二进制不进主会话上下文**）+ doc_id + section_id + manifest 对应 rendered_image/pictures sha256 + **substrate 文本（若有，取精确文本）** + **inventory（完整性 ground truth）** + `assets/prompt-vision-extract.md`（page-transcribe 模式），返回 page-transcribe JSON 全文（schema 1.1，含 transcription / **unit_type** / **md_heading** / **personal_info_regions** / semantic_hint / uncertain / not_transcribed / personal_info_present）。**图样类单元 agent 嵌原图 + 图内文字照录，不拍平拓扑**（prompt 纪律 11/15，s1-handoff-contract §二）。
2. **主会话校验回填序列**（格式权威 tpl §五）：
   - 校验 schema_version==1.1 + mode==page-transcribe + section_id 存在且 extraction=="prepared" + source_sha256 匹配 manifest rendered_image/pictures sha（substrate-only 单元 source_image=null 跳过）+ **unit_type ∈ 9 值形态词表**。
   - text=transcription（清洁布局保真 md）、extraction="transcribed"、transcribe_meta 落位（agent/model_alias/backfilled_at/transcribe_sha256）、text_sha256=sha256(text)。
   - **接缝 affordance 回填**（s1-handoff-contract §七）：`unit_type`/`md_heading`/`personal_info_regions` 取 agent 输出落位 manifest section；**`verification_status` 由主会话设**（agent 不裁定置信度）——substrate_used=true→`substrate-exact`；否则 inventory.items 非空→`render-transcribed`；inventory.items=[]→`image-only-transcribed`（⑬ 靠 IG1 人核）。
   - **完整性交叉校验**（tpl §五.1）：inventory.items 逐项归一化后须出现在 transcription；缺失→gap（inventory-miss，pending IG1）或重转录。substrate 单元另核 substrate.text 关键 token 覆盖。
   - **机械层零触碰**——rendered_image/substrate/inventory/pictures 的 sha 锚复核未被改动（LLM 只填 text/transcribe_meta + 接缝 affordance）。
   - uncertain 保留进 gaps（uncertain-reading，note 挂候选读法），IG1 呈报人核；not_transcribed 登记（高置信装饰/水印剔除留痕）；personal_info_present=true→sensitive_flags 追加个人信息 + **personal_info_regions 落位给 S2 精确脱敏 checklist**（登记位非脱敏）。
   - 回填计数如实呈报（失败退占位+如实报计数）；**回填后包显式非 canonical**。
3. **最终清洁 md 由 I3 机械组装**（`scripts/assemble_pack.py`，**非 LLM 合并**）：I2 只逐单元转录回填 manifest.sections[].text；每源件单一 `<doc_id>.md` 的**按序/不丢弃/图嵌守恒由 I3 机械脚本保证**（LLM 合并有注意力遗漏/上下文截断/改写风险，且全文进上下文不可持续——机械组装从 manifest 读盘拼接零 LLM 上下文）。图样保真呈现规则（s1-handoff-contract §二）在**转录层**落实：图样类嵌原图 + 图内文字照录节，文字类纯文本不嵌原图，装饰 not_transcribed 不入正文，mixed/other 文字转录 + 图样嵌图。**md_heading 节序↔manifest 一一对应**由组装脚本机械断言（⑰ 溯源桥接）。
4. **批处理优化**（可选，⑭）：按文档/小批页 agent 返回数组减少调用次数（成本优化项，非默认）。

## I3 收卷与喂入（机械组装 + 交叉校验 + IG1 停等）

1. **零回写断言**：源文档 sha256 前后一致（脚本内置）+ 主会话复核冻结件未被触碰。
2. **最终清洁 md 机械组装**（`scripts/assemble_pack.py PACK_DIR... | --pack-root DIR`）：从 manifest.sections[].text 按序组装每源件单一 `<doc_id>.md`（落 pack 目录，与 attachments/ 同级）。**机械保证**（脚本自校验，exit 1 若失败）：唯一 H1=doc_id / 单元标题压实 H2 起连续层级 / `---` 分页节 / 空单元诚实占位 / 图嵌 `![[attachments/x]]`→`![[x]]` 裸文件名（Obsidian 全局文件名解析约定）/ **逐单元内容完备且按 manifest 序拼接**（归一化子串单调游标，不丢弃）/ 图嵌计数守恒 / 清洁无机器锚 / source.sha 零回写。**合并是机械操作非 LLM 语义操作**（铁律 4）——按序/不丢弃由脚本断言保证，不靠 LLM 合并纪律。
3. **完整性交叉校验汇总**：inventory 覆盖断言结果（inventory-miss gap 清单）+ substrate 覆盖；image-only 页诚实登记（⑬ 靠 IG1 目视）。
4. **清洁 md 断言**：最终 md 正文 grep `locator:|extraction:|## \[s|<!--|text_sha256|sensitive_flags` 零命中（图嵌入除外）——机器元数据全在 manifest，无下游 S1 污染。**图样保真断言**：unit_type∈图样类的单元清洁 md 必含 `![[原图.png]]` 裸文件名嵌原图（未拍平成纯文字叙事，⑯）。
5. **接缝 affordance 收卷断言**（s1-handoff-contract §七，⑰）：每节 `unit_type` 全填∈9 值词表；`verification_status` 全设（汇总三值分布 substrate-exact/render-transcribed/image-only-transcribed）；`md_heading` 落位 + **节序↔manifest.sections 一一对应**（组装脚本机械断言）；`personal_info_present=true` 单元 `personal_info_regions` 非空（S2 精确脱敏 checklist 齐）。
6. **敏感登记复核**：sensitivity.level + 节级 sensitive_flags 齐；真实业务包确认受控目录归属。
7. **manifest 收卷**：coverage（units_total/units_prepared/units_transcribed）/gaps（含 uncertain-reading/inventory-miss）/term_candidates/回填计数 + **unit_type 形态分布 + verification_status 置信度分布**。
8. **IG1 停等**：呈原料包覆盖/gaps/uncertain/inventory-miss/转录计数 + **verification_status 分布**给用户**亲自确认保真**（对照源件目视复核，尤其 **image-only-transcribed 页 + uncertain + 图样类单元**〔拓扑保真须人核〕）→喂入 ontology-model S1（入口 (a)，按 s1-handoff-contract §六消费）。**不代答代签**；LLM 转录须人核保真（机械交叉校验是护栏非权威）。

## 闸门总览

| 闸门 | 位置 | 内容 | 停等对象 |
|---|---|---|---|
| IG1 | I3 收卷 | 原料包保真确认（覆盖/gaps/uncertain/inventory-miss/转录计数 + 目视复核）→喂入 model S1 | 用户（亲自验收，不代签；image-only 页 + uncertain 须目视） |

## 铁律

1. **零时间戳**——canonical 准备态包（MD+manifest）零 now()/mtime/随机 id；解析时刻由主会话记 run-manifest；时间戳只在 transcribe_meta（回填后非 canonical 层）。
2. **零回写**——源文档 sha256 前后断言（否则 exit 1）；输出 realpath 碰撞守卫；再解析守卫护转录回填层（--force 显式覆盖）。
3. **照录不脱敏**——解析层保真转录（阈值照录不模糊化），脱敏在 model S1→S2；本层只做登记位（sensitivity.level + 节级 sensitive_flags）；真实业务包必须受控目录。
4. **机械/LLM 分界反转但纪律保留**——I1 机械 CLI 不调 LLM（产准备态护栏）；I2 LLM 经只读 agent 整页转录（primary，零臆造，模糊登记候选读法绝不猜测定值）；I3 交叉校验机械（inventory 覆盖，护栏非权威）+ **最终 md 机械组装**（assemble_pack.py 按 manifest 序拼接，保证按序/不丢弃/图嵌守恒，非 LLM 合并）。**不变量：任何单元都不被静默路由 mechanical-only 跳过 LLM**。**机械不创作转录正文**（内容权威是 LLM 逐单元转录），**但机械组装最终 md**（结构组装是确定性机械操作，LLM 合并不可保证不丢弃）；LLM 不改机械字段。
5. **fitz 零代码路径 + 质量优先**——PDF 渲染 pypdfium2（BSD/Apache，MIT 兼容）；不 import fitz/PyMuPDF（AGPL/商业双许可）；不引入系统 OCR 二进制/本地 VLM（违通用性 + 许可不兼容 + 与 vision agent 冗余）。纯 pip 放宽为「pip + LibreOffice 子进程渲染（可选），质量优先」（parsing-limits ⑨⑩）。
6. **产物永不写入 skill 目录**——`.claude/skills/`、`.claude/agents/` 只放机制本体；萃取原料包入 run/受控目录；attachments 二进制不进主会话上下文。
7. **hint 不预判本体语义 + unit_type 正交 fail-safe**——semantic_hint 只提示内容特征（9+1 词表，对照 model mapping），机械启发式可空永不权威；S1' 第1步逐节复核，hint 不替代识别。**unit_type 形态维**（I2 LLM 转录副产品）与 semantic_hint 内容特征**正交**（形 vs 义），**fail-safe 不承重**：机械无条件保图，分类只驱动清洁 md 呈现不驱动图存在，误判不丢内容（S1 拿原图重解读 + IG1 人核兜底，⑯）。
8. **清洁 md + 图样保真二分**——机器元数据（locator/extraction/sha/hint/sensitive/接缝 affordance）全入 manifest，md 正文清洁 markdown；下游 S1 无机器锚污染。**图样类**（流程图/交互图/架构图/图表）嵌原图 + 图内文字照录（拓扑解读留 S1 多模态 Read 原图，不文字扁平化）；**文字类**（正文/表格）纯文本不嵌原图（⑯，s1-handoff-contract §二）。

## 资产索引

- `references/`：parsing-limits.md（格式解析边界①-⑱/许可登记〔pypdfium2/LibreOffice〕/渲染确定性/image-only 诚实边界/LLM 成本/机械-LLM 分界反转/图样保真二分+形态分类 fail-safe〔⑯〕/接缝元数据+溯源映射〔⑰〕/原生矢量保图边界〔⑱〕/term 种子/完整四通道扩展位，编号稳定迭代唯一入口）
- `assets/`：tpl-extract-pack.md（pack schema 2.1 + 清洁 MD 规范 + 图样保真呈现规则 + page-transcribe schema 1.1 + 接缝 affordance + 完整性交叉校验断言 + hint 9+1 词表对照 mapping + exit 三态 + 虚构配例）/ prompt-vision-extract.md（page-transcribe 主模式 + image-extract 兼容，整页布局重建 + 图样保真 + 形态分类 fail-safe 纪律）
- `scripts/`：parse_documents.py（I1 机械层 CLI：渲染+inventory+substrate+接缝 affordance 准备态 null，懒 import，exit 0/1/2，py3.9）/ assemble_pack.py（I3 机械组装 CLI：manifest.sections[].text 按序→每源件单一 `<doc_id>.md`，保证按序/不丢弃/图嵌守恒/裸文件名图嵌，自校验 exit 0/1/2，py3.9，确定性零时间戳）
- agents：ontology-vision-extractor（I2，只读，无 model 字段，平台中立模型由编排指定，page-transcribe 双模式，输出 unit_type/md_heading/personal_info_regions）
- `README.md`（人类手册）/ `CHANGELOG.md`（版本历史，执行不依赖）
- 姊妹 skill：ontology-model（下游消费原料包，S1 入口 (a)；**接缝契约唯一接口权威=`references/s1-handoff-contract.md`**〔五类 affordance + S1 消费协议〕，hint 词表对照=`references/structured-input-mapping.md`，敏感口径=`references/sensitivity-rules.md`，只读不改）/ ontology-review / ontology-simulate
