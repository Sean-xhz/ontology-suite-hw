---
name: ontology-simulate
metadata:
  version: 1.3.1
description: 本体 what-if 模拟验证——客户画像+业务诉求（受控范围内接受真实案例，对外产物用虚构案例）→ 合规实例编译 → Pellet 物化推理（双快照 diff+逐规则归因）→ 业务语言解读报告。三闸门防臆造（check_instance 机械拦截/compiler 零臆造纪律/SG1 人核）。触发：「what-if 模拟」「本体推演」「模拟业务验证」「画像模拟」。
---

# ontology-simulate：what-if 模拟验证

## 定位与边界

在专家复核过的本体上（通常经 ontology-review AG1）做**实例级业务模拟**：把「客户画像+诉求」编译成合规实例 → 物化推理 → 归因到规则 → 业务语言解读。业务专家不写一行 TTL 就能验证「这套规则对这样的画像会给出什么判定」。

- **执行内核**：双快照 diff=推断层 / 逐规则启停=归因 / TBox 边界=类级走断言直读
- **不做**：本体编辑（入口 (c) 管）、审阅批注（ontology-review 管）。A/B 三臂实验=本 skill 第二协议（与 what-if 共享物化内核；完整协议见 `references/ab-protocol.md`）
- **沙箱铁律**：模拟实例与物化结果**零回写**本体/黄金集——模拟输出独立落盘，显式 hash 断言
- **路径约定**：脚本调用以 `<skill根>` 指本 skill 根目录（Claude Code 环境=`.claude/skills/ontology-simulate/`；独立套件=`skills/ontology-simulate/`）；跨 skill 脚本经相对路径 import，部署时三 skill 保持同级
- 版本历史=`CHANGELOG.md`（执行不依赖）；人类手册=`README.md`

## T0 输入定位

1. 确认本体 run 目录（`ontology.ttl` 须在）；敏感级判定（对齐 ontology-model `references/sensitivity-rules.md`）：**真实业务本体（真实载体 run）→ 模拟输出只写 run 目录内受控区（不进版本控制/不进入对外分发通道）**；虚构载体 run → 输出可入版本控制目录（可分发）
2. 画像输入纪律（真实/虚构双轨）：what-if 的价值在真实业务问题推演——**受控前提下真实案例可直接作为模拟输入**。受控前提三条：①模拟输出只写受控目录（不进版本控制/不进入对外分发通道）；②真实案例轨道的一切产物不外发、不入对外示例；③真实客户**个人标识**（姓名/证件号/联系方式）即使受控轨道也替换为虚构标识（业务要素结构保留、个人标识去除）。**虚构画像**（与黄金用例五项遮盖同构）用于两类场景：对外分发产物（examples/demo/A/B 材料）、无受控目录时。用户口述案例时先确认 run 目录受控归属，并在工作记录登记画像轨道（真实受控/虚构）
3. 工作目录：默认本体 run 目录旁 `模拟demo/`（每问题一组文件 instance/sim-result/report）；**真实载体必须在 run 目录内受控区**（T0.1）

## T1 签名提取

```bash
python3 <skill根>/scripts/extract_signature.py <ontology.ttl> [--output signature.json]
```

产出编译约束词汇表（类含 derived 标记/属性含受控值/规则面/instance_schema 契约）。signature 是 compiler 的唯一词汇来源——重复模拟复用同一 signature（TTL 不变则 sha 不变）。

## T2 实例编译

**编译路径裁定（双路径，check_instance 为统一硬闸门）**：
- **自然语言画像** → 委托 **ontology-whatif-compiler**（只读 agent）：传画像+诉求+signature 路径+`assets/prompt-whatif-compiler.md`，返回实例 JSON 全文
- **结构化画像**（字段级已对齐 signature）→ 主会话直构实例 JSON（少一层转录失真）

两路皆合规，路径选择登记工作记录；主会话落盘 `<问题名>-instance.json`。

画像来源三种：①用户直接给虚构画像；②用户给真实案例 → 按 T0.2 双轨判定（受控前提满足→直接编译；不满足→虚构化后编译）；③主会话按 demo 需求代拟（标注「代拟画像」）。

## T3 机械校验（SG1 机器侧）

```bash
python3 <skill根>/scripts/check_instance.py <instance.json> <signature.json>
```

exit 1（臆造/越权/类型错）→ 缺陷清单回编译侧修订（≤2 轮，超限停等用户裁决）；exit 0 过（warning 如 W08 具名 datatype 登记性提示，如实入报告存疑项）。

**T3 组合（数据完整性补闸，编排器职责）**：check_instance 是签名词汇表封闭闸门（防臆造/越权/类型错）；W08 具名 datatype 的 facet 实例校验由 ontology-model **SHACL 层（R4）**承接——编译产 TTL 后可喂 `ontology-model/scripts/validate_shacl.py <data.ttl> <shapes.ttl>`（shapes 经 `derive_shacl.py` 从本体派生）做 facet/基数/唯一性强制，再进 T4。三闸正交：check_instance（JSON 零臆造）→ validate_shacl（TTL 数据完整性）→ simulate_reason（物化推理）。契约见 ontology-model `assets/tpl-shacl-shapes.md`。

## T4 物化推理

```bash
python3 <skill根>/scripts/simulate_reason.py \
    --instance <instance.json> --ttl <ontology.ttl> \
    [--signature <signature.json>] [--attribution rules|none] \
    [--json-output <问题名>-sim-result.json] [--render-md <渲染.md>]
```

