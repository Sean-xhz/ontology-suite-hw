---
name: ontology-model
metadata:
  version: 1.14.2
description: 业务场景自动化本体建模管线——把业务资料/访谈/术语集编译为符合 W3C 规范的结构化本体（RDF/OWL/SKOS/SWRL，Turtle 输出），含双模型生成-审计-仲裁质检与黄金用例验收。当用户要求为业务场景（金融、保险、供应链、制造等行业域）构建领域本体/知识图谱 schema、把自然语言业务资料转成 RDF/OWL/SWRL 结构化模型、审计或质检既有本体 TTL 文件、做本体黄金用例验收、或提到「本体建模」「ontology」「TTL 生成」「本体审计」「29句话」「7+1 语义」时使用本 skill。即使用户只说「帮我把这份业务资料建模」而未点名本体，只要产物指向结构化语义模型，也应触发。
---

# ontology-model：业务场景自动化本体建模管线

## 定位与边界

七环管线（萃取→语义原料→准入→生成→质检→结构把关→验收）的 skill 化落地。方法论执行依据=**`references/methodology-core.md`（自包含内核，源自《本体驱动的AI数据管理》公开方法论）**。版本历史见 `CHANGELOG.md`（执行不依赖）。

**路径约定**：文中 `scripts/…`、`references/…`、`assets/…` 均相对本 skill 根目录，执行时按部署位置解析（Claude Code 环境=`.claude/skills/ontology-model/`；独立套件=`skills/ontology-model/`）。run 产物永不写入 skill 目录。

- **MVP scope**：RDF/OWL/SKOS/SWRL 四标准；SPARQL **Read 取知已形式化激活**（D3c，`scripts/derive_sparql.py` 从 TBox 派生查询模板库）；BPMN2.0/ODRL/SPARQL C/U/D 服务类语义仍为「扩展位」，降级为 md 结构化描述
- **语义覆盖矩阵**（7 类语义×承接形态三态，防「全覆盖」误读）：

| 描述集类别 | 承接形态 | 构件/落位 |
|---|---|---|
| 1 对象描述类 | **编译进 TTL** | owl:Class / DatatypeProperty / ObjectProperty（domain/range） |
| 2 分层约束类 | **编译进 TTL** | subClassOf / equivalentClass / AllDisjointClasses / Restriction / cardinality |
| 3 术语类 | **编译进 TTL** | skos:Concept（prefLabel/altLabel/definition/broader） |
| 4 控制规则类 | **编译进 TTL** | swrl:Imp + 结论类 disjoint；违反处置动作（4.3）登记于 md 处置档 |
| 5 流程活动类 | **md 扩展位登记** | BPMN2.0+OWL-S（IOPE）扩展位；四要素表进建模方案 |
| 6 权限管控类 | **md 扩展位登记** | ODRL 扩展位；角色-动作三档表进建模方案 |
| 7 CRUD 查询类 | **Read 形式化激活（D3c）+ C/U/D md 扩展位** | `derive_sparql.py` 产 7 类 SELECT 模板库（query-templates schema 1.0）；业务查询意图表由 S6 黄金用例消费；C/U/D（SPARQL UPDATE）留后续 R6 |

  「+1 目标评估」=消费链路治理登记（md，G1 必填，反博物馆），不产本体构件；清单参数运算与数值评分=**不承接**（数据层/应用层职责，本体只登记结构位与受控词表）。**扩展位路线图**：SPARQL **Read 取知已 skill 级激活**（D3c，`derive_sparql.py`；真实业务 run 级消费仍须 G1 范围评审）；BPMN2.0/ODRL/SPARQL C/U/D 形式化为 MVP 后能力，无排期承诺；启用条件=消费场景提出形式化硬需求且经 G1 范围评审。
- **三层边界**：机械脚本管形式层（语法/结构/推理一致性）、双模型管语义层（贴合度/逻辑漏洞）、人工管争议层（G1/G2/G3 闸门）——推理机与双模型互补不替代
- **不做**：向量化/RAG 接入、图数据库入库、生产部署（管线只交付 8 件套产物）

## 管线总览

