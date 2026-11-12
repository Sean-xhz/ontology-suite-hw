# Agent 定义一览与平台适配指南

> 本目录含五个 agent 定义，为 **Claude Code 参考实现**（`.claude/agents/` 形态）。脚本层平台无关；agent 层按本指南适配其他平台。
> 异构纪律为方法论硬约束，不绑定任何平台或模型别名。

## 一、五 agent 一览

| Agent | 消费 skill / 阶段 | 职责 | 工具 | 模型（参考实现） |
|---|---|---|---|---|
| ontology-generator | ontology-model S3 生成 / S4 辩护 | 29 句话描述集 + 术语词典 → W3C Turtle 本体；逐条回应审计缺陷 | Read, Write, Edit, Glob, Grep | opus |
| ontology-auditor | ontology-model S4 审计 | 黑盒三维度审计（语法规范性 / 逻辑一致性 / 业务贴合度），四元组缺陷报告 | Read, Glob, Grep（只读） | sonnet |
| ontology-whatif-compiler | ontology-simulate T2 | 客户画像 + 诉求 + signature → 本体合规实例 JSON（零臆造） | Read, Glob, Grep（只读） | 由编排指定 |
| ontology-whatif-interpreter | ontology-simulate T5 | 物化 diff + 规则归因 → 业务语言解读报告（每断言挂规则 ID 溯源） | Read, Glob, Grep（只读） | 由编排指定 |
| ab-responder | ontology-simulate A/B | 共用应答契约回答业务题，三段式 JSON（结论 / 依据 / 置信度）；臂别无关 | Read, Glob, Grep（只读） | 由编排指定 |

所有 agent 均**不主动触发，仅接受 skill 编排调用**。generator 是唯一可写 agent（只在 run 目录写）；其余四个只读，产出文本返回主会话落盘。

## 二、异构纪律（硬约束）

**生成与审计两角色必须由不同模型承担，禁止同模型自审。**

- Claude Code 参考实现：generator = opus，auditor = sonnet（别名与底层模型映射若变更，异构性须复核）。
- 其他平台：按同构纪律配置两个不同底层模型分别承担生成与审计角色。模型选择以能力特征为准（生成者偏业务理解与表达力，审计者偏推理严密与指令遵循），不以别名为准。
- compiler / interpreter / ab-responder 无固定模型绑定，由 skill 编排按任务需求指定；A/B 实验三臂须同模型配置（公平性纪律，见 `skills/ontology-simulate/references/ab-protocol.md`）。

## 三、平台适配四条款

1. **角色映射**：将五个 agent 定义映射为目标平台的等价机制（system prompt + tool 权限 + 模型配置）。agent 定义中的铁律与输出契约须完整保留。
2. **工具权限**：generator 须有 run 目录写权限；其余四个严格只读。目标平台若无细粒度工具权限，以 prompt 纪律 + 主会话复核承接。
3. **异构配置**：生成 / 审计两角色配置不同底层模型（§二）；配置变更后复核异构性。
4. **编排入口**：agent 由 skill 主会话编排委托（非用户直接触发）；目标平台须支持主会话→子 agent 委托与结果回收机制。

## English Summary

Five agents ship as a **Claude Code reference implementation**. The script layer is platform-agnostic; adapt the agent layer per this guide.

**Heterogeneity discipline (hard constraint):** the generator and auditor roles MUST run on different underlying models — no self-review. `opus`/`sonnet` are Claude Code reference aliases, not a platform binding. Other platforms: configure two different models with matching capability profiles (generator: business comprehension + expressiveness; auditor: rigorous reasoning + instruction following).

**Adaptation checklist:** (1) map each agent definition to the target platform's equivalent mechanism (system prompt + tool permissions + model config), preserving all iron rules and output contracts; (2) generator gets run-directory write access, the other four are strictly read-only; (3) configure different models for generator/auditor and re-verify heterogeneity after any config change; (4) agents are invoked by skill orchestration (not user-triggered) — the target platform must support main-session → sub-agent delegation with result collection.