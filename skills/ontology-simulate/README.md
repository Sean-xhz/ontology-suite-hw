# ontology-simulate：本体 what-if 模拟验证 skill

> 在专家复核过的本体上做**实例级业务模拟**：客户画像+诉求 → 合规实例编译 → Pellet 物化推理（推断层分离+规则归因）→ 业务语言解读报告；另含 **A/B 三臂实验协议**（本体臂/描述集臂/裸臂），量化「形式化相对自然语言的增量」。
> 当前版本见 SKILL.md frontmatter；版本历史见 `CHANGELOG.md`。
> **本文件=人类手册**（三受众拆分：SKILL.md=LLM 执行契约 / README=人类手册 / CHANGELOG=版本历史）。

## 一、解决什么问题

本体建好并通过专家审阅后，仍要回答两个问题：

1. **这套规则对具体业务画像会给出什么判定？**（what-if）——业务专家不写一行 TTL，口述画像即可推演；每个结论挂规则 ID 溯源，「未推出≠否定」的开放世界语义如实呈现
2. **形式化本体相对自然语言描述、相对裸模型，到底带来多少增量？**（A/B）——三臂同题面同契约同模型对照，机械判据+专家盲评双通道，AG2 终审后才可对外引用数字

**三闸防臆造**：compiler 零臆造纪律 + check_instance 机械拦截（臆造属性/非法受控值/结论断言越权）+ SG1 人核实例忠实于画像。

## 二、快速上手（what-if）

```bash
# 1. 签名提取（编译约束词汇表；TTL 不变则 sha 不变，可复用）
python3 <skill根>/scripts/extract_signature.py <ontology.ttl> [--output signature.json]
# 2. 实例编译：自然语言画像→委托 ontology-whatif-compiler agent；
#    结构化画像（字段级已对齐 signature）→主会话直构。两路皆过同一硬闸门：
python3 <skill根>/scripts/check_instance.py <instance.json> <signature.json>   # exit 1=缺陷清单回修
# 3. 物化推理（双快照 diff+逐规则归因；--render-md 出业务语言渲染层）
python3 <skill根>/scripts/simulate_reason.py --instance <instance.json> --ttl <ontology.ttl> \
    [--signature <signature.json>] [--attribution rules|none] [--json-output sim-result.json] [--render-md 渲染.md]
# 4. 业务解读：委托 ontology-whatif-interpreter agent → 解读报告（每断言挂规则/公理 ID）
# 5. 零回写断言：shasum ontology.ttl golden-cases.json 前后一致（显式执行留输出）
```

`<skill根>`=本 skill 根目录（Claude Code 环境=`.claude/skills/ontology-simulate/`；独立套件=`skills/ontology-simulate/`）。跨 skill 复用 ontology-model 的 canonicalize_base/find_java 与 ontology-review 的 parse_ttl（相对路径 import，三 skill 须同级部署）。

**闸门**：SG1（实例合规：机器侧 check_instance + 人核忠实于画像）/ SG2（解读报告确认：结论链忠实+业务口径）——停等用户，不代签。

**时间预期**：小规模（5 规则归因）~1 分钟；大规模（44 规则自动降级 attribution=none）单次物化 ~15s；canonical 缓存大规模本体 ~60s 一次性摊销。

## 三、A/B 三臂实验（第二协议）

| 臂 | 注入材料 |
|---|---|
| ①本体臂 | 该题画像物化结果（render-md 业务语言渲染+原始 JSON 双轨）；L1 题=signature TBox 摘要 |
| ②描述集臂 | 29句话描述集全文 |
| ③裸臂 | 无（仅通用指令） |

流程：题库编制（素材白名单+gold 裁定，见 `references/ab-protocol.md` 题库编制契约）→ 冻结双哈希 → 三臂×每题独立会话（ab-responder agent，臂别中立隔离目录）→ `ab_score.py score` 机械判据 + 盲评表单（A/B/C 乱序代名，映射表仅主会话持有）→ 专家盲评回收 → `ab_score.py aggregate`（含评分者间一致率）→ 六节报告（公平性披露+样本量限制为强制节）→ **AG2 终审停等**。