| Stage | 内容 | 执行者 |
|---|---|---|
| S0 准入与裁剪 | 定入口模式、run 目录、受控状态确认、manifest 开卷 | 主会话 |
| S1 知识萃取（条件） | 原始资料→三维访谈框架（对象-任务-规则）萃取草稿+高频名词候选实体清单 | 主会话（盲测辅助验证模式可委托干净 subagent） |
| S2 语义原料组装 | 29句话描述集+术语词典 | 主会话 |
| **G1 准入评审** | 四标准两段评审：模型初审 Checklist→人工复核 | **人工闸门** |
| S3 生成 | 29句+词典→Turtle+建模方案草稿 | ontology-generator |
| S4 质检 | 机械脚本（L1-L3）→审计四元组→辩护/修订，≤3 轮 | 脚本+双 agent |
| **G2 争议仲裁** | A/B 争议人工裁定（一致时自动通过不触发） | **人工闸门** |
| S5 结构把关 | 可视化三步 checklist+四属性特征校验（可降级文本拓扑） | 主会话+人工 |
| S6 业务验收 | 黄金用例三元组→AI 扩展矩阵→失败三类归因→80%→90% | 主会话 |
| **G3 验收终审** | 测试报告终审 | **人工闸门** |

## S0 准入与裁剪决策

1. 评估输入形态，定入口模式并登记 manifest：**(a)** 原始业务资料→全管线（异构文档载体 PDF/图片/Excel/Word/PPT 可先经姊妹 skill `/ontology-ingest` 产「萃取原料包」〔清洁保真 MD+manifest+attachments，含 unit_type/verification_status/personal_info_regions/md_heading 接缝 affordance〕再喂入 S1，**按 `references/s1-handoff-contract.md` §六消费协议**〔形态分派/图样多模态 Read/溯源携带/置信度校准/精确脱敏〕，hint+unit_type 加速 S1' 第1步、适用判定不降级）；**(b)** 已有 29 句描述集→跳 S1；**(c)** 既有 TTL→只跑 S4 审计起（S5/S6 按需）。所有裁剪（跳过的 Stage、降级的验证层、未启用的扩展位）显式登记，禁止静默裁剪。**入口 (c) 增量通道（R2）**：既有 TTL 的简单修改（label/注解/受控值/增删类属性/规则级编辑）可走 `scripts/incremental_patch.py`（编辑操作 JSON→draft TTL+report，不覆盖权威，契约=`assets/tpl-patch-schema.md`），draft 仍以入口 (c) 起审计晋升；规则编码变更（MAJOR）无回归守护时转入口 (c) 全量审计。

   **基线迭代细则（入口 (b) 变体）**：对既有本体基线做迭代修订的 run，标准流程=①影响评估（新输入变化→受影响构件与规则族定位）→②修订对照表（基线构件 vs 新诉求，逐项处置=不动/修订/新增/删除）→③G1 评审对照表（口径冲突类业务裁定在闸门完成，不遗留到生成后）→④增量生成（冻结区零触碰，新构件只进增量区）→⑤继承黄金集**逐字节冻结**（哈希比对登记；改动既有用例必须走 G2 裁定）→⑥零回归双证明（继承用例全 PASS+机械校验全量复跑零新增 error）→⑦构件计数以机械实测为准（禁手抄）。迭代 run **事件驱动启动**（源头数据归一化完成/结构性缺口登记/生产化排期启动等触发条件），无触发条件不制造 run（反博物馆）。
2. 定 run 目录：`<runs_root>/<场景名>_<YYYYMMDD>/`。**runs_root 解析顺序**：①用户调用时显式指定 → ②环境变量 `ONTOLOGY_RUNS_ROOT` → ③本 skill README「环境与目录约定」节的部署环境默认。**真实业务敏感场景：runs_root 必须指向受控目录（不进版本控制/不进入对外分发通道）**——按 `references/sensitivity-rules.md` 确认目录受控状态并登记。
3. 建 run 目录+`run-manifest.md` 开卷（入口模式/目录受控状态/场景敏感级/参与角色），**并按三区结构建目录骨架**（归置判据=「同事消费会不会打开它」：会→交付物；追溯才看→过程；仅定位期有效→实验）：

   ```text
   <run目录>/
   ├── run-manifest.md          # 唯一根级过程文件（run 身份证）
   ├── 交付物/                   # 8 件套契约区（对外消费只进这里；第 9 件交接说明可选）
   ├── 过程/
   │   ├── 01 输入与证据/        # 用户资料、融合层件、影响评估
   │   ├── 02 闸门/              # G1/G2/G3 呈报件与裁定登记
   │   ├── 03 机械校验/          # validate.json / consistency.json / gc-results / 哈希比对
   │   ├── 04 结构把关/          # S5 拓扑报告+记录
   │   └── 05 复盘/              # 还原率对照、生产级复盘
   ├── 实验/                    # 削减实验 json+本体副本（登记可再生性，不入交付）
   └── archive/                 # 历史版本 TTL（命名规范 ontology_v<X.Y>.ttl）
   ```

   执行中各 Stage 产物**即产即归位**：机械校验产物→`过程/03`、闸门呈报件→`过程/02`、调试期实验副本→`实验/`；**禁止实验产物混入交付物区**（收卷净化兜底，见交付节）。
