# run-manifest：票据贴现端到端示例 run

## S0 准入登记

| 项 | 值 |
|---|---|
| 入口模式 | **(a)** 原始业务资料 → 全管线（S0-S6+G1-G3） |
| 输入资料 | `示例资料_票据贴现_虚构.md`（AI 构造全虚构资料，构造说明节对管线不可见） |
| 场景敏感级 | **虚构通用**——人物/机构/产品/数字均不真实；run 目录可用 git 追踪区（sensitivity-rules §二.2） |
| run 目录 | `票据贴现_20261026/（本示例快照）` |
| 参与角色 | 主会话=管线编排+本体工程师角色；ontology-generator（opus）=生成/辩护；ontology-auditor（sonnet）=审计；用户/业务专家=G1/G2/G3 闸门 |

## 依赖路径登记（路径失效即索取不猜测）

| 依赖 | 路径 |
|---|---|
| 方法论内核 | `references/methodology-core.md`（源自《本体驱动的AI数据管理》公开方法论，执行判据自包含） |
| skill 资产 | ontology-model（SKILL.md + references + assets + scripts） |
| agents | ontology-generator（opus）/ ontology-auditor（sonnet）——异构确认 ✅（生成/审计须不同模型） |

## 裁剪登记

| 裁剪项 | 理由 |
|---|---|
| 流程/权限/CRUD 三类扩展位 | MVP 降级为 md 结构化描述（BPMN2.0/ODRL/SPARQL 不产出形式化文件） |
| FIBO 公共层对齐 | 票据域无预置清单（fibo-guide §二纪律）；本次做轻量对齐尝试并登记检索结果，不强求 |
| S5 Protégé 图形化 | 无环境——report_topology.py 文本拓扑+checklist 降级执行并登记 |
| L4 pySHACL | 完全可选位，本次不启用 |

## 管线进度

| Stage | 状态 | 产物/结论 |
|---|---|---|
| S0 | ✅ | 本 manifest |
| S1 萃取 | ✅ | 萃取草稿并入 S2 产物溯源登记（三维：对象/任务/规则） |
| S2 组装 | ✅ | `29句话描述集.md` + `术语词典.md` |
| G1 准入评审 | ✅ **通过** | 四标准两段评审：工程师初审 + 业务专家复核闭环 → `G1初审checklist.md`；Q1=R2 优先（R4「随时」收窄）/Q2=仅状态停用/Q3=无性能要求/Q4=授权 S3 裁量回登记；描述集+词典冻结为 S3 基线 |
| S3 生成 | ✅ | ontology.ttl（类 10/对象属性 9/数据属性 13/SWRL 5/SKOS Concept 15+Scheme/hasKey×4/受限 datatype×5，全构件 label@zh+comment 消费点登记）+ 建模方案.md（四层结构+裁量登记+六族适配性复核+FIBO 对齐+编译缺口清单） |
| S4 机械脚本 | ✅ **全绿** | validate 0 error 0 warning + L3 Pellet 全量 consistent=true / swrl_verified="pellet" / rules=5 / inconsistent=[]——L1/L2/L3 全绿（SWRL 具名变量 + 枚举 datatype 内联 oneOf，详见缺陷报告） |
| S4 审计 | ✅ **收敛闭环（2 轮 < 上限 3）** | 第 1 轮裁定不通过（阻断① SWRL 变量 / 重要② USCC / 建议③-⑦）→ generator 7/7 修订 → 机械返修（枚举 datatype，全绿）→ 第 2 轮裁定通过（零阻断零重要）→ 轻量返修收编建议项。四元组完整率两轮均 100% |
| G2 争议仲裁 | ✅ **自动通过（A/B 一致）** | 无 A/B 对立主张（generator 0 辩护、auditor 两轮结论与 generator 实质一致）；备案清单=实测裁定 5 项（SWRL 变量模板 v2 / USCC hasKey / 枚举 datatype / 内联 oneOf 补 type / 限制⑩ facet 实例层假不一致，详见缺陷报告 §5）+ 业务待确认项 7 条 |
| S5 结构把关 | ✅（降级执行） | 无 Protégé 环境，report_topology.py 文本拓扑替代 → `S5拓扑报告.md`。三步审查全执行：全局拓扑 5/5（无环/无孤岛/分类轴纯净/深度 2 层/颗粒均衡）、局部语义穿透核心 5 类全查（domain-range 方向/数值防呆/四特征逐个业务问句）、规则路径回溯 R1/R4/R7（前提完备/边界代入/冲突可检出/触发链闭环）——发现问题 0，无回流。拓扑报告呈用户人工抽核 |
| S6 业务验收 | ✅ **15/15=100%** | 专家种子 6（代拟待专家确认）+AI 扩展 9（边缘 2/异常 7）+压力豁免（Q3）；R1-R7 每条 ≥1 正向+1 负向全覆盖。首跑 26.7%→根因=限制⑩（facet 具名 datatype Pellet 实例层假不一致，削减实验定案，归因第四类「执行环境限制」——本体/用例零改动，执行器 strip 降级）→重跑 100%（超 90% 目标）。关键实证：G3 Transitive 闭包 ['IndR3','IndR2'] / X1·X2 内联 oneOf 实例层真强制 / X3 R6 实质生效 / E4·X5 open-world 正确。产物=`黄金用例集.md`+`测试报告.md`+`golden-cases-result.json` |
| G3 验收终审 | ✅ **通过** | 呈报=测试报告+黄金用例集+S5 拓扑报告+8 件套清单+G2 备案；终审结论=通过交付（含代拟黄金用例专家确认 + S5 拓扑报告抽核认可）。ontology.ttl 为终版基线 |

## 敏感自查

输入即虚构资料（构造时已执行五项遮盖纪律）；产物落盘前仍按 S3-S6 时序跑 grep 自查（机构名/证件号/手机号模式）。
