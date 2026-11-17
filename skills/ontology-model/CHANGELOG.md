# ontology-model CHANGELOG

> **版本约定**：semver（MAJOR.MINOR.PATCH）——MAJOR=执行契约不兼容变更（Stage/闸门/交付契约改变）；MINOR=新增能力或条款；PATCH=措辞与修正。frontmatter `metadata.version` 为当前版本（skill schema 不支持顶层 version 属性，登记于 metadata）。子协议版本（如 golden-cases schema 1.0、SWRL 规范 v2）在对应版本条目登记，不随 skill 版本号联动。
> **本文件=构建档案层**（C1/N11 三受众拆分：SKILL.md=执行契约 / README.md=人类手册 / CHANGELOG.md=档案）。执行不依赖本文件；「实证证据登记」节为从执行资产迁出的构建史与证据链，开源发行可选携带。历史指针中的 vault 构建区路径仅为溯源记录，不构成运行依赖。

## 1.7.0（2026-11-17）— R4 SHACL 约束校验层（短期 CLI 能力增强第二项）

- **R4 SHACL 约束校验层**：新增 `scripts/derive_shacl.py`（TTL→SHACL shapes 派生，纯 rdflib，无 Java/无 pyshacl/无 LLM）+ `scripts/validate_shacl.py`（pyshacl 实例级数据完整性校验）。SHACL（封闭世界数据完整性）补 OWL（开放世界逻辑一致性）盲区：限制⑩下 Pellet 剥离 facet 具名 datatype 后推理器侧永不校验实例值，check_instance E08 对具名 facet datatype 只 W08 放行（实证 faceAmount=-5/billNumber="随便写" 当前通过）——R4 是套件内首个实例级 facet/基数/唯一性强制器，纯 Python 无 Java（skip-java 也可跑），R6 实例化管道前置地基，激活 README §六 L4 既有 pySHACL 预留位。
- **TTL-direct 派生（规格 refine，审批级）**：shapes 从 ontology.ttl（TBox）直接派生，非从 29 句话描述集——TTL 是 G1 冻结+S3 编译+S4 审计+L3 返修定版，含描述集没有的精确化（正则位数/InverseFunctional→hasKey 替代/枚举内联化/qualified cardinality 裁量），从描述集派生绕过裁定链、重新引入已消解歧义。provenance 经 rdfs:comment 源句编号（SOURCE_RE）不断链。不改 extract_signature/parse_ttl/review_extract（避 T4 冻结签名漂移）。
- **四设计裁定**（实证驱动，正确性必需非可选优化）：R-a 定义类展开（qualified cardinality onClass 定义类展开 equivalentClass intersectionOf/hasValue/someValuesFrom，深度≤3，修复输入侧未物化漏检）/ R-b 逆路径（inverseOf 属性 path=sh:alternativePath(p, inversePath(q))，**独立 list 节点+谓词包裹**——path 节点本身不可为 rdf:list 否则 pyshacl 误判序列路径静默失效）/ R-c 子类闭包（sh:class 值约束改具名子类闭包 sh:or，对齐 check_instance E06 ancestors，SHACL 不得比它更严；hasKey SPARQL ?other 类型匹配同用闭包 UNION）/ R-d 数值 datatype 容忍（decimal/double/float range 不发 sh:datatype，compile int→xsd:integer 误报修复；minExclusive decimal 对 integer 数值提升比较实证成立）。
- **契约模板**：新增 `assets/tpl-shacl-shapes.md`（第 14 模板）——TBox→SHACL 映射表 + 四裁定 + unmapped 登记契约 + CLI/exit 三态 + 虚构票据配例（派生计数锚+校验三态）+ 金额 JSON 数值契约 + 边界分界（targetClass 无推理 limitation/与 check_instance 正交/与 S6 分界/R2 解耦）。
- **复用面**（只 import/重实现不改）：validate_ontology.VOCAB_NS/local_name（只读 import）；incremental_patch.serialize_draft 确定性配方（canonical-copy-rebind 同算法重实现，自有 header）；review_extract.rdf_list_items/union_class_members 算法（本地重实现，不 import 避 model→review 反向分层）；simulate_reason.compile_instance_ttl base 回推算法（TTL-direct 版，不 import 避顶层 owlready2）；check_instance 报告体例（pass/counts 对齐）。
- **纪律零改动**：check_instance 逻辑零改动（仅 W08/E08 注释指针「L2 承接」→「SHACL 层 R4 承接」，见 simulate 1.2.4）；SHACL 不接入 run_golden_cases/S6（golden 15 active 仅 2/15 conform，开放世界推理 fixture 设计使然，语义正交）；agents 零改动（五 agent 职责面不变）。shapes 非权威·可再生·零回写（源 TTL sha 前后断言+realpath 守卫+默认落 cwd）；确定性（canonical-copy-rebind+无时间戳+禁 bnode 随机标签，**序列化前绝不喂 pyshacl**——validate 篡改 shapes 图注入 owl 公理实证）。
- **SKILL.md 薄指针**：S4 第一步 SHACL 通道命令行 + S6 末句 facet 承接方措辞 refine + 资产索引 scripts/assets 各一条（不叠条款，契约细节在 tpl-shacl-shapes）。README §六 L4 行 pySHACL 启用 + R2 小节后「SHACL 约束校验（R4）」同构小节 + §七依赖 pyshacl。references/reasoner-limits.md 限制⑩ + §五表 facet 承接方措辞 refine（编号①-⑭稳定不动）。
- **子协议登记**：shapes schema **1.0** / derivation-report **1.0** / violations-report **1.0**（三独立子协议，不随 skill 版本联动）。pyshacl **==0.29.1** 精确钉住为核心 pip 依赖（照 owlready2==0.51 体例，升级须重跑 T12+实证矩阵）。
- **版本判据**：新增脚本+模板资产（能力面扩展），执行契约 Stage/闸门/交付零改动 → MINOR。
- **实证证据**：见下「实证证据登记 G 节」（E1-E20 规划期预验证 + 实施期正式脚本重跑：派生双跑字节一致+计数锚+8 例校验矩阵+补洞三态对偶+手工边界矩阵）。套件 T12 验收电池见套件 CHANGELOG/README v10。