4. 路径纪律：manifest 中登记本次依赖的外部路径（知识库卡片/原书/脚本等，如有）；任何路径失效即向用户索取新位置，禁止猜测。

## S1 知识萃取（条件执行）

入口 (a) 且无现成描述集时执行。按 `references/methodology-core.md` §1（三维结构化访谈协议）的提问清单与萃取纪律，沿**对象–任务–规则**三维从原始资料萃取：对象维（实体/属性/标识）、任务维（流程/操作/时序）、规则维（约束/阈值/例外/权限）。产出萃取草稿直接喂 S2。资料含真实个人信息时在进入 S2 前替换为虚构标识（sensitivity-rules §四）。**输入已是统一章节模板的结构化文档集**（业务侧已完成文档标准化）→ 按 `references/structured-input-mapping.md` 走 S1' 机械映射档（章节→描述集分节映射，G1 闸门不降级）。

**输入是 ingest 萃取原料包（清洁 md + manifest + attachments）→ 按 `references/s1-handoff-contract.md` §六消费协议执行**：①**形态分派**——读 manifest 每节 `unit_type`（形态维，与 `semantic_hint` 内容特征正交）：table→规则/参数维；flow-diagram/ui-interaction/architecture-diagram→**Read 清洁 md 嵌入的原图**提炼任务维（IOPE+拓扑）/对象维关联；text-prose→对象/规则维；decoration→skip；mixed/other→按子区域 / Read 原图判定。②**图样多模态消费**——图样类单元拓扑（分支/并行/泳道/时序）**未文字化**（ingest 只保形+照录图内文字），S1 须 Read 原图从视觉提炼，不依赖扁平文字；清洁 md 图内文字照录节作标签核对辅助。③**context 预算**（methodology-core §4.6 Token 超长三对策落地）——选择性 Read 图样单元原图（非全量页图）；图样密集文档（大规模文档集）可委托 vision agent 做「图样→任务维结构化」（复用 ontology-vision-extractor 模式，主会话只消费结构化结果），委托与否登记 manifest。④**溯源携带**——每条描述句挂来源（doc_id/section_id/locator，填 tpl-29「来源」列；md_heading 桥接清洁 md 节），S3 编译 TTL 挂 annotation。⑤**置信度消费**——读 `verification_status`（substrate-exact/render-transcribed/image-only-transcribed）+ gaps（uncertain-reading/inventory-miss），G1 对 image-only-transcribed + uncertain 单元更怀疑（不对所有内容一视同仁）。⑥**个人信息精确脱敏**——按 `personal_info_regions` 精确虚构替换（非全文猜，sensitivity-rules §四）。⑦**hint/unit_type 不替代识别**——只是加速底稿，S1 逐节复核三维萃取判断。

**高频名词候选实体登记（机械步骤）**：萃取时对输入资料中出现 ≥3 次（或每万字 ≥2 次）的业务名词**强制登记候选实体清单**——每个名词一行「名词/出现频次/建实体 or 降属性 or 不收 + 一句话理由」。低密度但结构关键的名词（如某条线特有的关联对象）最易被三维访谈漏检；本清单是 S2 组装描述集前的**核对底稿**，G1 评审时随描述集一并呈报（专家可当场推翻建/不建判断）。

**盲测对照（辅助验证模式，非默认路径）**：管线主路径=资料→方案+TTL 的**生成式建模**（入口 (a)/(b)）；盲测是一种**辅助验证模式**——当组织需要以历史人工方案为对照基准校准自动化建模能力（如采用决策评估、能力验收）时启用，不属日常建模场景。启用条件=存在历史人工方案作对照基准、需保护对照效力。执行纪律：S1/S3/S4 委托**干净上下文 subagent** 隔离执行（主会话可能已含历史方案摘要级信息，直接执行会污染对照效力）——委托时 subagent 禁读隔离区（历史方案/PRD 等，S0 在 manifest 中列明隔离清单），主会话只做编排与落盘；执行者偏差与「辅助验证模式」定位登记 manifest。盲测 run 收官时**必须**做还原率对照（模板=`assets/tpl-restoration-report.md`，见收卷清单勾稽位）。

