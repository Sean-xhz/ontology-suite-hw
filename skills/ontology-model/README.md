# ontology-model：自动化本体建模 skill

> 把「7+1」29 句话业务描述集编译为符合 W3C 语义规范（RDF/OWL/SKOS/SWRL）的结构化本体模型（Turtle），全程带主动语义校验与人工闸门。
> 当前版本见 SKILL.md frontmatter；版本历史见 `CHANGELOG.md`。方法论执行依据=`references/methodology-core.md`（自包含内核）；ingest↔S1 接缝接口权威=`references/s1-handoff-contract.md`。
> **本文件=人类手册**（三受众拆分：SKILL.md=LLM 执行契约 / README=人类手册 / CHANGELOG=版本历史）。

## 一、解决什么问题

其他业务场景需要快速完成初期本体建模时，不依赖「LLM 即兴发挥」，而是走一条**可复现、可校验、可审计**的管线。两项核心能力：

1. **语义转化**：自然语言业务描述（29 句话框架）→ RDF/OWL/SKOS/SWRL 形式化构件，每个构件可回溯到输入源句
2. **主动校验**：生成过程中检出规则冲突、关系矛盾、属性特征冲突、datatype 陷阱——机械脚本（形式层）+ 双模型博弈（语义层）+ 推理机（一致性层）三道防线

## 二、架构：三层边界

```
┌─ 人工争议层 ─ G1 准入 / G2 仲裁 / G3 终审（停等，禁代签）
├─ LLM 语义层 ─ ontology-generator 生成/辩护 ⇄ ontology-auditor 审计（须不同模型）
│               四元组缺陷报告；博弈 ≤3 轮；Claude Code 参考实现=opus/sonnet
└─ 机械形式层 ─ validate_ontology.py（L1/L2 结构）+ check_consistency.py（L3 Pellet/HermiT）
                + report_topology.py（S5 文本拓扑）；error 直返不占博弈轮次
```

分工原则：脚本做机械操作，LLM 做语义操作，人只做业务裁量与方法论裁定。技术事实争议（引擎行为/规范语义）由主会话构造**最小实验实测定案**，以证据+结论留 G2 备案，不消耗人工仲裁。

## 三、管线速览（S0-S6 + G1-G3）

| Stage | 内容 | 产物 |
|---|---|---|
| S0 | 准入评估：定入口模式 (a)/(b)/(c)，所有裁剪显式登记 | run-manifest.md |
| S1 | 三维萃取（对象-任务-规则），仅入口 (a)；统一模板结构化输入走 S1' 机械映射档 | 萃取草稿 |
| S2 | 「7+1」29 句话组装+术语词典 | 29句话描述集.md / 术语词典.md |
| **G1** | **人工闸门**：四标准（清晰/正确/完备/极简）两段评审，冻结描述集 | G1初审checklist.md |
| S3 | generator 编译 29 句→Turtle（只读输入契约，编译官不自带正确性保证） | ontology.ttl / 建模方案.md |
| S4 | 机械脚本先行→auditor 三维度审计（四元组）→generator 辩护/修订，≤3 轮 | 缺陷报告.md |
| **G2** | **人工闸门**：A/B 争议仲裁（一致时自动通过，备案留痕） | manifest 登记 |
| S5 | 结构把关：可视化三步 checklist（无 Protégé 降级文本拓扑） | S5拓扑报告.md |
| S6 | 黄金用例业务验收：专家种子+AI 扩展矩阵→实例级推理→四类失败归因→80%→90% 闭环 | 黄金用例集.md / 测试报告.md |
| **G3** | **人工闸门**：验收终审（含代拟用例的专家确认） | manifest 收卷 |

**入口模式**：(a) 原始业务资料→全管线；(b) 已有 29 句描述集→跳 S1（含基线迭代变体）；(c) 既有 TTL→只跑 S4 审计起。盲测对照=辅助验证模式（非默认路径，以历史人工方案为对照基准校准能力时启用）。