## 1.6.0（2026-11-17）— R2 增量 patch 引擎（短期 CLI 能力增强首项）

- **R2 增量 patch 引擎**：新增 `scripts/incremental_patch.py`（机械 backbone，纯 rdflib 核心，顶层仅标准库+rdflib+同目录 rdflib-only 复用模块；owlready2/推理层经 run_one 函数内延迟导入）。消费结构化编辑操作 JSON（schema 1.0）→ rdflib 增量修改产 **draft TTL + patch-report.json**（不覆盖权威）→ L1/L2 零新增 error delta 闸门 + 可选 L3 + 黄金用例受影响子集回归守护 + 语义版本 diff。R2 是 D4 拖拽编辑的机械 patch 地基；「意见→编辑操作」语义翻译由外接编排器（LLM/D4 前端/手工）承担，R2 只机械执行不含 LLM 调用。
- **8 操作目录**：add_triple（幂等）/ remove_triple（目标必存）/ replace_literal（s 可选全图唯一匹配，oneOf 枚举改值高频形态）/ modify_label（PATCH 单值化）/ add_class / add_property（MINOR）/ remove_rule / replace_rule（MAJOR，规则级编辑绕开 bnode 寻址）。项编码契约：字符串一律 IRI（全 IRI/前缀名/裸 localname→默认 ns），字面量 dict，number/bool 仅 o 位，**`_:` 项一律拒绝**（bnode 跨 parse 不可寻址，实证 no-op）。
- **契约模板**：新增 `assets/tpl-patch-schema.md`（第 13 模板）——patch JSON schema 1.0 全文 + 操作目录 + 项编码 + 虚构票据配例（modify_label/replace_rule）+ exit 三态 + 纪律节 + 回归子集算法 + 保真边界。
- **三处设计裁定**（对原迭代清单两段 bump 规格的 refine）：① 版本 bump 三段 PATCH/MINOR/MAJOR（annotation→PATCH，结构→MINOR，规则→MAJOR）；② L1/L2 闸门=零新增 error（delta 口径，对齐基线迭代细则⑥；`--strict` 绝对档）；③ MAJOR 回归守护硬前提（MAJOR+无 --golden→blocked 转入口 (c)；MAJOR+无 Java→blocked；MINOR/PATCH+无 Java→降级登记放行）。
- **复用面**（只 import 不改）：validate_ontology.Validator（L1/L2 双侧 delta）/ run_golden_cases.run_one+canonicalize_base+find_java（回归双侧实跑）/ check_consistency.strip_swrl（MAJOR 闭包检测通道②）+ subprocess（L3）。规则级联删除按 simulate_reason._destroy_list/drop_rule **同算法图级实现**（不 import：其顶层 import owlready2 破坏 rdflib-only + model→simulate 反向分层）。
- **纪律零改动**：意见单 schema §四.2「一切形式化修改走入口 (c)」不变——R2 产 draft 携带 `entry_c:pending_audit`，晋升仍走入口 (c) S4 审计→G2/G3→人工闸门，R2 永不执行晋升。零回写三文件 sha256 断言 + 输出 realpath 碰撞守卫 + 默认输出落 cwd。
- **SKILL.md 薄指针**：S0 入口 (c) 增量通道 + S4 第一步增量修改通道命令行 + 资产索引 scripts/assets 各一条（不叠条款，契约细节在 tpl-patch-schema）。README §六后补「增量 patch（R2）」小节。references/reasoner-limits.md **不动**（复用⑩⑭既定机制，无新引擎限制）。
- **子协议登记**：patch JSON schema **1.0**（独立子协议，不随 skill 版本联动）；report schema 1.0。
- **版本判据**：新增脚本+模板资产（能力面扩展），执行契约 Stage/闸门/交付零改动（入口 (c) 纪律不变）→ MINOR。
- **实证证据**：见下「实证证据登记 F 节」（虚构票据 fixture 手工矩阵 + 契约边界 10/10 + MAJOR 全集回归 + L3 通道 + 双跑确定性 + 零回写）。套件 T11 验收电池见套件 CHANGELOG/README v9。

## 1.5.0（2026-11-12）— 盲测模板补齐 + 交付节瘦身 + 引擎归因成文 + 部署表述泛化

