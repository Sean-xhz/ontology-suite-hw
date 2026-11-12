# run-manifest：票据贴现端到端试跑（Phase D 主试跑）

## S0 准入登记

| 项 | 值 |
|---|---|
| 入口模式 | **(a)** 原始业务资料 → 全管线（S0-S6+G1-G3） |
| 输入资料 | `试跑资料_票据贴现_虚构.md`（AI 构造全虚构资料，构造说明节对管线不可见） |
| 场景敏感级 | **虚构通用**——人物/机构/产品/数字均不真实；run 目录可用 git 追踪区（sensitivity-rules §二.2） |
| run 目录 | `票据贴现_20261026/（本示例快照）` |
| 试跑性质 | skill 构建期端到端验收（plan Phase D 裁定③⑧）；兼复核 structure-patterns.md [provisional] 项对票据域的适配性 |
| 参与角色 | 主会话=管线编排+本体工程师角色；ontology-generator（opus）=生成/辩护；ontology-auditor（sonnet）=审计；用户/业务专家=G1/G2/G3 闸门（授权代跑时登记） |

## 依赖路径登记（路径失效即索取不猜测）

| 依赖 | 路径 |
|---|---|
| 方法论卡簇 | KC-20261013-001~028（执行判据已焙入 references/methodology-core.md；vault 环境溯源索引=references/methodology-index.md） |
| skill 资产 | `.claude/skills/ontology-model/`（SKILL.md+references×4+assets×9+scripts×3） |
| agents | `.claude/agents/ontology-generator.md`（opus）/ `ontology-auditor.md`（sonnet）——异构确认 ✅ |

## 裁剪登记

| 裁剪项 | 理由 |
|---|---|
| 流程/权限/CRUD 三类扩展位 | MVP 降级为 md 结构化描述（BPMN2.0/ODRL/SPARQL 不产出形式化文件） |
| FIBO 公共层对齐 | 票据域无预置清单（fibo-guide §二纪律）；本次试跑做轻量对齐尝试并登记检索结果，不强求 |
| S5 Protégé 图形化 | 无环境——report_topology.py 文本拓扑+checklist 降级执行并登记 |
| L4 pySHACL | 完全可选位，本次不启用 |

## 管线进度