**异构文档进料（入口 (a) 前置）**：原始资料若是 PDF/图片/Excel/Word/PPT 等非纯文本形态，可先经姊妹 skill **`/ontology-ingest`** 做「萃取就绪的保真」进料——LLM 整页布局感知转录为主路径（每视觉单元必过）+ 机械渲染/inventory/substrate/交叉校验为护栏，产「萃取原料包」（清洁保真 MD + canonical manifest + attachments），再喂入本 skill S1。

**接缝契约（`references/s1-handoff-contract.md`＝接口权威）**：ingest 产出与 S1 消费在契约层共同设计，非「产 md、读 md」扔过墙。S1 按五类 affordance 消费——① **形态维 `unit_type`**（与内容特征维 `semantic_hint` 正交）分派消费方式：图样类（flow-diagram/ui-interaction/architecture-diagram/chart）**Read 原图**提炼流程语义（OWL-S/BPMN2.0 IOPE+拓扑），文字类读清洁 md；② **图样保真**：流程图/交互图/架构图嵌原图+图内文字照录，拓扑解读留 S1 多模态，不转文字扁平化；③ **置信度 `verification_status`**（substrate-exact/render-transcribed/image-only-transcribed）校准 G1 怀疑度；④ **个人信息精确位 `personal_info_regions`** 供 S2 精确脱敏 checklist；⑤ **溯源映射 `md_heading`**（机械标题↔LLM 语义标题桥接）打通 `source→section→描述句→TTL` 溯源链。解析层照录不脱敏，脱敏仍在 S1→S2（`references/sensitivity-rules.md` §四）；hint+unit_type 加速识别但不替代 S1' 逐节复核，适用判定不降级。

**交付 8 件套**：ontology.ttl / 建模方案.md / 29句话描述集.md / 术语词典.md / 缺陷报告.md / 黄金用例集.md / 测试报告.md / run-manifest.md；第 9 件（可选）=生产化交接说明（进入生产化消费时必产）。

## 四、如何使用

触发：`/ontology-model` + 场景资料或描述集路径。

**run 根目录（runs_root）解析顺序**：①调用时显式指定 → ②环境变量 `ONTOLOGY_RUNS_ROOT` → ③下方「环境与目录约定」默认。run 目录=`<runs_root>/<场景名>_<YYYYMMDD>/`，按三区结构（交付物/过程/实验）组织。**真实业务敏感场景必须指定受控目录**（不进版本控制/不进入对外分发通道；S0 登记，见 `references/sensitivity-rules.md`）。

### 人的四个输入点（按价值排序）

1. **G1 准入评审**：业务专家对 29 句话描述集做四标准复核+待确认项裁定——输入契约质量决定全管线质量上限
2. **S6 黄金用例**：**业务专家直接提供用例三元组（场景+核心问题+预期结果）≥5 条为首选路径**；专家缺位时主会话代拟并强制标注「代拟待专家确认」（推导源限定为描述集核心业务问题清单，禁止从本体反推；负向用例由异构 auditor 契约补位），G3 终审时专家确认
3. **G2 争议仲裁**：仅业务裁量与方法论修订需人工；技术事实走实测定案通道
4. **G3 验收终审**：测试报告+拓扑报告人工抽核，通过后交付

## 五、语义覆盖矩阵（7 类语义×承接形态）

| 描述集类别 | 承接形态 | 构件/落位 |
|---|---|---|
| 1 对象描述类 | **编译进 TTL** | owl:Class / DatatypeProperty / ObjectProperty（domain/range） |
| 2 分层约束类 | **编译进 TTL** | subClassOf / equivalentClass / AllDisjointClasses / Restriction / cardinality |
| 3 术语类 | **编译进 TTL** | skos:Concept（prefLabel/altLabel/definition/broader） |
| 4 控制规则类 | **编译进 TTL** | swrl:Imp + 结论类 disjoint；违反处置动作（4.3）登记于 md 处置档 |
| 5 流程活动类 | **md 扩展位登记** | BPMN2.0+OWL-S（IOPE）扩展位；四要素表进建模方案 |
| 6 权限管控类 | **md 扩展位登记** | ODRL 扩展位；角色-动作三档表进建模方案 |
| 7 CRUD 查询类 | **Read 形式化激活（D3c）+ C/U/D md 扩展位** | derive_sparql.py 产 7 类 SELECT 模板库；业务查询意图表由 S6 黄金用例消费；C/U/D 留后续 R6 |