- **盲测还原率对照报告模板**：新增 `assets/tpl-restoration-report.md`（12 模板）——对照口径与方法（两侧形态差异/判定三档/双口径公式）→ 摘要结论 → 五矩阵（实体/关系/公理/规则库/切片）→ 误报清单 → 漏检三分类归因 → 形式化增量 → 盲测效力诚实声明 → 汇总计算表。S1 盲测段与 manifest 勾稽位补模板指针；收卷硬要求（双口径+误报/漏检清单）不变。
- **交付分级与通道节删除**：独立段（通道中立 boilerplate）删除；交付分级纪律（内部协作版 vs 外部分享版，后者须过 sensitivity-rules 脱敏口径）浓缩为 manifest 收卷补全清单一条目。通道描述（交付方式由调用环境自定）无执行语义，删除。sensitivity-rules §一§四 + 铁律 3 已覆盖分级实质。
- **引擎限制归因成文**：`references/reasoner-limits.md` 新增 §七「归因分类与升级路径判断」——限制①-⑭按根因分三类（A 绑定/序列化层〔owlready2/rdflib，升级推理机无效〕/ B 引擎实现缺陷〔Pellet 2.3.1，Openllet fork 可能修复部分但无实证不得预设〕/ C 引擎能力边界〔HermiT 终版无升级标的〕）+ ④特殊（W3C 正确序列化形态，非引擎坑）+ 升级纪律（规避形态均为标准合法形，引擎无关；版本变更属独立引擎维护批次须逐项复核+全量验收+重冻结）。
- **部署表述泛化（纯净化）**：README 目录约定表 vault 行具体路径（`01 AI 实验室/…`/`03 当前工作/`/Obsidian 品牌）泛化为中性占位（`<知识库根>/runs/`/版本控制忽略区）；review README 受控区惯例同步泛化。套件对外分发不暴露本地目录结构。
- **版本判据**：新增模板资产（能力面扩展）+ 交付节删除（契约面变更）→ MINOR。子协议（golden-cases schema 1.0/SWRL 规范 v2）不联动。

## 1.4.2（2026-11-11）— 文档结构治理：执行纪律浓缩 + 知识库叙述清理

- **限制⑩⑭内联段浓缩**：S6 两段引擎机制详述（Pellet facet 假不一致成因链/rdflib bnode 漂移链）浓缩为单一「实例级推理执行纪律」块——机制与证据已在 `references/reasoner-limits.md` 限制⑩⑭自包含（1.4.0 内核化时只切指针未浓缩，本次补齐）；SKILL.md 保留全部操作纪律（strip 默认档与 --no-strip 调试档/内联 oneOf 保留/canonical 内置默认与确定性含义/禁盲改→两次确定性确认→削减实验/漂移期单次结果不构成证据/并发压力用例主载体/孤立 FAIL 转 exempt 第四类/本体零改动/facet 校验 L2 承接）+ 指针。执行语义零变更。
- **知识库事件叙述清理**：删除与套件运行无关的 vault 知识库事件叙述（拆域迁移/旧路径修正事件/卡片治理修订事件/EL 条目引用/卡版本事件标记），保留构建溯源指针（vault 构建区路径/卡 ID 来源括注/部署约定）——C1/C3 既定边界（溯源记录非运行依赖）。涉及本 CHANGELOG 3 处 + methodology-core 2 处（卡版本事件标记）+ methodology-index（拆域叙述与来源文件名，用户套件侧编辑镜像回权威）。
- **版本判据**：条款浓缩与叙述清理，执行契约（Stage/闸门/交付）零改动 → PATCH。

## 1.4.1（2026-11-11）— Phase C 开源工程（N3 平台中立化 + N7 i18n）

- **N3 异构纪律平台中立化**：铁律 4 抽象为「生成与审计两角色必须由不同模型承担，禁止同模型自审」（方法论纪律不绑定平台别名）；opus/sonnet 降为 Claude Code 参考实现注记（S3/S4 委托点同步标注）；其他平台适配说明见套件 `agents/README.md`（套件级资产）。纪律实质不变，仅表述抽象化 → PATCH。
- **N7 i18n**：README 增 English Summary 节（仓库门面英文化；执行资产保持中文，无翻译漂移）。

## 1.4.0（2026-11-11）— Phase B 内核纯净化（课题 1 前置）

- **C1/N11 三受众拆分**：SKILL.md 纯净化为执行契约（条款来源日期/复盘注记/run 教训迁本文件）；README.md 重写为人类手册（任务史迁出）；本 CHANGELOG 建立。
- **C2/N6 路径参数化**：S0 run 根改三级解析（调用传入 > 环境变量 `ONTOLOGY_RUNS_ROOT` > README 目录约定）；脚本调用路径改 skill 根相对约定；sensitivity-rules「git 忽略目录」泛化为「受控目录（不进版本控制/不进入对外分发通道）」，vault git 惯例降为 README 使用建议。
- **M4 引擎限制内核化**：新增 `references/reasoner-limits.md`（限制①-⑭+削减实验矩阵 A-E+三级降级链+L2/L3 分工，自包含）；SKILL.md/README/structure-patterns/prompt-generator/tpl-production-handoff 共 5 处外部文档引用（原 `00 构建资料/L3-reasoner环境与用法.md`）全部切换。
- **M3 覆盖矩阵**：7 类语义×（编译进 TTL / md 扩展位登记 / 不承接）三态显式表进 SKILL.md 边界节与 README；扩展位路线图单列。
- **N1 版本体系**：frontmatter 加 `metadata.version`（schema 合规修正：顶层 version 属性不被 skill schema 支持，VS Code 诊断捕获后移入 metadata，版本号语义不变）；本文件建立（历史版本回溯登记见下）。
- **N8 外置词表表述修正**：tpl-golden-cases 敏感前置检查改指向 closeout_check `--patterns` 外置词表机制（内置仅泛化模式，真实词表不入 skill 资产）。
- **C3 残留同步**：structure-patterns 使用纪律「以 methodology-index 指向的卡为准」改「以 methodology-core 为准」（内核化后口径）；README 头部方法论权威表述同步。
- 脚本文件头构建任务史净化（run_golden_cases/closeout_check 头部注记、--engine help 文案）；引擎行为注释中的日期证据锚点保留。
- **一致性清扫（同批）**：validate_ontology/run_golden_cases 注释中「L3 环境文档」松引用切换 reasoner-limits；资产头部「源自原书+KC」来源注记（prompt-auditor/prompt-defense/tpl-defect-report/checklist-visual-review）迁 D 节；tpl-gate-submission/structured-input-mapping 头部日期注记迁出；tpl-ontology-doc 敏感级占位符改「受控目录」。**KC 来源括注在 agents/fibo-guide 保留**（与 methodology-core 逐条来源括注同类：溯源非运行依赖）。