参数建议值：题量 10-15/盲评 2 人（一致率计算最低人数）/1-5 分三维度——可调须登记；题库改动即重冻结+全量重跑。

完整协议条款（三臂定义/应答契约版本/编制契约/执行纪律/AG2 终审）见 `references/ab-protocol.md`（协议迭代唯一入口）。

## 四、环境与目录约定

**依赖**：python3（3.9+）+ rdflib + owlready2 + JRE（**Pellet 需 Java ≥25**，`find_java()` 自动选最高版本，`OWL_JAVA_EXE` 可覆盖）。引擎限制与失败归因见 ontology-model `references/reasoner-limits.md`（限制⑭ canonical 确定性档/孤立场景 exempt 纪律同源）。

**工作目录**：默认本体 run 目录旁 `模拟demo/`（每问题一组 instance/sim-result/report）；可另设 workspace 目录。

**画像受控双轨**（敏感纪律，对齐 ontology-model `references/sensitivity-rules.md`）：

| 轨道 | 前提 | 产物去向 |
|---|---|---|
| 真实案例（受控） | ①输出只写受控目录（不进版本控制/不进入对外分发通道）②产物不外发不入对外示例 ③个人标识（姓名/证件号/联系方式）一律替换为虚构标识 | 仅 run 目录受控区内部流转 |
| 虚构画像 | 与黄金用例五项遮盖同构 | 对外分发产物（examples/demo/A/B 材料）一律用此轨 |

**沙箱铁律**：模拟实例与物化结果**零回写**本体/黄金集——T6 hash 断言强制。

## 五、边界（不做）

- 本体编辑（ontology-model 入口 (c) 管；模拟发现本体问题→登记回流，不直改）
- 审阅批注（ontology-review 管）
- 排序/评分等应用层计算（本体只给判定与依据，决策权归外部）

## 六、目录结构（skill 根）

```
ontology-simulate/
├── SKILL.md                  # T0-T6 执行契约 + A/B 协议指针（LLM 编排入口）
├── README.md                 # 本文件（人类手册）
├── CHANGELOG.md              # 版本历史（执行不依赖）
├── references/               # ab-protocol.md（A/B 三臂实验协议全文，迭代唯一入口）
├── assets/                   # prompt-whatif-compiler / prompt-whatif-interpreter
│                             # / tpl-sim-report / prompt-ab-responder（三臂共用应答契约 v1.1）
│                             # / tpl-ab-questionbank（题库契约）/ tpl-ab-report（六节报告）
└── scripts/                  # extract_signature / check_instance（E01-E10 机械校验）
                              # / simulate_reason（物化+归因+canonical 缓存+render-md）
                              # / ab_score（score 机械判据 + aggregate 盲评聚合）
```

配套 agents（Claude Code 形态，部署于 `.claude/agents/`）：ontology-whatif-compiler（T2，只读）/ ontology-whatif-interpreter（T5，只读）/ ab-responder（A/B 三臂应答，只读，臂别无关）。平台中立纪律与适配说明见套件 `agents/README.md`。

## 七、姊妹 skill

- **ontology-model**：上游产本体（8 件套）；模拟发现的本体问题走入口 (c) 回流
- **ontology-review**：同基线审阅层（通常先过 AG1 再做模拟）

## English Summary

**ontology-simulate** runs instance-level business simulation on an expert-reviewed ontology: customer profile + request → compliant instance compilation (zero-fabrication discipline + `check_instance.py` mechanical gate) → Pellet materialization (dual-snapshot diff isolates the inferred layer; per-rule attribution; canonical cache) → business-language interpretation with rule-ID provenance and honest open-world semantics ("not inferred ≠ negated"). A second protocol provides a three-arm A/B experiment (ontology arm / description-set arm / bare LLM arm; same question bank, same response contract, same model — differing only in injected materials; mechanical scoring + expert blind review behind the AG2 final gate), quantifying the increment of formalization over natural language. Sandbox iron rule: zero write-back to the ontology/golden cases (hash-asserted). Execution contract: `SKILL.md`.