- 「+1 目标评估」=消费链路治理登记（md，G1 必填，反博物馆），不产本体构件。
- 清单参数运算与数值评分=**不承接**（数据层/应用层职责，本体只登记结构位与受控词表）。
- **扩展位路线图**：SPARQL **Read 取知已 skill 级激活**（D3c，derive_sparql.py；真实业务 run 级消费仍须 G1 范围评审）；BPMN2.0/ODRL/SPARQL C/U/D 形式化为 MVP 后能力，无排期承诺；启用条件=消费场景提出形式化硬需求且经 G1 范围评审。

## 六、验证体系（L1-L4）

| 层 | 工具 | 覆盖 |
|---|---|---|
| L1 | rdflib | Turtle 语法解析+标准前缀 IRI 字节级校验（L1-PREFIX） |
| L2 | validate_ontology.py | 循环继承/属性特征矛盾/domain-range 悬挂/disjoint∧subClassOf/具名枚举 datatype 陷阱/SWRL 结构 |
| L3 | check_consistency.py（owlready2+Java） | Pellet/HermiT 一致性推理含 SWRL；三级降级链（Pellet 全量→HermiT→剥离 SWRL），swrl_verified 字段登记档位 |
| L4 | pySHACL（R4）+ Protégé | **pySHACL 已启用（R4）**：derive_shacl+validate_shacl 实例级数据完整性（facet/基数/唯一性）；Protégé 仍可选 |

**引擎限制**：限制①-⑭清单、削减实验矩阵、三级降级链与 L2/L3 分工的自包含登记=`references/reasoner-limits.md`（执行与失败归因必读；引擎版本变更须逐项复核）。要点：限制⑨=具名枚举 datatype Pellet 值空间判空→唯一兼容形态=range 内联匿名 oneOf（补 rdf:type rdfs:Datatype 为标准推荐形）；限制⑩=facet 具名 datatype 模式层兼容/实例层假不一致→S6 执行器剥离降级（内联 oneOf 保留，实例层有真强制力），实例级 facet 校验由 R4 SHACL 层承接；限制⑭=canonical 确定性档内置+孤立场景失灵由并发压力用例承载验收。

### 增量 patch（R2）

**何时用**：既有本体的简单修改——label/注解、受控枚举值、增删类/属性、规则级编辑——不必触发全量重建（入口 (c) 重编译）。R2 消费结构化编辑操作 JSON，rdflib 增量修改产 **draft TTL + patch-report.json**，附 L1/L2 零新增 error 闸门 + 黄金用例受影响子集回归守护 + 语义版本 diff。R2 是 D4 拖拽编辑的机械 patch 地基（前端产 patch JSON，R2 机械执行）。

```bash
python3 scripts/incremental_patch.py <baseline.ttl> <patch.json> \
    [--golden cases.json] [--with-l3] [--output-draft PATH] [--report PATH] \
    [--bump auto|major|minor|patch] [--strict] [--regression-full] [--cache-dir DIR]
# 套件统一 CLI：ontology_cli.py model patch <baseline.ttl> <patch.json> [...]
```

**exit**：2=应用前输入错（schema/sha 错配/项编码错/操作目标缺失，不产 draft）；0=released；1=blocked（L1/L2 新增 error / 回归检出翻转 / MAJOR 无守护 / L3 不一致）。exit 0/1 均产 draft+report（blocked draft 供检视）。

**纪律边界**：① **draft 非权威**——意见单 schema §四.2「一切形式化修改走入口 (c)」零改动，R2 产 draft 携带 `entry_c:pending_audit`，晋升仍走入口 (c) S4 审计→G2/G3→人工闸门，R2 永不执行晋升。② **零回写**——baseline/golden/patch 三文件 sha256 前后断言 + 输出 realpath 碰撞守卫，默认输出落 cwd 不进 run 目录。③ **与全量重建分界**——规则编码变更（MAJOR）无 `--golden` 回归守护→blocked 转入口 (c) 全量审计；R2 不是绕过闸门的捷径。④ **保真边界**——rdflib 序列化丢失原文件注释，draft 为机械中间产物，晋升时历史注释合并由编排器/人工承接。

