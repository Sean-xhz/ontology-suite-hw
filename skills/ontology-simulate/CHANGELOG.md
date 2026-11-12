# ontology-simulate CHANGELOG

> **版本约定**：semver（MAJOR.MINOR.PATCH）——MAJOR=执行契约不兼容变更（T 阶段/闸门/A/B 协议改变）；MINOR=新增能力或条款；PATCH=措辞与修正。frontmatter `metadata.version` 为当前版本（skill schema 不支持顶层 version 属性，登记于 metadata）。**子协议版本独立登记不联动**：应答契约（prompt-ab-responder.md）当前 v1.1；题库 schema 1.0。
> **本文件=构建档案层**（C1/N11 三受众拆分：SKILL.md=执行契约 / README.md=人类手册 / CHANGELOG.md=档案）。执行不依赖本文件；「实证证据登记」节为从执行资产迁出的构建史与证据链，开源发行可选携带。历史指针中的 vault 构建区路径仅为溯源记录，不构成运行依赖。
> **敏感纪律**：真实载体 run 的评分数字/答卷/盲评材料只落 run 目录受控区（内部流转），**本文件只记机制级结论与虚构载体数字**。

## 1.2.3（2026-11-11）— 文档结构治理：A/B 协议抽出 references（防堆砌）

- **A/B 实验协议独立成文**：新增 `references/ab-protocol.md`——三臂定义/应答契约版本注（v1.1）/题库编制契约 4 条/执行纪律 6 条自 SKILL.md 原样迁出；文件头立防堆砌纪律（协议迭代一律在该文件内，SKILL.md 只留三臂定义+AG2 闸门+指针）+ 子协议版本独立登记指针（CHANGELOG B 节）。
- **SKILL.md 瘦身**：A/B 节保留三臂一句话定义+AG2 终审闸门（人工闸门属执行契约）+资产指针；铁律 7（盲评不露臂别）留铁律节；定位节指针同步。应答契约 v1.1/题库 schema 1.0 不联动。
- **README/资产索引联动**：目录结构补 references/ 行；流程描述中「见 SKILL.md 题库编制契约」改指 reference；人类手册补完整协议指针。
- **版本判据**：条款搬家、语义零变更、执行契约（T 阶段/SG 闸门/A-B 协议实质）零改动 → PATCH。

## 1.2.2（2026-11-11）— 引擎维护批次：signature 确定性（依赖驱动，联动 review 1.2.2）

- **extract_signature 输出确定性**：本 skill 脚本零改动；共享解析层 review_extract.parse_ttl（ontology-review 1.2.2）修复 bnode 非确定性——signature 匿名 union domain/range 由随机 bnode 标签改为空串（联合成员经 domain_union/range_union 承载）。冻结 票据_signature.json 历史三类漂移（union 字段/bnode 域标签/? 前缀）经重生成消除；signature 双跑字节一致。
- **消费端兼容实证**：check_instance 正例 exit 0/反例 exit 1（domain_ok union 优先/空 domain 不限语义不变）；simulate_reason 只消费 signature 的 id/label（label_map），不受影响；T8 物化实跑重验（推断 3/3 + 归因 ruleR1/R3/R7 + 零回写）。
- **版本判据**：依赖驱动的输出表示修正，执行契约（T 阶段/SG 闸门/A-B 协议）零改动 → PATCH；子协议（应答契约 v1.1/题库 schema 1.0）不联动。

## 1.2.1（2026-11-11）— Phase C 开源工程（N3/N7）

- **N3 平台中立化**：README 配套 agents 节增套件 `agents/README.md` 指针（五 agent 一览 + 异构纪律平台中立表述 + 其他平台适配说明；套件级资产）。本 skill 执行契约不变（compiler/interpreter/ab-responder frontmatter 本无 model 别名绑定；A/B 三臂同模型公平性纪律本就平台中立）。
- **N7 i18n**：README 增 English Summary 节（执行资产保持中文）。

## 1.2.0（2026-11-11）— Phase B 内核纯净化（课题 1 前置）