## 1.3.0（2026-11-10）— Phase A 正确性与边界裁定（课题 1 前置）

- **C3 方法论内核化**：新增 `references/methodology-core.md`（28 卡判据细节按 Stage 焙为自包含内核，逐条括注来源卡 ID，附录溯源表）；SKILL.md 执行引用全切换；铁律 6 改「内核是执行权威，冲突回报用户裁定」；methodology-index 降为 vault 环境溯源附录并修正卡片来源路径。
- **M1 图 6-1 口径修正**：按用户原书图核对确认 7 类合计 29 子项（2/7/3/1/5/4/7）；tpl-29-sentences 子项表实为编译导向重构（合计 32 子项），删除「读图 28 差 1」错误防御表述。
- **M2 结构化映射通用化**：structured-input-mapping 重写为通用四步法（章节语义识别→run 级映射表→机械映射→缺口分级），原特定模板十一节表降为附录示例并中性化。
- **M6 盲测降级**：主路径=生成式建模（入口 (a)/(b)）；盲测重定位为「辅助验证模式，非默认路径」（组织以历史人工方案为对照基准校准能力时启用）。
- **C4 交付通道中立**：协作平台绑定描述删除，交付方式由调用环境自定；保留内部协作版/外部分享版分级。

## 1.2.0（2026-11-10）— 套件 v2 通用化清理

- 载体中立化（65 处/18 文件，三 skill 共享批次）：构建/验收历史注记改通用措辞（[verified] 证据链保留规模数字与日期、仅去载体名）；description「金融场景」泛化为「业务场景（金融、保险、供应链、制造等行业域）」；敏感纪律条目措辞泛化（纪律本体全保留）；模板虚构配例与 prompt 示例句按设计保留；fibo-guide 保留金融域公共标准扩展参考定位。

## 1.1.0（2026-11-03）— 真实载体生产级 run 实证反哺

- **SWRL 编译形态约束**（限制⑪⑫）：head 单原子化+双通道标准形态入 prompt-generator/structure-patterns §七；L2-SWRL-FORM 启发式 warning。
- **canonical 确定性档**（限制⑭第一段根治）：`canonicalize_base()` 内置 run_golden_cases 默认档；S6 验收纪律升级（多规则并发压力用例主载体+孤立用例 FAIL 先确认确定性）。
- **基线迭代入口 (b) 变体**：影响评估→修订对照表→G1 评审对照表→增量生成→黄金集逐字节冻结→零回归双证明→计数机械实测；迭代 run 事件驱动启动。
- **run 目录三区结构**（交付物/过程/实验）+即产即归位纪律；**呈报件规范**（tpl-gate-submission，G1/G2/G3 通用）；**审计文档面向纪律**（缺陷报告完整落盘，下一轮 auditor 以文档为唯一输入）。
- **收卷三步**（净化/打包/登记）+ `closeout_check.py`（齐套+敏感模式+计数一致+净化清单，词表外置 --patterns）；**计数单一事实源**（建模方案计数登记节为唯一权威，禁手抄）；**执行预算分片**（>60 条 --only 分组）。
- **tpl-production-handoff**（第 9 件可选交付物：生产化交接说明）；**structured-input-mapping**（S1' 机械映射档，统一章节模板输入快速通道）；**高频名词候选实体登记**（≥3 次强制登记，S2 前核对底稿）。
- HermiT 实例层对照复测（限制⑬定案：DL 交叉验证定位，swrl_verified 只能 Pellet 给出）。

## 1.0.0（2026-10-27）— skill 收官

- 方法论卡簇（KC-20261013-001~028，书级蒸馏）→ skill 产品化首例：S0-S6+G1-G3 管线、双模型异构质检（generator=opus/auditor=sonnet，四元组缺陷报告，博弈 ≤3 轮）、L1-L3 机械校验、黄金用例业务验收（80%→90% 闭环）。
- **S6 执行器泛化**：run 级 run_cases.py（用例内嵌）→ `scripts/run_golden_cases.py`（参数化+用例外置 golden-cases.json schema 1.0=专家黄金集输入接口形式化+限制⑩ strip 内置+exempt 机制+--check schema 校验）；基准 run 用例外置后全量回归 15/15=100% 行为等价；旧执行器留 run 级归档。
- 验收基准=虚构示例载体端到端试跑（G3 用户终审通过）：L1/L2/L3 全绿 swrl_verified="pellet"；黄金用例 15/15=100%；S4 两轮收敛；5 项实测裁定留档。

---

## 实证证据登记（构建史档案，自执行资产迁出）

### A. structure-patterns 修订登记（原 §九，2026-11-11 迁出）