契约全文（patch JSON schema 1.0 + 8 操作目录 + 项编码 + 虚构配例）=`assets/tpl-patch-schema.md`。「意见→编辑操作」语义翻译由外接编排器（LLM/D4 前端/手工）承担，R2 只机械执行不含 LLM 调用。

### SHACL 约束校验（R4）

**何时用**：实例级数据完整性校验——数值上下界/正则 pattern/必填基数/functional 多值/限定基数/hasKey 唯一性。OWL 开放世界「未推出≠否定」+ 限制⑩下 Pellet 剥离 facet 后推理器侧永不校验实例值，check_instance E08 对具名 facet datatype 只 W08 放行；R4 用 W3C SHACL（封闭世界数据完整性）补此盲区，是套件内首个实例级 facet/基数/唯一性强制器，纯 Python 无 Java（skip-java 也可跑），R6 实例化管道前置地基。

```bash
python3 scripts/derive_shacl.py <ontology.ttl> [--output-shapes PATH] [--report PATH]
python3 scripts/validate_shacl.py <data.ttl> <shapes.ttl> \
    [--json-output FILE] [--derivation-report FILE] [--strict] [--focus IRI]
# 套件统一 CLI：ontology_cli.py model shapes <ontology.ttl> [...] / model shacl <data.ttl> <shapes.ttl> [...]
```

**exit**：derive 0=成功 / 1=IRI 碰撞或零回写失败 / 2=输入错；validate 0=无 error（非 strict 放行 warning）/ 1=有 error（strict 下 warning 也致 1）/ 2=输入错或 pyshacl 缺失。

**四设计取舍**（实证驱动，正确性必需）：R-a 定义类展开（qualified cardinality onClass 定义类展开 equivalentClass，修复输入侧未物化漏检）/ R-b 逆路径（inverseOf 属性 sh:alternativePath 双向匹配）/ R-c 子类闭包（sh:class 改具名子类闭包 sh:or，对齐 check_instance E06，SHACL 不得比它更严）/ R-d 数值 datatype 容忍（decimal/double/float 不发 sh:datatype，修复 compile int→xsd:integer 误报）。

**纪律边界**：① shapes 非权威·可再生（源 TTL 不变则字节不变，TTL 变更后须重派生）；② 零回写（源 TTL sha 前后断言+realpath 守卫，默认落 cwd）；③ 确定性（canonical-copy-rebind+无时间戳，序列化前绝不喂 pyshacl）；④ TTL-direct 派生（不动签名提取，避 T4 冻结漂移；provenance 经 rdfs:comment 源句不断链）。

**分界**：与 S6 推理验收正交（SHACL=输入完整性闸门，不接入 golden 集——golden 15 active 仅 2/15 conform，开放世界推理 fixture 设计使然）；与 check_instance 正交互补（零臆造 vs 数据完整性，T3 组合=check_instance→compile→validate_shacl→simulate_reason）。

契约全文（映射表+四取舍+unmapped 登记+exit 三态+虚构配例+金额 JSON 数值契约）=`assets/tpl-shacl-shapes.md`。

### SPARQL 查询模板（D3c）

**何时用**：本体建好之后，下游 Agent「经 SPARQL 取知」（methodology-core §8.1）需要可执行查询脚手架。D3c 从 TBox 机械派生 **7 类 SELECT 模板库**（class-list 列举 / key-lookup 标识精查 / property-get 取值 / enum-filter 受控值过滤 / facet-filter 数值范围 / op-join 关联遍历 / derived-query 推理结论），是 model 覆盖矩阵「7 CRUD 查询类」SPARQL 扩展位的 **Read 取知形式化激活**。纯 rdflib 内置 SPARQL 1.1（prepareQuery 语法自检 + graph.query 可执行），无 Java、无 LLM、**零新增依赖**（rdflib 已在核心 tuple），skip-java 也可跑。与 derive_shacl（R4）完全同构：TTL-direct 派生、非权威可再生、零回写、确定性 canonical。

