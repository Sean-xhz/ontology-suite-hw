# what-if 模拟验证报告：票据贴现 demo1（多手背书·承兑人 A 级）

> 票据贴现 demo1 ｜ 生成：2026-11-04 ｜ ontology-simulate T5
> 本体基线：`票据贴现_20261026/（本示例快照）ontology.ttl` ｜ sha=ec85ca9598b4 ｜ 实例：`demo1-instance.json` ｜ 物化结果：同目录 `demo1-sim-result.json`

## 一、画像与诉求

> 虚构画像，无真实客户数据（scenario+query 忠实转录自 instance.json / sim-result）。

**画像（scenario 原文）**：持票人经多手背书取得票据后申请贴现，承兑人信用 A 级——触发 R1 持票核对 + R3 A 级禁止 + R7 背书链衔接的并发推理。

**诉求（query 原文）**：评估该多手背书票据的贴现资格：申请是否有效？票据是否可贴现？给出触发规则的逐条依据。

画像要素（输入事实·业务语言，全量见 instance.json）：

- **票据**（indBill1）：票号 PJ202604010012，票面金额 50 万元，2026-04-01 出票、2026-10-01 到期
- **承兑人**（indAcc1）：信用等级 **A**
- **背书链**（同票两条记录）：第 1 手 2026-04-10，持票人 H0→H1；第 2 手 2026-04-20，H1→H2
- **当前持票人**：H2（= 链末被背书人）
- **贴现申请**（indApp1）：编号 ZX202604200001，2026-04-20 提交（与第 2 手背书同日——取得票据当日即发起申请），状态「已提交」，期望贴现金额 49.5 万元；发起人 H2，针对上述票据

## 二、推理结论（业务语言）

机器总况：consistency=**consistent**（画像与本体公理无冲突）；物化 tag=full，断言 580 → 583，净增推断 3 条、撤回 0 条；逐规则归因模式（attribution_mode=rules，已编译 SWRL 规则 5 条）。

### 结论 1：申请是否有效？——**有效**

**该贴现申请（ZX202604200001）是「有效申请」：申请发起人与票据当前持票人为同一人，R1 持票核对通过。**

依据链：
- 输入事实：申请 indApp1 由持票人 indH2 发起（initiatedBy「申请发起人」）；申请针对票据 indBill1（targetsBill「针对票据」）；该票据当前持票人为 indH2（currentHolder「当前持票人」）。
- 推断事实：`indApp1 → 有效申请（ValidApplication）`（sim-result.inferred 第 1 条）
  - 归因：**ruleR1「R1 发起人持票核对规则」**（若申请发起人是该票据当前持票人，则申请有效）——机器形态以 initiatedBy 与 currentHolder 共享同一变量实现身份同一性核对，本例两者均指向 indH2，前提命中。
- 边界说明：R1 的否定方向（非持票人发起一律拒绝）由应用层执行（建模方案 Q4-1 裁定，SWRL 无否定语义）；本次为正向命中，不涉及否定分支。

### 结论 2：票据是否可贴现？——**不可：禁止贴现（R3 评级拦截档）**

**该票据（PJ202604010012）被判定为「禁止贴现票据」：承兑人信用等级为 A 级，触发 R3 A 级禁止贴现规则，处置档＝禁止贴现（拦截，强约束）。**

依据链：
- 输入事实：票据 indBill1 的承兑人为 indAcc1（hasAcceptor「票据承兑人」）；承兑人信用等级 creditRating="A"。
- 推断事实：`indBill1 → 禁止贴现票据（NonDiscountable）`（sim-result.inferred 第 2 条）
  - 归因：**ruleR3「R3 A 级禁止贴现规则」**（承兑人评级 A 级 ⇒ 该票据禁止贴现）——输入评级值 "A" 命中规则前提。违反处置（源 4.3）：禁止贴现（拦截）。