| 日期 | 修订 | 理由与依据 |
|---|---|---|
| 2026-10-27 | 六族组织法→**七族**：增设 R 推导族（推导型规则不入约束族，独立成族）；标注更新为「第二场景已复核/粒度 provisional」 | 基准虚构 run（第二场景）复核发现推导型规则 R1-R7 在按「违反发现位点」组织的六族中无自然归属（建模方案 §十一登记，run 内按族外独立登记过渡处理）；G2 唯一开口项呈报，用户裁定方案 2（增设 R 族）而非方案 1（族外条款）。同轮登记：处置档五分类粒度复核意见（「仅登记留痕」或需独立档）维持 provisional 未修订，待第三场景 |
| 2026-11-02 | **第三场景复核（真实业务域生产级验收 run）**：① 新增 §七「SWRL 编译形态约束（Pellet 2.3.1 实测）」[verified]（限制⑩⑪⑫+双通道标准形态+≥2 轮全量复跑验收线；编译细节权威=prompt-generator.md）；② provisional→verified 升级 5 项：七族分族粒度（消费位差异注记：C/X/P 族归工程文档面属正常分布）/关系一等公民/逆关系全局约定/约束等级分布自检（77% 两场景精确复现）/八条配套原则条数；③ 处置档档数维持 provisional（第三场景处置语义由四态结论类承载，档表未直接消费，无复核数据） | 真实业务域本体 run（S0-S6+G1-G3 全链闭环，46 类/26 SWRL/3736 三元组；黄金用例 42 条首轮 96.9%→第二轮 100%；盲测还原率核心推理面 100%/误报 0）。复盘归口=生产级验收复盘 §三.B1（用户 G3 裁定③排期） |

### B. structure-patterns [verified] 证据明细（原注记括注，2026-11-11 迁出）

- **八条配套原则**：第三场景真实载体 run 八条全数适用——消费驱动=8 消费场景构件级绑定/反博物馆/不补造=误报 0 量化证明/LLM 只读不写=专家只读不写+闸门停等/约束分级+敏感分离=登记与执行授权分离。
- **关系一等公民**：第二场景 17 关系独立成层+第三场景 14 对象属性独立层，还原率对照关系矩阵成立，两场景复核无推翻。「关系一等公民」为实践裁量（书方法论四要素中关系本归属对象属性位），泛化到其他域时保留裁量但允许场景推翻。
- **逆关系全局约定**：第三场景 S5 复核 inverseOf 0 对=观察项豁免登记，反向查询由 SPARQL 逆路径承载，与约定同构；复查时点=生产化反向推理需求。
- **七族组织法三场景复核**：第二场景（2026-10-26 虚构载体）约束侧六族 F/L 适配、C/P 部分适配、X/S 空而有结构性理由，R 推导族 2026-10-27 用户裁定增设；第三场景（2026-11-02 真实载体，26 公理）分族粒度适配。消费位差异：F/S 族在 TTL 形式化面重建成立，C/X/P 族主要归属解析管线与行动环工程文档面（形式化面由 F/L/S/R 族承载）——七族框架跨「本体形式化+工程实施」双文档面完整覆盖，单看 TTL 面族空位属正常分布而非不适配。
- **R 推导族增设**：基准虚构 run 复核发现+G2 用户裁定方案 2（2026-10-27）。推导型规则与约束型公理语义正交：约束族服务「不可违反断言」（违反→处置档），推导规则是「条件⇒结论」的知识编译（不触发=未判定≠违反，否定方向由应用层拦截并登记）。
- **约束等级分布自检**：首次实践强约束占比约 77%（数据质量门禁+合规刚性为主体）；第三场景 26 公理=强 20/弱 4/提示 2，强占比 77% 精确复现——强监管域基线参考值成立。
- **§七 SWRL 编译形态约束两 run 实证**：第二场景（虚构载体）head 均单原子=形态巧合未踩；第三场景（真实规模载体，26 规则 32 用例）双结论规则踩中限制⑪⑫两缺陷，一次等价形态重写+6 份文档同步的返工成本——生成期预防优于验收期返工。HermiT 对照复测（2026-11-02）：不可对照（拒跑含 builtin 的 SWRL），双通道形态保留为 Pellet 硬要求（对 DL 层无副作用）。

### C. SKILL.md 条款固化来源（2026-11-11 迁出）

- **2026-11-02 增补**：高频名词候选实体登记（真实载体 run 教训：资料在白名单内、名词有出现，但未升格实体，成为范围内真漏检——低密度但结构关键的名词最易被三维访谈漏检）；盲测还原率对照勾稽位（缺对照报告不得收卷）。
- **2026-11-03 双 run 复盘固化**：基线迭代细则（入口 (b) 变体七步）；run 目录三区结构（归置判据=「同事消费会不会打开它」）；呈报件规范（P2）；审计文档面向纪律（消除 resume 单点）；执行预算分片；收卷三步；计数单一事实源（真实载体 run 教训：手抄计数产生多份漂移口径）；tpl-production-handoff 触发条件（复盘 D2）。
- **2026-11-02 敏感前置检查增补**（tpl-golden-cases）：真实载体 run 实证——3 处真实品牌名泄露均在 desc 字段（用例主体已虚构仍漏）；desc 通常直接引用专家黄金集案例描述原文，最容易带入真实品牌名/机构名/人名。敏感自查必须在落盘前执行（事后 grep 是兜底不是门禁）。

### D. Prompt 与模板资产规范来源（2026-11-11 迁出）