- **C1/N11 三受众拆分**：SKILL.md 纯净化为执行契约（构建期 Phase 编号/裁定日期注记迁本文件）；README.md 新建（人类手册）；本 CHANGELOG 建立。
- **C2 路径参数化**：脚本调用改 `<skill根>/scripts/…` 约定；T0.3 工作目录默认=本体 run 目录旁 `模拟demo/`（真实载体必须在 run 目录内受控区）；vault workspace 路径惯例迁 README。
- **S4 题库编制契约成文**：出题素材白名单（建模方案 R 族规则表/F 族 L 族约束/残留风险登记/黄金用例同构变体，禁凭空出题）+ 编制分工（主会话构造+gold 裁定，agent 可扩展变体但 gold 须主会话裁定+用户确认）+ gold 交叉核验冲突裁定分支（gold 错→修 gold / 本体错→入口 (c)）+ 冻结双哈希——写入 SKILL.md A/B 协议节与 tpl-ab-questionbank.md。
- **N9 实验参数建议化**：题量 N≈12→建议 10-15（实证基线 12）；盲评 2 人=建议（一致率计算最低 2 人）；1-5 分三维度=建议默认（可调须登记）；三层占比为建议值。历史 run 口径不回改。
- **N10 编译路径裁定**：T2 补双路径——自然语言画像→compiler agent；结构化画像（字段级已对齐 signature）→主会话直构；两路皆合规，check_instance 为统一硬闸门（裁量依据见 D 节）。
- **N6 受控目录表述**：「git 忽略区/workspace git 追踪区」泛化为「受控目录（不进版本控制/不进入对外分发通道）/可分发」。
- **构建期编号清理**：SKILL.md/ab-responder description/脚本 docstring（ab_score 标题与 KC 引用、simulate_reason 技术路线注记）的「Phase 0/Phase 3」改通用表述（实测定案/A/B 实验阶段）；引擎行为注释日期锚点保留。
- **N1 版本体系**：frontmatter 加 `metadata.version`（schema 合规修正：顶层 version 属性不被 skill schema 支持，VS Code 诊断捕获后移入 metadata，版本号语义不变）；本文件建立（历史版本回溯登记见下）。

## 1.1.0（2026-11-10）— Phase A + 套件 v2/v3 通用化

- **S1 画像受控双轨**（用户裁定，裁定史见 C 节）：受控前提三条满足即真实案例可入模拟；个人标识去除为双轨通用红线；对外分发产物一律虚构。compiler prompt 联动修订。
- **应答契约 v1.0→v1.1**（子协议，史见 B 节）：simulate_reason `--render-md` 业务语言确定性渲染层 + 本体臂材料双轨注入 + 三臂统一表述纪律——下轮 run 生效，历史 run 不回改。
- **C4 交付通道中立**：盲评回收通道由调用环境自定（表单/文档/邮件均可），协作平台绑定描述删除。
- **载体中立化清理**（套件 v2/v3 共享批次）：ab-responder 角色去企业背景；构建/验收历史注记改通用措辞；`--carrier` 缺省值泛化为业务场景。

## 1.0.0（2026-11-10）— skill 上线（课题 2 Phase 2-3）

- **what-if 协议**：T0-T6（签名提取→实例编译→check_instance 机械闸门→Pellet 物化〔双快照 diff 推断层+逐规则归因+canonical 缓存〕→业务解读）+ SG1/SG2 停等闸门 + 沙箱零回写 hash 断言。
- **A/B 三臂实验协议**：本体臂/描述集臂/裸臂同契约独立会话、臂别中立隔离目录注入、ab_score 机械判据（label/要点覆盖/规则真实性/幻觉计数）+ 专家盲评聚合、AG2 终审闸门。
- **双载体实证完成**：虚构示例载体 run（12 题×36 应答，机械判据可对外）+ 真实载体 run（专家盲评 AG2 通过——载体与数字见内部 run 登记，不入本文件）。关键实证发现（机制级）见 E 节。

---

## 实证证据登记（构建史档案，自执行资产迁出）