## S2 语义原料组装

按 `references/methodology-core.md` §2（「7+1」框架与 29 句话模板判据）。用 `assets/tpl-29-sentences.md` 产出 **29句话描述集**（7 类语义逐句组装，NL→W3C 构件映射对齐）+ `assets/tpl-term-dict.md` 产出**术语词典**。执行最小化双原则（内核 §2.3：范围够用且可扩展、表达极简）与点线面小切口（内核 §2.4：首期只做「点」）。第 8 类「目标评估」必填——写明本本体服务的消费场景，无消费场景即中止并回报（反博物馆，内核 §4.5）。

## G1 准入评审（人工闸门·停等）

1. 模型初审：按 `references/methodology-core.md` §3.1 四标准判定问句（描述清晰/逻辑正确/内容完备/极简表达）出 Checklist 初审报告，逐句标注通过/存疑。
2. **停等人工复核**：把描述集+初审报告呈给用户（或用户指定的业务专家）；工程师判不了业务对错——业务语义必须由人确认。结论（通过/修改后通过/驳回）记入 manifest。驳回→回 S2 修订。

**呈报件规范（G1/G2/G3 通用）**：三道闸门呈报件统一用 `assets/tpl-gate-submission.md` 骨架，落 `过程/02 闸门/`；人工裁定结果按标准格式回填呈报件「裁定登记」节（裁定项/结论/理由/日期）——闸门记录可追溯，评审人无需读会话上下文即可定位「审什么/怎么裁/结论回填在哪」。

## S3 生成

委托 **ontology-generator** agent（Claude Code 参考实现 model: opus；平台中立异构纪律见铁律 4），传：run 目录路径、29句话描述集、术语词典、消费链路登记、`assets/prompt-generator.md`（Prompt 四段式+SWRL 规范写法硬要求）。金融域公共层对齐按需读 `references/fibo-guide.md`（金融场景扩展参考，其他行业域可同构对接该域公共标准本体；类复用=owl:imports+rdfs:subClassOf；术语对齐=skos:exactMatch/broadMatch；登记来源 IRI）。产出 `ontology.ttl` + `建模方案.md`（骨架=`assets/tpl-ontology-doc.md`，结构细则=`references/structure-patterns.md`）。**溯源 annotation**：描述句「来源」列（doc_id/section_id/locator）经编译挂 TTL annotation——`rdfs:isDefinedBy` 指向源文档/节、`skos:note` 登记溯源，使构件可回溯到源单元（G1 回溯源页核验 / S4 审计引源 / S6 黄金用例溯源 / 产品参数变更定位受影响公理；s1-handoff-contract §五.2，prompt-generator 编译纪律）。专家只读不写：生成过程无人工改稿，意见走 S4 缺陷通道。

## S4 质检（机械→审计→辩护，≤3 轮）

**第一步·机械脚本**（主会话 Bash 执行，形式层；`<skill根>` 按路径约定解析）：

```bash
python3 <skill根>/scripts/validate_ontology.py <run>/ontology.ttl --json-output <run>/validate.json   # L1+L2
python3 <skill根>/scripts/check_consistency.py <run>/ontology.ttl --json-output <run>/consistency.json # L3
```

exit≠0 的 error 级发现直接回 generator 修订（不占审计轮次）；L3 exit 2（环境不可用）→登记 manifest 降级 L2，不阻塞。warning 全部登记 manifest。

**增量修改通道（R2，入口 (c) 简单修改适用）**：`python3 <skill根>/scripts/incremental_patch.py <baseline.ttl> <patch.json> [--golden cases.json] [--with-l3]`——消费编辑操作 JSON 产 draft TTL+patch-report（L1/L2 零新增 error 闸门 + 受影响子集回归守护 + 版本 diff，**不覆盖权威**），draft 再以入口 (c) 起审计。exit 2=输入错不产 draft / 0=released / 1=blocked。契约与操作目录=`assets/tpl-patch-schema.md`。