- **处置档区分（纪律要点）**：同为 NonDiscountable 类成员，处置按归因规则分档——本条归因 ruleR3（**评级拦截档**：禁止贴现、拦截、强约束），而非 ruleR5（**小额仅登记档**：不进贴现池+留痕、弱约束、非拦截）。本例 R5 未触发（票面 50 万元 ≥ 10 万元门槛），不存在小额登记情形。依据链命中规则编号是处置分档的唯一依据，不得笼统合并为「不可贴现」——建模方案 :NonDiscountable comment 残留风险 1 同款登记（不得仅凭类成员身份硬拦截，须按命中规则编号区分，7.6/X2）。
- **与结论 1 并存的处置含义（资格冲突场景）**：推理机报告 consistent——「申请有效」（作用于申请）与「票据禁止贴现」（作用于票据）之间**无公理互斥**（互斥公理 L3 仅约束 Discountable ⊥ NonDiscountable 两结论类），两条结论合法并存。业务含义＝「**申请有效但票据禁贴**」：R1 的「有效」仅指发起人资格核对通过（形式有效性），不构成贴现许可；贴现资格由票据侧规则判定，本例被 R3 拦截。受理处置：该票据不得进入贴现（拦截档）；后续申请状态迁移与拒绝动作由应用层按状态机执行（快照语义，见 §四），本模拟不含状态迁移推断。

### 结论 3：背书链是否衔接连续？——**连续（首→末可达）**

**背书记录 1（H0→H1）与记录 2（H1→H2）有效衔接：第 1 手被背书人＝第 2 手背书人（同为 H1），推导出记录 1 为记录 2 的链上游；isUpstreamOf 具传递性，首→末可达，即该票据背书链（已建模范围内）连续——背书有效。**

依据链：
- 输入事实：票据挂两条背书记录（hasEndorsementRecord「票据背书记录」）：记录 1（序号 1，2026-04-10，背书人 H0→被背书人 H1）、记录 2（序号 2，2026-04-20，背书人 H1→被背书人 H2）。
- 推断事实：`indEnd1 →（链上游背书记录 isUpstreamOf）→ indEnd2`（sim-result.inferred 第 3 条）
  - 归因：**ruleR7「R7 背书链有效衔接推导规则」**（同一票据 ∧ 序号相邻 n2=n1+1 ∧ 前手被背书人=后手背书人 ⇒ 有效衔接）——机器形态：swrlb:add 判定序号相邻（2=1+1）＋共享变量判定衔接（记录 1 被背书人 H1 = 记录 2 背书人 H1）。
  - 闭包表述（传递闭包纪律）：「链连续」由 **ruleR7 相邻衔接推导 ＋ isUpstreamOf 传递性（Transitive）** 共同导出——首记录→末记录可达 ⟺ 全链相邻衔接（R7 机器判定形态）。本链仅两手，该条上游关系即首→末可达。记录级闭包严格限定同票据内（建模方案裁量 10.5-3：取记录级而非持有人级，防跨票据误串链）。
- 业务含义：链末被背书人 H2 与输入的当前持票人一致（该一致性由数据管线保证，本体无公理绑定——建模方案残留风险 3 口径）；R7 源句「若背书链连续则背书有效」——本例链连续成立，「断裂票据不得贴现」分支未触发。
- 边界说明：R7 首手核对（出票时收款人 vs 第一手背书人 H0）所需数据位未建模（编译缺口-1/P2，应用层承接）——本体侧「链连续」结论**不含首手核对**；链形态线性（序号链内唯一递增，L8）亦由应用层核对承接。

### 综合受理判定（结论 1+2+3 汇总）

- 申请资格：R1 ✓ 有效 ｜ 背书链：R7 ✓ 连续 ｜ 票据贴现资格：R3 ✗ 禁止贴现（评级 A，拦截档）
- **受理结论：申请形式有效、背书链连续，但票据因承兑人 A 级评级被禁止贴现——贴现资格不成立，处置＝拦截（R3 拦截档）。** 输出形态为「结论＋依据链」，平台不做审批承诺（建模方案 5.7/X3：资金方独立决策）。
- 未触发规则（5 条已编译 SWRL 规则中）：**R4**（前提＝评级 AAA ∧ 过 R2 核对——本例评级为 A，前提不满足）；**R5**（前提＝票面 <10 万元——本例 50 万元，前提不满足）。R2/R6 非 SWRL 推断位（R2 应用层降级、R6 DL 公理），登记见 §四。