```bash
python3 scripts/derive_sparql.py <ontology.ttl> [--output-json PATH] [--output-md PATH] [--report PATH]
# 套件统一 CLI：ontology_cli.py model queries <ontology.ttl> [...]
```

**exit**：0=派生成功（gap 登记不阻塞）/ 1=template_id 碰撞或 prepareQuery 语法自检失败或零回写失败 / 2=输入错（文件缺失/TTL 解析失败/输出==源/无 base ns）。

**五设计取舍**：D-a TTL-direct（直接读 ontology.ttl 本地解析词汇，一步自包含，不改签名提取避 T4 漂移）/ D-b Read 取知 MVP（只产 SELECT；C/U/D 登记 extension_slots 留后续 R6，示例 §7.4 删除悬置不补造）/ D-c 子类闭包 property path（class-list/derived-query/key-lookup 用 `a/rdfs:subClassOf*`，个体仅类型化子类不漏检，R-c 对齐）/ D-d derived 类分流（SWRL head 结论类→derived-query，derived_flag+需先物化注记，禁入实例输入但可查推理结论）/ D-e 参数化+IRI 守卫（数据值永不进查询文本，?var 参数化，受控枚举值域作 params.enum_values 元数据；嵌入 IRI 过 IRI_UNSAFE_RE）。

**纪律边界**：① 模板库非权威·可再生（源 TTL 不变则字节不变，TTL 变更后须重派生）；② 零回写（源 TTL sha 前后断言+realpath 守卫，默认落 cwd）；③ 确定性（JSON sort_keys/indent=1+尾换行，MD LF，零时间随机，全排序，template_id 确定性后缀命名，禁 bnode 随机标签泄漏）；④ TTL-direct 不动签名提取（rdf_list/union/子类闭包/derived 判定本地重实现，不反向 import review/simulate）。

**机械/LLM 分界**：CLI 只产**结构脚手架**（原子 SELECT 模板）；**业务查询意图**（票据 §7.2 背书链/受理结论/可贴现判定、§7.5 贴现池组合查询）由主会话 md 补写——绑定模板参数 + 多模板拼接 + ORDER BY + 业务阈值 → S6 黄金用例消费（「查询模板随规则消费场景补写」口径不变）。组合查询非 CLI 职责。

**分界**：与 derive_shacl 同构正交（shapes=封闭世界数据完整性，validate_shacl 消费；query-templates=取知查询脚手架，Agent/主会话消费）；与 check_instance 正交（签名词汇封闭防臆造 vs 取知查询，derived 类禁入输入 E04 但可查结论）；与 ontology-simulate what-if 联动（物化实例后 derived-query 查推理结论，互补消费形态，**零代码依赖**文档联动）。

契约全文（7 kind 映射表+五取舍+gaps/extension_slots 登记+exit 三态+虚构票据配例计数锚+执行三态）=`assets/tpl-query-templates.md`。

## 七、环境与目录约定

**依赖**：python3（3.9+）+ rdflib + owlready2 + pyshacl（R4 SHACL 校验，==0.29.1；derive_shacl/derive_sparql 派生仅需 rdflib——D3c 用 rdflib 内置 SPARQL 1.1，零新增依赖）+ JRE（HermiT 需 Java ≥17；**Pellet 需 Java ≥25**——`find_java()` 自动选本机最高版本，环境变量 `OWL_JAVA_EXE` 可显式覆盖）。node 仅 ontology-review 回归层语法检查项需要。L3 不可用时自动降级 L2 并登记 manifest，不阻塞交付；R4 SHACL 与 D3c SPARQL 纯 Python 无 Java，skip-java 环境也可跑。

**目录约定（按部署环境）**：

| 环境 | runs_root 默认 | 敏感场景受控目录 |
|---|---|---|
| 知识库集成环境 | `<知识库根>/runs/`（或 `ONTOLOGY_RUNS_ROOT` 指定） | 版本控制忽略区 |
| 独立部署/套件 | 建议 `./runs/`（或 `ONTOLOGY_RUNS_ROOT` 指定） | 任何不进版本控制、不进入对外分发通道的目录 |