### A. 执行内核技术验证（原 Phase 0，2026-11-11 迁出）

- **双快照 diff=推断层分离**：assert-only 快照 vs sync_reasoner 后快照，diff 三元组即推断层——owlready2 内存态断言/推断混存无标记，diff 是唯一可靠分离法；虚构载体 5 规则规模最小验证通过。
- **逐规则启停=归因**：R1 启停 diff 变化可观测；多规则并发场景归因碎裂风险→multi_rule_joint/schema_propagation 如实登记纪律（不粉饰为精确归因）。
- **bnode 漂移风险前置去险**：canonical 确定性档（复用 ontology-model run_golden_cases `canonicalize_base()`）+ `.sim-cache/<ttl_sha>.nt` 缓存，大规模本体 ~60s 摊销为一次性。
- 实测清单原始档案=vault 构建区 `00 构建资料/课题2-Step0-图示与物化实测清单.md`（溯源记录，不构成运行依赖）。

### B. 应答契约 v1.0→v1.1 史（2026-11-10 裁定，2026-11-11 迁出）

- **v1.0 损伤面**：本体臂注入原始物化 JSON，应答暴露规则 ID/物化记法（「ruleR1 触发」类表述），业务可读性受损且三臂表述风格不齐——风格差异可能污染盲评。
- **v1.1 三件套**：①`simulate_reason.py --render-md` 业务语言确定性渲染层（不过 LLM，保机械回归）；②本体臂材料双轨注入（渲染 md+原始 JSON，溯源记法保留在依据括注内/L1 题 TBox 摘要）；③三臂统一表述纪律（prompt-ab-responder.md 第 6条）。
- **生效纪律**：下轮 run 生效，历史两 run（虚构载体/真实载体）不回改——引用历史数字按 v1.0 口径披露。

### C. S1 画像受控双轨裁定史（2026-11-10 产品化盘点，2026-11-11 迁出）

- 用户裁定：what-if 的价值在真实业务问题推演——**受控范围内接受真实案例作为模拟输入**，才能真正贴合业务实际。
- 受控前提三条：①模拟输出只写受控目录；②真实案例轨道一切产物不外发、不入对外示例；③真实客户个人标识（姓名/证件号/联系方式）即使受控轨道也替换为虚构标识（业务要素结构保留、个人标识去除=双轨通用红线）。
- 虚构画像用于：对外分发产物（examples/demo/A/B 材料）、无受控目录时。compiler prompt 联动 6 处修订。

### D. N10 编译路径裁量（2026-11-11 Phase B 登记）

- compiler agent 的价值集中在**自然语言→结构化**的编译（画像语义理解+signature 词汇对齐）；结构化画像（字段级已对齐 signature）无需过 agent，主会话直构更快且少一层转录失真。
- 两路皆合规的前提=**check_instance 统一硬闸门不变**（臆造/越权/类型错机械拦截，与编译路径无关）；路径选择登记工作记录。

### E. A/B 参数实证依据与关键发现（机制级）

- **首轮参数即实证基线**：N=12（三层占比 L1~1/3、L2~5/12+、L3~1/4）/盲评 2 人/1-5 分三维度（业务正确性/解释质量/依据充分性）——虚构载体 run 12 题×36 应答全量执行；真实载体 run 采用精简题集（协议参数见内部 run 登记）。1.2.0 起为建议值非硬约束，调整须登记 run-manifest。
- **关键实证发现**（双载体互证，机制级结论）：①知识注入增量集中于系统特有事实题（裸臂 L1 事实题不可用）；②本体臂 vs 描述集臂实质正确性分野在 L3 边界开放世界行为（过度断言 vs undetermined，机械+盲评双通道互证）；③「未推出≠否定」需制度性载体（人类专家间亦有口径分歧）；④机械判据须人工复核分离口径误报（真幻觉 0）。
- **对外口径纪律**：对外材料仅用虚构载体 run 机械判据数字，并披露「专家盲评在真实载体执行、数字不可外发」；真实载体评分/一致率数字只在 run 目录受控区内部流转。