- 双快照 diff+逐规则归因（规则数 >12 自动降级 `none` 并登记——N+1 次 Pellet 成本）
- canonical 缓存（`.sim-cache/<ttl_sha>.nt`，大规模本体 ~60s 摊销为一次性）
- `consistency: inconsistent` = 画像与公理冲突被检出（重要业务结论，转 T5 如实报告，非失败）
- **时间预期**：小规模（5 规则归因）~1 分钟；大规模（44 规则降级 none）单次物化 ~15s
- **引擎限制与失败归因**：见 ontology-model `references/reasoner-limits.md`（限制⑭ canonical 确定性档/孤立场景失灵处置纪律同源；首跑失败禁止盲改，先确认确定性再做削减实验）

## T5 业务解读（interpreter agent + SG2 停等）

委托 **ontology-whatif-interpreter**（只读 agent）：传 sim-result.json+instance.json+`assets/prompt-whatif-interpreter.md`，按 `assets/tpl-sim-report.md` 产出报告全文，主会话落盘 `<问题名>-sim-report.md`。

**SG2 停等**：报告呈用户确认（画像→结论链是否忠实、处置档表述是否合业务口径）。解读有出入 → 回 T5 修（翻译问题）或发现本体问题 → 登记走入口 (c)/下轮 G1（**不直改本体**）。

## T6 收尾登记

1. **零回写断言**：`shasum <ontology.ttl> <golden-cases.json>` 前后一致（版本控制 diff 也可辅助）——显式执行并留输出
2. run-manifest / 工作记录追加模拟轮：问题清单/实例数/推断数/归因分布/一致性结论/SG2 结论/未编译概念登记
3. 限制⑭型场景（数值规则孤立、bnode 漂移影响归因）显式登记处置

## 闸门总览

| 闸门 | 位置 | 内容 | 停等对象 |
|---|---|---|---|
| SG1 | T2-T3 间 | 实例合规（机器侧 check_instance 拦臆造 + 人核实例忠实于画像） | 用户（机器不过先回编译侧；机器过后人核可并 SG2） |
| SG2 | T5 尾 | 解读报告确认（结论链忠实+业务口径正确） | 用户 |

## A/B 实验协议（三臂对照，第二协议）

三臂对照量化「形式化相对自然语言的增量」与「知识注入相对裸模型的增量」：**①本体臂**（注入该题画像物化结果——render-md 业务语言渲染+原始 JSON 双轨；L1 题=signature TBox 摘要）/ **②描述集臂**（注入 29句话描述集全文）/ **③裸臂**（无材料）。

完整协议（三臂定义/应答契约版本/题库编制契约/执行纪律/机械判据/专家盲评）见 `references/ab-protocol.md`——**协议迭代唯一入口**，SKILL.md 只留指针（防堆砌）。应答契约=`assets/prompt-ab-responder.md`（当前 v1.1）；题库契约=`assets/tpl-ab-questionbank.md`；报告骨架=`assets/tpl-ab-report.md`。

**AG2 终审（人工闸门·停等）**：六节报告（机械判据+盲评聚合+对照分析+**公平性披露**+**样本量限制与结论边界**为强制节）呈用户终审；**未过 AG2 的数字不入任何对外材料**；禁止「本体无用/万能」式泛化。

## 铁律

1. **零回写**——本体/黄金集/既有 run 产物永不因模拟被改；T6 hash 断言强制
2. **三闸防臆造**——编译纪律（零臆造）+ check_instance 机械拦截 + SG1 人核，三层不塌陷
3. **结论挂依据**——报告每断言可溯源（推断三元组+规则 ID 或输入事实），无源断言违规
4. **真实本体不出本地**——真实载体模拟输出只在受控目录（不进版本控制/不进入对外分发通道）；虚构载体可对外
5. **画像受控双轨**——真实案例可入模拟，但仅限受控目录且产物不外发；个人标识一律去除；对外分发产物（examples/demo/A/B 材料）一律用虚构画像
6. **归因不纯即登记**——multi_rule_joint / schema_propagation / 降级归因如实入报告，不粉饰为精确归因
7. **A/B 盲评不露臂别**——应答标注臂别哈希仅主会话持有；盲评表单/专家可见材料一律 A/B/C 代号乱序

## 资产索引

- `references/`：ab-protocol.md（A/B 三臂实验协议全文，协议迭代唯一入口）
- `scripts/`：extract_signature.py（TTL→签名）/ check_instance.py（E01-E10 机械校验，exit 0/1）/ simulate_reason.py（物化+归因+canonical 缓存+`--render-md` 业务语言确定性渲染〔A/B 本体臂材料可读层〕，复用 run_golden_cases 的 canonicalize_base/find_java 与 review_extract 的 parse_ttl——跨 skill import，禁分叉）/ ab_score.py（A/B：机械判据 score + 盲评聚合 aggregate，跨 skill import review_extract 建词汇表）
- `assets/`：prompt-whatif-compiler.md / prompt-whatif-interpreter.md / tpl-sim-report.md / prompt-ab-responder.md（三臂共用应答契约 v1.1）/ tpl-ab-questionbank.md（题库三层+编制契约+冻结纪律）/ tpl-ab-report.md（六节报告含强制披露节）
- agents：ontology-whatif-compiler（T2，只读）/ ontology-whatif-interpreter（T5，只读）/ ab-responder（A/B 三臂应答，只读，臂别无关）
- `README.md`（人类手册）/ `CHANGELOG.md`（版本历史，执行不依赖）
- 姊妹 skill：ontology-model（上游产本体；引擎限制登记=`references/reasoner-limits.md`）/ ontology-review（同基线审阅层）