**SHACL 约束校验通道（R4，实例级数据完整性）**：`python3 <skill根>/scripts/derive_shacl.py <ontology.ttl>` 从 TBox 机械派生 shapes.ttl+derivation-report（纯 rdflib）；`python3 <skill根>/scripts/validate_shacl.py <data.ttl> <shapes.ttl>` 用 pyshacl 校验实例数据 facet/基数/唯一性（补限制⑩剥离后推理器侧空白，纯 Python 无 Java）。与 S6 推理验收正交（SHACL=输入完整性闸门，不接入 golden 集）；与 check_instance 正交互补（零臆造 vs 数据完整性）。契约=`assets/tpl-shacl-shapes.md`。

**SPARQL 查询模板通道（D3c，Read 取知形式化）**：`python3 <skill根>/scripts/derive_sparql.py <ontology.ttl>` 从 TBox 机械派生 query-templates.json+.md（7 类 SELECT 模板库，纯 rdflib 内置 SPARQL 1.1，零新增依赖）——下游 Agent「经 SPARQL 取知」的静态脚手架。CLI 只产结构脚手架；业务查询意图（组合拼接+ORDER BY+阈值绑定）由主会话 md 补写、S6 黄金用例消费。与 derive_shacl 同构（TTL-direct/非权威可再生/零回写）；derived-query 联动 ontology-simulate what-if（物化后查推理结论）。C/U/D 留后续 R6。契约=`assets/tpl-query-templates.md`。

**第二步·双模型审计**：委托 **ontology-auditor**（Claude Code 参考实现 model: sonnet，只读；异构纪律见铁律 4）按 `assets/prompt-auditor.md` 出三维度四元组缺陷报告；主会话落盘 `缺陷报告.md`（`assets/tpl-defect-report.md`）。**入口 (c) 无描述集/词典时**：委托 prompt 须显式声明业务贴合度基准缺失——维度三降级为「有无核对」（消费登记缺失可查，与第 8 节一致性不可查），不得以「无基准下一切构件皆自创」机械推论充数；降级口径记入缺陷报告维度覆盖声明节。

**第三步·辩护/修订**：有缺陷→委托 generator 按 `assets/prompt-defense.md` 逐条辩护或修订→修订后重跑机械脚本+再审计。**收敛上限 3 轮**；超限未决或双方立场冲突→升级 G2。

**审计文档面向纪律**：每轮审计意见与辩护裁定**完整落盘缺陷报告**（含辩护成立项及其理由，禁止只留在会话记忆里）——下一轮 auditor 以描述集/词典/缺陷报告等**文档为唯一输入**，不依赖会话上下文；新会话或更换 auditor 可无损接手（消除 resume 单点）。

## G2 争议仲裁（人工闸门·停等）

A/B 结论一致（审计通过或辩护全部成立）→自动通过，manifest 登记「未触发」。**存在争议→停等**：呈双方立场+证据给用户人工裁定——核心规则争议不可由第三个模型裁决（内核 §5.2 硬禁令）。裁定结论与理由记入 manifest 与缺陷报告仲裁节。

## S5 结构把关（可降级）

按 `assets/checklist-visual-review.md` 执行可视化三步（全局拓扑/局部语义穿透/规则路径回溯）+四种 OWL 属性特征校验（Functional/InverseFunctional/Transitive/inverseOf——业务语义问句逐个过，内核 §6）。无 Protégé 环境（默认）→跑 `report_topology.py` 出文本拓扑报告对照 checklist 执行，manifest 登记降级；建议同时把拓扑报告呈用户做人工抽核（专家审图能暴露 AI 常漏的逻辑错误）。

## S6 业务验收

按 `assets/tpl-golden-cases.md`：专家黄金用例三元组（场景+核心问题+预期结果）≥5 条（专家缺位时由主会话代拟并标注「代拟待专家确认」）→AI 扩展边缘/异常/压力矩阵→逐条执行（SPARQL 查询/reasoner 代入/描述集回溯）→失败三类归因（模型缺陷→回 S3 / 用例错误→修用例 / 规则冲突→G2；根因在执行引擎能力边界时登记第四类「执行环境限制」，修执行器不改本体）→通过率 ≥80% 方可进 G3，迭代向 90% 收敛。产出 `黄金用例集.md` + `测试报告.md`。