- **prompt-generator**：四段式结构源自原书建模 Prompt 示例与 KC-20261013-010「输入三要素」。
- **prompt-auditor / prompt-defense / tpl-defect-report**：角色定位与四元组格式源自原书大模型 B（审计者/逻辑审计员）与大模型 A（辩护与修订）Prompt、KC-20261013-012 双大模型协同校验（异构协同、黑盒思维、逻辑博弈机制）。
- **checklist-visual-review**：专家三步审查法源自原书 6.2.3 与 KC-20261013-013 可视化专家把关三步法。
- **tpl-gate-submission**：呈报件规范设计原则=2026-11-03 双 run 复盘 P2 固化。
- **structured-input-mapping**：来源=2026-11-02 真实业务域生产级验收 run 复盘（20 份统一模板文档=该次基线迭代主输入形态），用户 G3 后裁定资产化；2026-11-10 产品化裁定（M2）重写为通用四步法，原特定模板十一节映射表降为附录示例并中性化。
- **SWRL 硬规范 v2**：2026-10-26 双引擎实测裁定修订，旧「bnode 包装层」规范（v1）废止——真根因=包装层变量同一性失效（Pellet 报 "is not a URI node"）；具名变量写法 Pellet+HermiT 双引擎实测规则触发。对照实验=四变体最小重现（vault 构建区 swrl-variant-test）。
- **datatype 硬规范**：2026-10-26 Pellet 三变体实测裁定（m1a 具名枚举判空/m1c onDatatype 拒跑/m1d 内联+type 兼容）；票据虚构载体 v1.2.1 返修采用推荐形态。
- **SWRL 编译形态约束**：2026-11-02 Pellet 2.3.1 实测，真实规模本体 32 用例验收定案（9 组削减实验矩阵，详见 reasoner-limits §六矩阵 C）。

### E. 验收基准与任务史（原 README §九，2026-11-11 迁出）

- 基准 run=虚构示例载体端到端 run（run 目录见 vault 构建区 `01 AI 实验室/06 本体建模能力/runs/`，与套件 examples/ 同源）；评估汇总=vault 构建区 `workspace/评估报告.md`（7 项定量指标+baseline 对照）。
- 单测（vault 构建区）：`00 构建资料/单测样例/run_tests.sh`，PASS=13/13（含 1e/1f=run_golden_cases --check 正/负例）；L3 环境单测早期口径 PASS=9/9（L2×6+L3×3，含 custom_datatype 回归）。
- 登记待办（1.0.0 时点）：HermiT 实例层复测（探索项，已于 1.1.0 完成=限制⑬）/ structure-patterns [provisional] 项待第三场景复核（已于 1.1.0 完成 5 项升级，处置档档数维持 provisional）。
- **任务 2 可视化审核平台暂缓史**：2026-10-27 裁定暂缓收尾——WebProtégé 实测出局（round-trip SWRL hollowing+inverseOf 丢失），修订组合方向=审阅图示层/意见回流/管线重编译分离承载。该方向后由 ontology-review skill 承接落地（2026-11-10，课题 2）；图示三外采组件（OntoInk/WebVOWL/Reactodia）实测不满足 SWRL/hasKey/oneOf 门禁→自建 cytoscape 单文件（详见 ontology-review CHANGELOG）。
- L3 引擎限制原始实测档案=vault 构建区 `00 构建资料/L3-reasoner环境与用法.md`（2026-10-26 实测定型，含本机环境明细与 Java 下载通道注记）；执行侧自包含登记已内核化至 `references/reasoner-limits.md`（1.4.0）。

### F. R2 增量 patch 引擎实证矩阵（2026-11-17，1.6.0）

> fixture=虚构票据贴现载体（套件 `examples/票据贴现/建模run/ontology.ttl`，566 三元组/0 error 0 warning/10 类 9 对象 13 数据 5 规则；golden-cases.json 16 用例 Q3-STRESS exempt→15 active，纯全局 X1-X4）。环境=python 3.9.6 / rdflib 7.6.0 / owlready2 0.51 / Java jdk-25.0.5 Pellet。patch JSON 运行时生成（sha 运行时算），examples/ 零改动。

**设计 grounding 实证**（Plan 阶段，修正原草图 7 处）：
- bnode 跨 parse 不可寻址：两次 parse bnode 标签随机不同，用 bnode term 做 remove 是 no-op→契约禁 `_:` 项 + 规则级编辑 + 单 parse 工作图（三元组复制共享 bnode 对象）。
- 序列化确定性：canonical-copy-rebind turtle（to_canonical_graph→复制普通 Graph〔ReadOnlyGraphAggregate 不可 bind〕→rebind 原前缀）跨 PYTHONHASHSEED 字节稳定；diff 渲染经 to_canonical_graph 取确定性 cb 哈希标签（report 无随机标签泄漏，v6 纪律）。
- 回归子集原型：remove_ruleR3 受影响 7→保守扩展 37→15/15 选中（MAJOR 全审查合理）；孤立新类（无 subclass_of）→交集空→仅全局守卫。
- L2-DISJOINT error 触发：`:Discountable rdfs:subClassOf :NonDiscountable`（二者 AllDisjointClasses 成员）→new_errors≥1。
- oneOf 字面量挂 bnode list cell：replace_literal p=rdf:first，s 省略全图唯一匹配；锚点反向 BFS 回溯承载属性（applicationStatus）。

**手工实证矩阵**（incremental_patch.py 直跑，输出落 tmp）：

| 子例 | 操作 | 结果 |
|---|---|---|
| T11a 注解 | modify_label :Bill | exit 0；bump=PATCH（auto=patch）；regression=skipped(annotation-only)；zero_wb ✓ |
| T11b 结构 | add_class :PatchDemoClass ⊑ :Bill | exit 0；bump=MINOR；regression=pass（选中 15，Bill 重连接→保守扩展全子集）；new_errors 0 |
| T11c L2 反例 | add_triple :Discountable ⊑ :NonDiscountable | exit 1；new_errors 1；blocked；draft 仍产；regression=skipped(l1l2-blocked)（短路省 JVM） |
| T11d 回归反例 | replace_literal oneOf 已提交→已递交 | exit 1；bump=MINOR；regression=fail；选中 9（G1/G4/G6/E4/X1-X4/X7，锚点+扩展精度非全集）；newly_failed G1/G4/E4/X7；通过率 100→55.6% |
| T11e1 MAJOR 政策 | remove_rule ruleR3 无 --golden | exit 1；bump=MAJOR；regression=blocked（硬前提缺失转入口 (c)） |
| T11e2 契约 | baseline sha 错配 | exit 2；不产 draft（防陈旧 patch） |
| T11f 确定性 | T11a 双跑（两子进程） | draft md5 字节一致（c18a2097…） |
| MAJOR 全集回归 | remove_rule ruleR3 + --golden + Java | exit 1；bump=MAJOR rule_touched ✓；regression=fail 选中 15；baseline 15/15→draft 14/15；newly_failed G2；通过率 100→93.3%（守护检出规则删除影响）；zero_wb ✓ |
| L3 通道 | modify_label + --with-l3 | exit 0；L3 subprocess consistent=True reasoner=pellet exit_code 0 |
| 零回写独立 | examples/ baseline+golden sha 前后 | baseline sha 不变 ✓ golden 稳定 ✓（权威 fixture 未被改动） |