## 三、推断事实清单（输入 vs 推断分层）

机器物化：tag=full ｜ asserted 580 → after 583 ｜ diff_inferred=3 ｜ retracted=0 ｜ attribution_mode=rules（rules_total=5）

| # | 主体 | 推断（label_map 译） | 归因 | 层级 |
|---|------|------|------|------|
| 1 | indApp1（贴现申请 ZX202604200001） | 有效申请（ValidApplication） | ruleR1「R1 发起人持票核对规则」 | 推断 |
| 2 | indBill1（票据 PJ202604010012） | 禁止贴现票据（NonDiscountable） | ruleR3「R3 A 级禁止贴现规则」 | 推断 |
| 3 | indEnd1 → indEnd2（背书记录 1→2） | 链上游背书记录（isUpstreamOf；首→末可达＝链连续） | ruleR7「R7 背书链有效衔接推导规则」 | 推断＋闭包 |

> 输入事实（画像断言）：8 个个体＋10 条关系断言，不列全表，见 demo1-instance.json（§一 已给业务语言摘要）。推断与输入严格分层：上表 3 条全部为推理器产出（instance_level=true，attribution_mode=rules 逐规则归因），无一条为画像原始断言。

## 四、处置档与开放世界登记

1. **处置档区分（R3 拦截 vs R5 仅登记）**：结论 2 归因 ruleR3 ⇒ 拦截档（禁止贴现，强约束）。若同结论归因 ruleR5（票面<10 万），处置为「仅登记」：不进贴现池＋留痕，非拦截（弱约束）。本例仅命中 R3，不存在合并处置；依据链命中规则编号是分档唯一依据（建模方案残留风险 1）。
2. **资格冲突并存（R1×R3）**：consistent——申请侧「有效」与票据侧「禁贴」并存非公理冲突；处置以票据侧 R3 拦截为准，「申请有效」≠「可贴现」（结论 2 详述）。
3. **R2 间隔受理未断言（应用层承接位，非推理机缺口）**：R2 双条件核对（申请日期<到期日期 ∧ 间隔≥15 天）按 Q4-2 裁定降级为应用层执行，本物化未产出 :AcceptableApplication 断言（instance 未断言、inferred 无此结论）。开放世界语义如实登记：**本次物化对该申请的 R2 可受理性未判定**——不得据此报告「可受理」或「不可受理」；如需完整受理链，须应用层核对后断言 :AcceptableApplication 再触发重推理。
4. **R4 可贴现推导未触发**：前提＝评级 AAA ∧ AcceptableApplication，本例评级 A（≠AAA）且 R2 结论未断言，双重不满足。本票据的可贴现性已由 R3 **反向判定**（NonDiscountable），不属「AA 级未判定」开放世界情形（该语义见建模方案 :Discountable comment 残留风险 2——AA 票据两结论类均不获推导、未判定≠不满足，本画像评级为 A，不涉及）。
5. **快照语义**：全部规则判定均为受理时快照（本体无时间轴；建模方案 §4.R 快照语义登记）——评级/状态/持票人变动后须由应用层触发重新推理，本报告结论仅对当前断言集有效。
6. **R7 降级部分**：链连续结论不含首手核对（P2 数据位缺口，应用层承接）；「断裂⇒不得贴现」的拦截处置亦由应用层执行（本次链连续成立，未涉及）。
7. **R6 审核互斥**：本快照申请状态为「已提交」，无「审核中」申请——R6 基数公理无涉及、无违反检出。

## 五、存疑项