**执行器**：`scripts/run_golden_cases.py ONTOLOGY.ttl CASES.json [--only ID ...] [--json-output FILE] [--engine pellet|hermit]`（--engine hermit=DL 对照档：HermiT 拒跑 SWRL builtin 且 datatype 需 ignore 参数，仅 DL 层对照可用，见 `references/reasoner-limits.md` 限制⑬）。用例外置 JSON（schema 1.0）=专家黄金集输入接口的形式化：`meta`（schema_version/scenario/source）+ `cases[]`（id/kind/seed/gen/desc/ttl/expect；kind∈expert_seed/ai_edge/ai_negative/ai_stress；exempt 条目登记不执行）；断言枚举与 arity 见脚本 `ASSERT_ARITY`。`--check` 仅做 schema 校验（exit 0/1，可入单测）。字段接口详见 `assets/tpl-golden-cases.md` §5。

**实例级推理执行纪律（限制⑩⑭；机制、证据与削减实验方法详见 `references/reasoner-limits.md`）**：两项引擎处置均已内置执行器默认档——具名 datatype 剥离（`strip_named_datatypes()`，默认开启，`--no-strip` 仅调试档；内联匿名 oneOf 保留，实例层有真强制力）与 canonical 确定性档（`canonicalize_base()`，一次性 ~60s；S6 结果跨进程可复现，「≥2 轮零 FAIL」具备确定性含义）。操作纪律：①**首跑失败禁止盲改本体/用例**——先跑 canonical 档两次确认确定性，再做削减实验定根因（方法=reasoner-limits §六）；漂移期的单次 PASS/FAIL 均不构成证据。②黄金集须含**多规则并发压力用例**作为 builtin 数值规则的语义验收主载体（孤立单规则场景存在引擎级确定性失灵，FAIL 时转 exempt 第四类）。③本体文件不因引擎限制改动；facet 实例校验由 SHACL 层（R4，`scripts/derive_shacl.py`+`validate_shacl.py`）+数据管线承接。

**执行预算**：黄金集 >60 条时改用 `--only` 分片分组执行，每组时长登记 manifest——canonical 档每进程含一次性 canonicalization 开销（约 60s），大集一次全量执行进度不可观察、失败即全量重跑；分片兼具失败隔离与预算可见。

## G3 验收终审（人工闸门·停等）

呈测试报告+8 件套齐套清单（骨架=`assets/tpl-gate-submission.md` §G3）给用户终审；结论记入 manifest。通过后进入收卷三步（见交付节）。

## 交付物（8 件套）与 manifest 收卷

**8 件套契约区**（落 `交付物/` 根，对外消费只进这里）：`ontology.ttl` / `建模方案.md` / `29句话描述集.md` / `术语词典.md` / `缺陷报告.md` / `黄金用例集.md` / `测试报告.md` / `run-manifest.md`。**第 9 件（可选）=生产化交接说明**（`assets/tpl-production-handoff.md`：层间接口契约+推理时长预算+引擎限制消费注意+下一版本待办）——本体进入生产化消费时必产；裁剪须在 manifest 登记理由。

**收卷三步**：①**净化**——实验产物移入 `实验/`，可再生副本登记后可清理（原始实验结果 json 保留为证据）；②**打包**——`交付物/` 齐套核对+每文件一行消费者视角说明；③**登记**——manifest 增「打包与净化记录」节。机械执行用 `scripts/closeout_check.py`（齐套核对+敏感模式扫描+计数一致性+净化清单，一命令出收卷自查报告；敏感词表外置传入，词表本身不入 skill 资产）。

**计数单一事实源**：构件计数（类/对象属性/数据属性/规则/Concept 等）唯一权威=`建模方案.md` 计数登记节（以机械实测回填）；测试报告/manifest/呈报件引用该节口径、**不手抄数字**——手抄即产生多份会漂移的计数。