**回归与验收**：套件级统一验收（T0-T15）以 `examples/` 虚构示例载体为 fixture，入口=`scripts/run_suite_tests.py`（`--skip-java` 可跑纯 Python 档）；ontology-review `scripts/self_test.py --runs <fixture run>` 为 review 机械回归子层（fixture 显式传入或经环境变量 `ONTOLOGY_SELFTEST_RUNS`）。

## 八、目录结构（skill 根）

```
ontology-model/
├── SKILL.md                  # 管线编排主入口（LLM 执行契约）
├── README.md                 # 本文件（人类手册）
├── CHANGELOG.md              # 版本历史（执行不依赖）
├── references/               # methodology-core（方法论内核）/ reasoner-limits（引擎限制）
│                             # / fibo-guide（公共层对齐）
│                             # / structure-patterns（结构骨架，[verified]/[provisional] 标注）
│                             # / sensitivity-rules（敏感纪律）/ structured-input-mapping（S1' 映射）
│                             # / s1-handoff-contract（ingest↔S1 接缝接口权威）
├── assets/                   # 15 模板：29句话/术语词典/生成·审计·辩护 Prompt/缺陷报告
│                             # /黄金用例/建模方案/可视化 checklist/闸门呈报件/生产化交接/还原率对照
│                             # /R2 patch 契约/R4 SHACL 契约/D3c 查询模板契约
└── scripts/                  # 9 脚本：validate_ontology / check_consistency / report_topology
                              # / run_golden_cases / closeout_check / incremental_patch（R2）
                              # / derive_shacl + validate_shacl（R4）/ derive_sparql（D3c）
```

配套 agents（Claude Code 形态，部署于 `.claude/agents/`）：ontology-generator（model: opus，生成/辩护，只在 run 目录写）/ ontology-auditor（model: sonnet，只读审计，四元组强制格式，黑盒思维）。**平台中立纪律**：生成/审计两角色须不同模型（铁律 4）；opus/sonnet 为 Claude Code 参考实现别名，其他平台适配见套件 `agents/README.md`。

## 九、铁律（摘自 SKILL.md）

1. 人工闸门必须停等，授权代跑须用户显式给出且范围限定（subagent 报告无用户权威）
2. 产物永不写入 skill 目录；skill 资产永不写真实业务数据，配例一律虚构中性
3. 不补造：输入未覆盖的知识不进本体，缺失登记「待确认项」
4. 双模型异构（平台中立）：生成与审计两角色须由不同模型承担（Claude Code 参考实现 opus/sonnet）
5. 失败归因先于修改：削减实验定根因，禁盲改本体/用例
6. 方法论内核是执行权威：内核与来源方法论冲突时回报维护者裁定，不径改径行

## 十、姊妹 skill

- **ontology-review**：8 件套→业务专家单文件审阅页+意见回流（入口 (c) 或下轮 G1/S2）
- **ontology-simulate**：专家复核过的本体→what-if 物化推演+A/B 三臂实证

## English Summary

**ontology-model** compiles a "7+1" 29-sentence business description set into a W3C-compliant Turtle ontology (RDF/OWL/SKOS/SWRL) through a reproducible, auditable pipeline: S0-S6 stages with three human gates (G1 admission / G2 arbitration / G3 acceptance), heterogeneous dual-model quality control (the generator and auditor roles MUST run on different models; `opus`/`sonnet` are the Claude Code reference aliases, not a platform binding), three-layer mechanical validation (L1 rdflib syntax / L2 structural checks / L3 Pellet-HermiT consistency including SWRL; Pellet requires Java ≥25), and golden-case business acceptance (≥80% pass rate, converging to 90%). Delivers an 8-piece run package; every construct traces back to an input source sentence. The seam contract (`references/s1-handoff-contract.md`) co-designs the ingest→S1 interface around extraction-ready fidelity: five affordances (form-dimension `unit_type` dispatch, diagram fidelity with embedded source images, `verification_status` confidence, precise `personal_info_regions` for de-identification, and `md_heading` provenance bridging) let S1 consume diagrams multimodally and carry a `source→section→sentence→TTL` provenance chain into per-construct annotations. Execution contract: `SKILL.md`; human manual: this file; version history: `CHANGELOG.md`.