**契约边界矩阵 10/10 PASS**：replace_rule 合法片段→MAJOR blocked（无 golden）/ bnode 变量片段→exit 2 / 片段含 @prefix→exit 2 / 片段 IRI 不匹配→exit 2 / remove_triple 目标缺失→exit 2（附实际宾语）/ replace_literal 多匹配→exit 2 / `_:` 项→exit 2 / 未知前缀→exit 2 / add_class 重复声明→exit 2 / o 位字符串→IRI（永不解释为字面量）。

**保真边界实证**：rdflib 序列化丢失原文件注释（fixture 版本史头注释）——draft 头注释 + report 承载版本溯源，晋升时历史注释合并由编排器/人工承接（文本级保注释 patch 否决）。枚举字面量变更 diff 整 oneOf 子树过报（bnode 链哈希全变，安全侧；named_summary 从操作日志补可读性）。

**套件 T11 验收电池（`run_suite_tests.py`，2026-11-17 v9 重冻结）**：Java 档 **PASS 12 / FAIL 0 / SKIP 0**（T0 py_compile 14 脚本含 incremental_patch.py；T11 6 子例聚合行 PASS：a=PATCH/annotation-skip｜b=MINOR/pass｜c=L2-blocked/短路｜d=回归翻转 G1｜e=MAJOR-blocked/sha-exit2｜f=双跑字节一致｜零回写 ✓）；`--skip-java` 档 PASS 11 / SKIP 1 exit 0（T8 SKIP，T11d SKIP 登记，T11b not-requested）；坏套件根（`--suite-root` 空目录）exit 2——三态验证 ✓。CLI `model patch` 分发 exit 透传实证（注解 only exit 0，`entry_c.authoritative=false`·`pending_audit`，fixture 零回写）。权威↔快照 rsync 字节级一致（skills×3+agents×5）；套件 109 文件（+2）零缓存残留、examples 零副作用。

> **T11f 测试台修复（非引擎缺陷，构建档案登记）**：电池初版 T11f 误用不同 patch_id（t11a vs t11f）双跑比较——draft 溯源头含 `patch_id` 字段，不同 patch_id 头部必异→假 FAIL；另 `d` 变量被后续子例覆盖指向 t11e1 draft。修正为**复用同一 patch JSON（同 patch_id）跨进程二次跑**（真确定性测试：同输入→同输出）+ 独立 `da` 锁定 T11a draft 路径。引擎确定性本身经隔离实证（同 patch_id 跨 PYTHONHASHSEED 1/999 双跑 md5 一致 a58e3375…）+ 手工矩阵 T11f（c18a2097…）双重确认，**零引擎改动**（incremental_patch.py 未因此修复变更）。

### G. R4 SHACL 约束校验层实证矩阵（2026-11-17，1.7.0）

> fixture=虚构票据贴现载体（套件 `examples/票据贴现/建模run/ontology.ttl`，566 三元组/10 类 9 对象 13 数据 3 facet datatype 5 SWRL 4 hasKey；golden-cases.json 15 active）。环境=python 3.9.6 / rdflib 7.6.0 / **pyshacl 0.29.1**（Apache-2.0）/ owlready2 0.51 / Java jdk-25（R4 纯 Python 无需 Java）。data/shapes 运行时 tmp 生成，examples/ 零改动；冒烟 PYTHONPYCACHEPREFIX 外置，skill 目录零缓存残留。

**规划期 grounding（Plan agent 内存实证 E1-E20，零落盘；四 refine + 电池否决来源）**：
- E8/E9 → R-a 定义类展开 + R-b 逆路径：`sh:qualifiedValueShape [sh:class :ApplicationUnderReview]` 在输入数据图（未物化）conforms=True 假阴性；数据断言 targetsBill 而公理挂 hasDiscountApplication（inverseOf）须逆路径。
- E11/E12 → R-d 数值容忍：compile_instance_ttl 把 JSON int 编码 xsd:integer，严格 sh:datatype xsd:decimal 误报；demo1（int 金额 500000/495000）conforms=True。
- E14/E15 → R-c 子类闭包：个体仅类型化子类（:AcceptableApplication）严格 sh:class 误报；闭包 sh:or 修复，真阳性不损。
- E13 → 电池设计否决：golden 15 active 仅 2/15 conform（9 例缺承兑人=开放世界推理 fixture 设计使然）→ SHACL 不接入 S6，T12 正例运行时自建。
- E6（hasKey sh:sparql）/E16（canonical 确定性）/E17（--strict）/E18（advanced=True 显式）/E19（provenance regex 可提取）/E20（全链许可兼容 + FunctionalProperty=11 非 10 + shape IRI 零碰撞）。E10 owlrl/rdfs 备选登记不启用（inference=None）。

**实施期正式脚本重跑（derive_shacl.py + validate_shacl.py 直跑，输出落 tmp）**：