| Stage | 状态 | 产物/结论 |
|---|---|---|
| S0 | ✅ | 本 manifest |
| S1 萃取 | ✅ | 萃取草稿并入 S2 产物溯源登记（三维：对象/任务/规则） |
| S2 组装 | ✅ | `29句话描述集.md` + `术语词典.md` |
| G1 准入评审 | ✅ **通过（授权代跑）** | 用户 2026-10-26 授权代跑，按初审建议裁定：Q1=R2 优先（R4「随时」收窄）/Q2=仅状态停用/Q3=无要求/Q4=授权 S3 裁量回登记。第二段复核表已闭环 → `G1初审checklist.md`；描述集+词典冻结为 S3 基线 |
| S3 生成 | ✅ | ontology.ttl（620 行：类 10/对象属性 9/数据属性 13/SWRL 5/SKOS Concept 15+Scheme/hasKey×4/受限 datatype×5，全构件 label@zh+comment 消费点登记）+ 建模方案.md（468 行：四层结构+裁量登记§十+六族适配性复核§十一+FIBO 对齐§七+编译缺口清单）。generator 自报磁盘复核通过（SWRL Variable 包装 43 处抽查合规） |
| S4 机械脚本 | ✅ **v1.2 全绿** | v1.0 初版 validate 0e1w + L3 第③档降级（swrl_verified=false）→ v1.1（SWRL 具名变量修订）L3 **第①档全量首次达成 swrl_verified="pellet"** 但阳性检出 ApplicationUnderReview≡⊥ → v1.2（枚举 datatype 迁移内联 oneOf）**validate 0 error 0 warning + L3 Pellet 全量 consistent=true swrl_verified="pellet" rules=5 inconsistent=[]**——**L1/L2/L3 全绿，plan W3C 验证层次首次完整达成（L3 构建目标裁定⑥）** |
| S4 审计 | ✅ **收敛闭环（2 轮 < 上限 3）** | 第 1 轮（sonnet 全基准）裁定**不通过**（阻断① SWRL 变量 / 重要② USCC / 建议③-⑦ + 残留风险 6）→ generator 7/7 修订 v1.1（0 辩护）→ 机械返修 v1.2（枚举 datatype，全绿）→ 第 2 轮（验证轮）裁定**通过**（零阻断零重要，建议级 2 + 范围外观察 3；确认 v1.1/v1.2 全部落实、语义等价零回归；高价值确认=枚举迁移使 R6 公理由空真恢复实质生效）→ v1.2.1 轻量返修收编全部建议项（m1d 实测定案补 rdf:type rdfs:Datatype）。四元组完整率两轮均 100% |
| G2 争议仲裁 | ✅ **自动通过（A/B 一致）** | 无 A/B 对立主张（generator 0 辩护、auditor 两轮结论与 generator 实质一致）；备案清单=实测裁定 5 项（SWRL 变量模板 v2 / USCC hasKey / 枚举 datatype / m1d 内联补 type / **限制⑩ facet 实例层假不一致（S6 新增）**，均证据+结论形式，详见缺陷报告 §5）+ 业务待确认项 7 条（缺口清单维持登记）+ **唯一待人工裁定开口项：structure-patterns.md 六族「推导规则归属」方法论修订建议**（skill 资产变更，呈报用户，不阻塞本 run 管线） |
| S4 终态 | ✅ **v1.2.1 全绿收官** | 磁盘复核 8/8 通过；validate 0e0w + L3 Pellet 全量 consistent=true / swrl_verified="pellet" / rules=5；generator 范围外未动项 3 处版本记号已由主会话机械同步（纯记号无语义），同步后 validate 复跑 0e0w。**S4 收敛终版=v1.2.1** |
| S5 结构把关 | ✅（降级执行） | **降级登记：无 Protégé 环境，report_topology.py 文本拓扑替代**→`S5拓扑报告.md`（71 行拓扑+审查记录）。三步审查全执行：全局拓扑 5/5（无环/无孤岛/分类轴纯净/深度 2 层/颗粒均衡）、局部语义穿透核心 5 类全查（domain-range 方向/数值防呆/四特征逐个业务问句——hasEndorser 记录具化规避经典误用）、规则路径回溯 R1/R4/R7（前提完备/边界代入/冲突可检出/触发链闭环）——**发现问题 0，无回流**。工具观察 2 条登记 skill 增强候选（Phase E）。拓扑报告呈用户人工抽核（G3 一并确认） |
| S6 业务验收 | ✅ **15/15=100%** | 专家种子 6（代拟待专家确认）+AI 扩展 9（边缘 2/异常 7）+压力豁免（Q3）；8.3 判据 R1-R7 每条 ≥1 正向+1 负向全覆盖；auditor 两轮用例契约 5/5 履行。首跑 26.7%→**根因=限制⑩**（facet 具名 datatype Pellet 实例层假不一致，削减实验定案，归因第四类「执行环境限制」——本体/用例零改动，执行器 strip 降级）→重跑 **100%**（超 90% 目标）。关键实证：G3 Transitive 闭包 ['IndR3','IndR2'] / X1·X2 内联 oneOf 实例层真强制（auditor 2.5 预警证伪）/ X3 R6 实质生效 / E4·X5 open-world 正确。产物=`黄金用例集.md`+`测试报告.md`+`golden-cases-result.json`；执行器=`workspace/golden-case-runner/run_cases.py`（泛化入 skill scripts 登记 Phase E 候选） |
| G3 验收终审 | ✅ **通过（用户终审，2026-10-27）** | 呈报=测试报告+黄金用例集+S5 拓扑报告+8 件套清单+G2 备案；用户结论「**通过，交付收官**」——含代拟黄金用例 G1-G6 专家确认 + S5 拓扑报告抽核认可。**run 交付收官**：ontology.ttl v1.2.1 为终版基线；Phase E 收尾项（入口(b)测试/git 入库范围/增强候选处置/六族方法论裁定）转 skill 构建轨道 |

**S4 前置事件登记**：validate_ontology.py 首跑误报 6 条「悬挂引用」——自定义 datatype（rdfs:Datatype+owl:onDatatype）未被 known 集合收录，脚本 bug 已修（known ∪ rdfs:Datatype 声明集）+回归 fixture `custom_datatype.ttl` 入单测。误报非本体缺陷，generator 产物未因此改动。