manifest 收卷补全：入口模式/裁剪登记/博弈轮次与收敛轨迹/L3 档位（swrl_verified）与降级项/S5 降级/消费链路绑定表/G1-G3 结论/敏感自查结果（grep 机构名/证件号/手机号模式，命中即脱敏）/**交付分级**（内部协作版 vs 外部分享版，后者须过 `references/sensitivity-rules.md` 脱敏口径后才可出）/**盲测勾稽位**（若 run 为盲测模式：还原率对照报告〔`assets/tpl-restoration-report.md`〕是否完成+双口径数据+误报/漏检清单——缺对照报告不得收卷）/**打包与净化记录**（收卷三步产物+closeout_check 报告位置）。

## 铁律

1. **人工闸门必须停等**——G1/G2/G3 呈报后等用户结论，禁止代答代签；用户显式授权代跑时，代跑理由与「授权代跑」字样记入 manifest。
2. **产物永不写入 skill 目录**——skill 资产目录（SKILL.md/references/assets/scripts）与 agent 定义只放机制本体；一切 run 产物入 run 目录。
3. **敏感纪律**——`references/sensitivity-rules.md` 全程生效：skill 资产永不写真实业务数据；真实业务 run 必须在受控目录（不进版本控制/不进入对外分发通道）；模板配例一律虚构中性。
4. **双模型异构（平台中立纪律）**——生成与审计两角色必须由**不同模型**承担，禁止同模型自审；Claude Code 参考实现=generator（opus）/ auditor（sonnet），其他平台按同构纪律配置不同模型（适配说明见套件 `agents/README.md`）；模型别名与底层模型映射若变更，异构性须复核。
5. **不补造**——输入未覆盖的知识不进本体；缺失登记「待确认项」而非编造；生成物必须过质检才可交付——编译官不自带正确性保证。
6. **方法论内核是执行权威**——执行依据=`references/methodology-core.md`（自包含，源自《本体驱动的AI数据管理》公开方法论）；发现内核与来源方法论表述冲突时，不得径改径行，回报维护者裁定。

## 资产索引

- `references/`：**methodology-core（方法论内核，自包含执行依据，S1-S6/G1 判据细节）** / **reasoner-limits（引擎限制①-⑭+削减实验矩阵+降级链+L2/L3 分工，自包含）** / **s1-handoff-contract（ingest→S1 接缝契约唯一接口权威：五类 affordance〔unit_type/图样保真/verification_status/personal_info_regions/md_heading〕+ S1 消费协议 §六 + 溯源链 §五）** / fibo-guide（公共层对齐）/ structure-patterns（四层结构骨架+SWRL 编译形态约束 §七，[verified]/[provisional] 两级标注）/ sensitivity-rules（敏感纪律）/ structured-input-mapping（结构化输入→29 句集通用映射方法+示例，S1' 机械映射档；形态维分派+溯源携带与 s1-handoff-contract 互补）
- `assets/`：tpl-29-sentences / tpl-term-dict / prompt-generator / prompt-auditor / prompt-defense / tpl-defect-report / tpl-golden-cases / tpl-ontology-doc / checklist-visual-review / tpl-gate-submission（G1/G2/G3 呈报件骨架）/ tpl-production-handoff（生产化交接说明，第 9 件可选）/ tpl-restoration-report（盲测还原率对照报告，收卷勾稽位必产物）/ tpl-patch-schema（R2 增量 patch 编辑操作 JSON 契约，schema 1.0）/ tpl-shacl-shapes（R4 SHACL shapes 派生与校验契约，shapes schema 1.0）/ tpl-query-templates（D3c SPARQL Read 查询模板派生契约，query-templates schema 1.0）
- `scripts/`：validate_ontology.py（L1+L2，exit 0/1/2）/ check_consistency.py（L3 reasoner 三级降级链，exit 0/1/2）/ report_topology.py（S5 文本拓扑）/ run_golden_cases.py（S6 执行器，canonical 确定性档内置）/ closeout_check.py（收卷自查：齐套+敏感模式+计数一致+净化清单，exit 0/1/2）/ incremental_patch.py（R2 增量 patch 引擎：编辑操作→draft+L1/L2+回归守护+版本 diff，不覆盖权威，exit 0/1/2）/ derive_shacl.py（R4 TTL→SHACL shapes 派生，纯 rdflib，exit 0/1/2）/ validate_shacl.py（R4 pyshacl 实例级数据完整性校验，exit 0/1/2）/ derive_sparql.py（D3c TTL→SPARQL Read 查询模板库派生，纯 rdflib 内置 SPARQL 1.1，exit 0/1/2）
- agents：ontology-generator（S3/S4 辩护）/ ontology-auditor（S4 审计，只读）
- 姊妹 skill：ontology-ingest（上游异构文档进料：PDF/图片/Excel/Word/PPT→萃取原料包，I0-I3+IG1 轻停等，喂入本 skill S1 入口 (a)）/ ontology-review（下游专家审阅+意见回流）/ ontology-simulate（下游 what-if 模拟+A/B 实证）