| 项 | 状态 | 说明 |
|---|---|---|
| multi_rule_joint 多规则联合归因 | 无 | 3 条推断均为单规则归因（ruleR1/R3/R7 各 1 条，attribution_summary 1+1+1） |
| schema_propagation 类推断 | 无 | diff 3 条全部为实例级规则推断（instance_level=true），无 schema 层传播项 |
| 画像未编译概念 | 无 | instance.json 无 compiler 未编译概念登记 |
| 归因降级（none/auto-degraded） | 无 | attribution_mode=rules，逐规则归因完整，非大本体降级 |
| label_map 覆盖缺口 | 无 | 本次涉及的类/属性/规则（ValidApplication／NonDiscountable／isUpstreamOf／ruleR1／ruleR3／ruleR7）均有业务名映射。附注：label_map 不含 ruleR2/ruleR6——R2 应用层降级无 SWRL 规则、R6 为 DL 公理，属设计而非缺口，本次亦未触发。个体名（indApp1 等）为实例标识符非词汇表项，报告中以「个体名＋业务角色」并列标注 |
| **W08 facet 校验缺口 ×4** | **有（值已合规）** | 票号 'PJ202604010012'、票面金额 500000、申请编号 'ZX202604200001'、期望贴现金额 495000 四值未在模拟侧做 pattern/facet 校验（具名 datatype BillNumberFormat／ApplicationNumberFormat／PositiveAmount，L2 承接）。人工比对 ttl pattern 原文（`PJ[0-9]{12}`／`ZX[0-9]{12}`／minExclusive 0）：四值均合规。**流程价值登记**：首版 fixture 票号 13 位、申请编号 APP 前缀两处违例被本报告 W08 登记项人工比对捕获（模拟侧不拦 facet 的设计下，登记+比对即兜底）——fixture 已修正重跑；本体侧「建模方案 §2.1⑧ 示例值同为超长形态」的系统性出入（编译缺口-2，编号位数假设待 G2 确认）仍为遗留，下轮 G1/S2 复核 |

## 六、推理机原语数据（机械转录，防漂移）

```json
{
 "consistency": "consistent",
 "inconsistency_detail": null,
 "materialize": {
  "tag": "full",
  "asserted": 580,
  "after": 583,
  "diff_inferred": 3,
  "retracted": 0,
  "bnode_subject": 0,
  "inconsistent": null,
  "t_load": 0.2,
  "t_sync": 10.5
 },
 "inferred": [
  {
   "subject": "indApp1",
   "predicate": "type",
   "object": "ValidApplication",
   "raw": "<http://example.org/bill-discount#indApp1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/bill-discount#ValidApplication> .",
   "instance_level": true,
   "attribution": [
    "ruleR1"
   ]
  },
  {
   "subject": "indBill1",
   "predicate": "type",
   "object": "NonDiscountable",
   "raw": "<http://example.org/bill-discount#indBill1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/bill-discount#NonDiscountable> .",
   "instance_level": true,
   "attribution": [
    "ruleR3"
   ]
  },
  {
   "subject": "indEnd1",
   "predicate": "isUpstreamOf",
   "object": "indEnd2",
   "raw": "<http://example.org/bill-discount#indEnd1> <http://example.org/bill-discount#isUpstreamOf> <http://example.org/bill-discount#indEnd2> .",
   "instance_level": true,
   "attribution": [
    "ruleR7"
   ]
  }
 ],
 "attribution_summary": {
  "ruleR1": 1,
  "ruleR3": 1,
  "ruleR7": 1
 },
 "attribution_mode": "rules",
 "rules_total": 5,
 "notes": [
  {
   "level": "warning",
   "code": "W08",
   "message": "属性 billNumber 为具名 datatype BillNumberFormat（pattern 类）——模拟侧不做 facet 校验（L2 承接），值 'PJ202604010012' 未验证"
  },
  {
   "level": "warning",
   "code": "W08",
   "message": "属性 faceAmount 为具名 datatype PositiveAmount（pattern 类）——模拟侧不做 facet 校验（L2 承接），值 500000 未验证"
  },
  {
   "level": "warning",
   "code": "W08",
   "message": "属性 applicationNumber 为具名 datatype ApplicationNumberFormat（pattern 类）——模拟侧不做 facet 校验（L2 承接），值 'ZX202604200001' 未验证"
  },
  {
   "level": "warning",
   "code": "W08",
   "message": "属性 expectedDiscountAmount 为具名 datatype PositiveAmount（pattern 类）——模拟侧不做 facet 校验（L2 承接），值 495000 未验证"
  },
  "canonicalize 缓存命中（sha=ec85ca9598b4）"
 ]
}
```