| 子例 | 构造 | 结果 |
|---|---|---|
| 派生确定性 | fixture derive 双跑（两子进程） | shapes+report 各字节一致 ✓；rc=0；零回写（源 TTL sha 前后一致）✓ |
| 派生计数锚 | fixture | node_shapes 5 / property_shapes 23 / mapped 34 / unmapped 7；kind_counts: data_property 14（USCC 双 domain）/ facet-datatype 3 / oneOf-in 2 / object_property 9 / restriction-someValuesFrom 1 / restriction-maxQualifiedCardinality 1 / hasKey-sparql 4；unmapped=SWRL×5+Transitive×1+AllDisjoint×1 |
| 结构核验 | shapes 图遍历 | R-b alternativePath=[hasDiscountApplication, inversePath(targetsBill)] 正确构造 ✓；R-a qualifiedValueShape sh:or 闭包 4 类+applicationStatus hasValue 审核中 ✓；hasAcceptor minCount1+maxCount1 幂等合并 ✓；R-d faceAmount datatype=None+minExclusive ✓；hasKey 闭包 UNION ✓ |
| b1 正例 | 完整 Bill（int 500000）+Acceptor(AAA)+Holder+DiscountApplication 申请 | rc=0 conforms（R-d 数值容忍） |
| b2 变体 | 申请仅类型化 AcceptableApplication | rc=0 conforms（R-c 子类闭包） |
| c facet 越限 | faceAmount=-5 + billNumber="随便写" | rc=1 MinExclusive+Pattern |
| d1 无承兑人 | Bill 缺 hasAcceptor | rc=1 MinCount（someValuesFrom） |
| d2 两承兑人 | Bill 两 hasAcceptor | rc=1 MaxCount（Functional） |
| d3 限定基数 | 两笔审核中 AcceptableApplication 申请经 targetsBill 指向同一 Bill | rc=1 QualifiedMaxCount（R-a 展开+R-b 逆路径+R-c 闭包三合一） |
| e 枚举 | creditRating="BBB" | rc=1 In |
| f hasKey | 两完整 Bill 同 billNumber | rc=1 SPARQL×2 |

**补洞三态对偶（c 场景，纯 Python 无 Java）**：同场景 instance JSON 喂 check_instance→**rc=0**（4×W08「具名 datatype…facet 校验 SHACL 层 R4 承接，值未验证」放行，含 faceAmount=-5）；同场景 data TTL 喂 validate_shacl→**rc=1**（MinExclusive+Pattern 检出）。三态=「Pellet 剥离放行 / check_instance W08 放行 / SHACL 检出」，实证 R4 填补实例级数据完整性真空白。

**手工边界矩阵**：shape IRI 碰撞（源图含 :BillShape 类）→derive exit 1（附碰撞 IRI）✓；复合 hasKey（2 键）→unmapped hasKey-composite ✓；深度>3 定义类（4 层嵌套 intersectionOf）→unmapped defined-class-too-deep ✓；坏 TTL/缺文件→derive exit 2 ✓；validate 缺 data/坏 data/缺 shapes→exit 2 ✓；空数据图→rc=0 平凡 conform ✓；--focus bill1→rc=1 ✓；Warning shape 非 strict rc=0 / --strict rc=1 ✓；realpath 守卫（output==input）→exit 2 ✓；py_compile 两脚本 OK ✓。

**两处关键发现（实施期实证，写入脚本 docstring + 契约模板）**：
- **alternativePath 正确构造**：必须「独立 rdf:list 节点 + sh:alternativePath 谓词包裹」——path 节点本身不可建成 rdf:list（漏 sh:alternativePath 谓词时 pyshacl `value_nodes_from_path`〔expression_helper.py L47〕先查 rdf:first 误判**序列路径**→空集→maxCount/qualifiedMaxCount 静默失效）。首测 conforms=True 假阴性经读 pyshacl 源码定位修正，T2-T7 全过。pyshacl 规格 alternativePath ≥2 项（单项抛 ReportableRuntimeError）。
- **pyshacl.validate 篡改 shapes 图**：即使 inplace=False（该参数指 data 图），advanced 处理向 shapes 图注入 owl 公理（`owl:Class rdfs:subClassOf rdfs:Class` 等）→破坏 canonical 确定性。处置：derive_shacl 序列化前绝不喂 validate（天然满足）；validate_shacl 每次从文件 fresh parse。新鲜图 canonical-copy-rebind 双跑字节稳定=True 实证。

> **derive 缺文件三态修复（构建档案登记）**：初版 main 在 load_ontology 存在性守卫**之前**调 file_sha256(src)，缺文件时 FileNotFoundError 未捕获→traceback exit 1（期 2）。修正为先 load_ontology（exit 2 守卫）再算 sha（parse 只读不影响零回写断言）。复测缺文件 exit 2 ✓ + fixture 重排后字节稳定 ✓，**派生逻辑零改动**。

**datatype 语义锚（写脚本前隔离实证）**：sh:datatype xsd:string 接受 plain literal（RDF 1.1，compile 字符串编码形态兼容）✓；sh:minExclusive "0"^^xsd:decimal 对 xsd:integer 字面量数值提升比较（int 500000 conform / int -5 违反 MinExclusive）✓；sh:in 枚举 plain literal 匹配 ✓；hasKey sh:sparql 重复键→每 focus 一条 SPARQLConstraintComponent ✓。

**套件 T12 验收电池**：见套件 CHANGELOG/README v10（run_suite_tests.py t12_shacl 7 子例聚合，Java 档 PASS 13 / --skip-java 档 PASS 12 SKIP 1，纯 Python 两档均执行）。