**S4 实测裁定登记**（机械/实测裁定先于人工仲裁，均以证据+结论留 G2 备案，不消耗人工仲裁）：
1. **SWRL 变量模板 v2**——auditor 阻断项① 成立；双引擎对照实验（`workspace/swrl-variant-test/` t1_named vs t2_wrapper）裁定 bnode 包装层致变量同一性失效（Pellet `is not a URI node`），改具名 `swrl:Variable` 个体；已固化 prompt-generator.md SWRL 硬规范 v2 + L3 环境文档限制④更正（旧「Pellet+SWRL=坏」为误判）+ 单测夹具改写
2. **USCC hasKey 语义**——hasKey=类内键公理（OWL 2 规范事实），auditor 重要项② 成立；描述集 1.2b/1.2c 本就只要求类内唯一，无业务裁量空间
3. **枚举 datatype**——L3 Pellet 全量档检出：具名枚举 datatype（仅 `owl:oneOf`）值空间判空 → hasValue 定义类静默 ≡⊥；三变体最小重现（m1a/b/c）裁定唯一兼容形态=range 内联匿名 oneOf；已固化 validate_ontology.py L2-DATATYPE 检查 + prompt-generator.md datatype 硬规范 + L3 环境文档限制⑨ + `enum_datatype.ttl` 回归夹具（**单测 PASS=10/10**）
4. **内联 oneOf 补 type（m1d，第 2 轮）**——OWL 2 DataOneOf 标准映射要求内联数据范围带 `rdf:type rdfs:Datatype`；m1d 全量实测：Pellet consistent=true 不重现判空 + L2 不误报（URIRef 过滤豁免 bnode）→ 裁定采用标准形态（v1.2.1）；固化=prompt-generator.md 推荐形态升级 + L3 文档限制⑨补充 + enum_datatype.ttl 对照 3 + 夹具前缀误拼卫生修正（`1999-02-22`→`1999/02/22`，误拼仅存在于夹具且从未被消费；ontology.ttl 前缀经 od 字节级核实正确）（**单测重跑 PASS=10/10**）
5. **限制⑩：facet 具名 datatype 实例层假不一致（S6）**——首跑 11/15 假不一致，削减实验（C1-C6/C1'/C4'）定案：Pellet 模式层忽略 facet 三元组（兼容），但个体断言字面量后 datatype 值空间判空→range 违反→实例层假不一致；处置=执行器 `strip_named_datatypes()` 降级（仅剥 URIRef 具名，内联 bnode oneOf 保留——X1/X2 实证其实例层真强制力），**本体/用例零改动**，重跑 15/15=100%。固化=L3 环境文档限制⑩+分工表补行 + SKILL.md S6 实例级推理执行纪律；归因第四类「执行环境限制」入 tpl-golden-cases 枚举=Phase E 候选（详见缺陷报告 §5 裁定⑤）

**唯一待 G2 人工裁定的真正开口项**：structure-patterns.md 六族「推导规则归属」方法论修订建议（generator S3 提出，属 skill 资产变更须人工裁定）——**已裁定闭环（2026-10-27）**：用户裁定**方案 2=增设 R 推导族**（六族→七族），structure-patterns.md §四已修订+§八修订登记+tpl-ontology-doc.md 同步；处置档粒度复核意见维持 provisional 待第三场景。

## Phase E 收尾登记（2026-10-27，G3 通过后）

| 项 | 结果 |
|---|---|
| 用户四项裁定 | ①六族修订=方案 2 增设 R 推导族（已落地）②description 触发优化 run_loop.py=不跑 ③git=全量入库并提交 ④可选增强档真实票据资料=不提供，关闭（主试跑虚构资料即终版验收依据） |
| 入口 (b) 回放 | ✅ `workspace/test-b_20261027/`（S0 判定/S1 跳过/S2 只校验三断言过；S3/S4 裁量不重跑已登记偏差理由） |
| 评估报告 | ✅ `workspace/评估报告.md`（7 项定量指标全达标+baseline 对照结论+3 条 baseline 发现处置：②采纳=L1-PREFIX 检查固化〔上线首跑即抓到 enum_datatype.ttl 混合形态误拼 `1999-02/22`，连带 m1a/b/c 修复，单测 11/11〕①③不采纳留档） |
| 资产增强 | report_topology.py bnode/SWRL atom 展开（S5 观察闭环）+ validate L1-PREFIX + tpl-golden-cases 归因第四类 + SKILL.md S6 执行纪律 |
| run 终态 | **交付收官**（G3 通过 2026-10-27）；ontology.ttl v1.2.1=终版基线 |
| S6 执行器泛化（Phase E 候选闭环） | ✅ 2026-10-27：`scripts/run_golden_cases.py` 落 skill（用例内嵌→外置 `golden-cases.json` schema 1.0=专家黄金集输入接口形式化；strip 内置；--check 入单测 1e/1f）；本 run 用例零转录外置 16 条（15 执行+Q3-STRESS exempt），全量回归 **15/15=100% 行为等价**（`workspace/golden-case-runner/泛化回归_20261027.json`）；单测 PASS=13/13 |

**人工闸门代跑登记**：G1=授权代跑（用户原话「授权代跑」，2026-10-26）；G2 触发条件=A/B 争议或 3 轮未收敛（A/B 一致自动通过）；G3 到时另行停等呈报（本次授权范围仅 G1）。

## 敏感自查

输入即虚构资料（构造时已执行五项遮盖纪律）；产物落盘前仍按 S3-S6 时序跑 grep 自查（机构名/证件号/手机号模式）。
