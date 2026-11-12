# 本体能力套件（Ontology Capability Suite）

> 业务场景自动化本体建模 → 可视化审阅 → 模拟验证与 A/B 实证的三件套能力快照（载体中立，适用各行业域）。
> 冻结日期：2026-11-12（**v8 重冻结**）｜三 skill 本体能力套件 + 开源工程资产｜中文 ｜ [English](README.en.md)
> 发布状态：**工程资产就绪，发布暂缓**（用户裁定 2026-11-11）——LICENSE/CI/单测/vendor 合规/Pages 站点已落套件；发布目录与 push 待用户决定时再做。

## v8 变更记录（2026-11-12，纯净化 + 盲测模板补齐 + 引擎归因成文）

用户三项确认（2026-11-12）：①引擎限制归因（版本低 vs 其他原因，升级是否解决）；②交付分级与通道节删除 + 盲测还原率对照报告模板补齐；③全套件纯净度审计（不含个人/企业隐私，可对外提供）。

1. **model 1.5.0**：新增 `assets/tpl-restoration-report.md`（盲测收卷必产物模板：双口径公式/五矩阵/误报漏检三分类/效力诚实声明）；交付分级与通道独立段删除（分级纪律浓缩为 manifest 收卷条目，通道 boilerplate 删除）；`references/reasoner-limits.md` 新增 §七 归因分类与升级路径判断（A 绑定层/B 引擎缺陷/C 能力边界 + 升级纪律）；README 部署表泛化（vault 具体路径→中性占位）。
2. **review 1.2.4**：README 受控区惯例泛化（去 vault 具体路径）。simulate 1.2.3 不变。
3. **examples 纯净化（14 文件）**：用户本机绝对路径（consistency/validate/review.json×2/审阅页×2/S5拓扑/demo1-4-sim-result）+ vault 相对路径（run-manifest/缺陷报告/demo1-sim-report）→ 中性相对路径；java_exe 全路径→`java`；demo ttl 字段→套件内相对。终态：本机绝对路径零残留 + vault 路径零残留。
4. **纯净度审计结论**：企业名/品牌名/人名清单/邮箱/信贷真实载体措辞 = **全零命中**。保留项（C1/C3 设计，非隐私）：KC 卡 ID 来源括注（methodology-core 逐条溯源）/ methodology-index（vault 可选附录）/ CHANGELOG 构建档案 / LICENSE 署名 Sean-xhz（用户裁定，发布时可调）。
5. **agents/README.md 重建**：rsync 全目录误操作修复（误增非本体 agent 已移除，README 重建：五 agent 一览 + 异构纪律 + 适配四条款双语）。
6. **重冻结验收**：权威↔快照 rsync 字节级一致（skills×3 + agents×5）；统一入口 **PASS 11 / FAIL 0 / SKIP 0**；三态复核 ✓；敏感扫描零命中；**102 文件**（+1 模板）零缓存。

## v7 变更记录（2026-11-11，文档结构治理批次：知识库叙述清理 + 三项结构调整，防堆砌）

用户审阅套件提出（2026-11-11）：①删除与套件无关的知识库更新事件叙述（如主题域 02→09 迁移——套件已把知识库内容焙入 methodology-core）；②三个结构问题（model 限制⑩⑭为何内联单摘 / review 呈现纪律是否独立 / simulate A/B 协议是否独立），确立「可迭代领域规范不能堆砌式叠加在 SKILL.md」原则。三项调整经用户批准执行（权威 `.claude/` 先行）：

1. **知识库事件叙述清理（10 处/5 文件）**：删 vault 知识库事件叙述（拆域迁移/旧路径修正事件/卡片治理修订事件/EL·CLAUDE.md 事件引用/卡版本事件标记/来源文件名），留构建溯源指针（vault 构建区路径/卡 ID 来源括注/部署约定/A/B 发行披露）——C1/C3 既定边界（溯源记录非运行依赖）。涉及 model CHANGELOG×3、methodology-core×2、methodology-index（用户套件侧编辑先镜像回权威）、本 README×2、examples run-manifest×3；复扫零命中。
2. **model 限制⑩⑭内联浓缩（1.4.2）**：S6 两段引擎机制详述浓缩为单一「实例级推理执行纪律」块——机制与证据已自包含于 reasoner-limits.md（1.4.0 内核化只切指针未浓缩，本次补齐）；操作纪律全保留（strip/canonical 默认档认知、禁盲改→两次确定性确认→削减实验、漂移期单次结果不构成证据、并发压力用例主载体、孤立 FAIL 转 exempt 第四类、本体零改动、facet 校验 L2 承接）+ 指针。执行语义零变更。
3. **review 呈现纪律抽出 references（1.2.3）**：新增 `skills/ontology-review/references/presentation-discipline.md`——R2 五组规范性条款原样迁出，**条款编号不变**（全链稳定引用位，self_test E8/E10 断言标签零影响，T1 复跑 10/10 实证）；文件头立防堆砌纪律+编号稳定规则（修订不改编号/废止保留不复用）；v6 登记的 union 共享属性呈现观察项迁入该文件「待迭代观察项」节。SKILL.md R2 留命令+七区概述+硬门禁指针（通俗翻译零占位符）。
4. **simulate A/B 协议抽出 references（1.2.3）**：新增 `skills/ontology-simulate/references/ab-protocol.md`——三臂定义/应答契约 v1.1 注/题库编制契约 4 条/执行纪律 6 条原样迁出；文件头立防堆砌纪律+子协议版本独立登记指针。SKILL.md 留三臂一句话定义+AG2 终审闸门（人工闸门属执行契约）+资产指针；铁律 7（盲评不露臂别）留铁律节。应答契约 v1.1/题库 schema 1.0 不联动。
5. **文档分层纪律成文（套件级）**：SKILL.md=薄执行契约（阶段/闸门/铁律/指针）；可迭代领域规范→各 skill `references/`（编号稳定，迭代在 reference 内发生）——与 reasoner-limits/methodology-core 既有模式同构，见「定位与权威关系」节。
6. **版本**：model **1.4.2** / review **1.2.3** / simulate **1.2.3**（PATCH——条款搬家与叙述清理，语义零变更，执行契约零改动）；子协议不联动；三 CHANGELOG 登记。
7. **重冻结验收**：权威↔快照 rsync 字节级一致（skills×3+agents×5）+ YAML 三版本校验 ✓；统一入口 **PASS 11 / FAIL 0 / SKIP 0**（T1 self_test E1-E10 10/10=条款编号稳定实证；T4 双跑字节一致+冻结件全量一致；T8 物化推断 3/3 ruleR1/R3/R7+零回写 ✓）；--skip-java PASS 10 / SKIP 1 exit 0、坏根 exit 2 三态 ✓；全套件敏感扫描零命中；套件 **101 文件**（+2 references）+ 零缓存残留（含 .sim-cache 检查）+ 电池零副作用。

## v6 变更记录（2026-11-11，引擎维护批次：parse_ttl 确定性修复 + T4 冻结件重生成）

用户指令（2026-11-11）：待办中继续推进 T4 signature 重生成，其余暂缓项不动。按引擎维护批次口径执行（权威 `.claude/` 先行，独立 smoke + 全链复验）：

1. **确定性修复（review_extract.parse_ttl，review 1.2.2）**：rdflib bnode 标签跨进程随机，原实现经 `local()` 泄漏入输出——三处泄漏点修复：object_properties.domain/range、data_properties.domain（及合并层 owner 回退）具名字段只承载具名 IRI localname，匿名类表达式（owl:unionOf 等）→ 空串（联合成员经 domain_union/range_union 承载）；inverseOf 同步具名守卫；rules.variables 语义修正（原实现误遍历 atom 列表收集 atom bnode 标签 → 改从已解析 atom 实参导出本规则真实变量名，? 前缀排序去重）。确定性纪律成文：输出禁含 bnode 随机标签。
2. **T4 冻结件重生成（examples 虚构载体，5 文件）**：票据_signature.json（历史三类漂移消除：union 字段补齐 / bnode 域标签→空串 / SWRL 变量 ? 前缀记法采用）+ review.json ×2 + 审阅页 ×2（页面标题经 --run-name 保持「票据贴现_20261026」场景标识；页面同步至当前模板含 N2 MIT 许可头——demo 页自此满足 MIT 副本声明；meta.run_dir 更新为套件 examples 路径=fixture 自包含溯源）。ttl_sha 不变（ec85ca9598b4），本体/黄金集零改动。
3. **T4 验收口径升级（run_suite_tests.py）**：计数口径 → **全量 JSON 相等 + 双跑字节确定性**（非确定性回归直接 FAIL）；新口径首跑 PASS。
4. **版本**：review **1.2.2** / simulate **1.2.2**（PATCH——缺陷修复+输出表示修正，消费端全兼容，执行契约零改动；simulate 脚本零改动，依赖驱动联动登记）；model 1.4.1 不变。子协议不联动。
5. **独立 smoke + 全链复验**：signature/review.json 双跑字节一致 ✓；新输出 bnode 零残留 ✓；check_instance 正例 exit 0 / 反例 exit 1 ✓；self_test E1-E10 10/10 ✓；统一入口 **PASS 11 / FAIL 0 / SKIP 0**（T8 物化推断 3/3 ruleR1/R3/R7 + 零回写 ✓）；权威↔快照 rsync 字节级一致（skills×3+agents×5）+ YAML 三版本校验 ✓；套件 **99 文件**不变（重生成为原位刷新）+ 零缓存残留。终态校验发现并清理历史杂散缓存 1 处（`examples/票据贴现/模拟demo/.sim-cache/`，手动 demo 运行的 canonical 缓存，mtime 11-10；统一入口 T8 自创建起即 `--cache-dir` 外置临时目录，核实非电池副作用）——清理后全量电池重跑 PASS 11，examples 零副作用实证（缓存不复现），99 文件复核 ✓。
6. **呈现观察项登记（不处置）**：union 域共享数据属性（unifiedSocialCreditCode）owner 回退为空串，类卡片视图不按组显示（模板按 owner===类 id 过滤）——修复前后行为等价（旧 bnode owner 同样不匹配），属呈现设计议题，留后续迭代。

## v5 变更记录（2026-11-11，课题 1 Phase C 批次：开源工程资产，发布暂缓）

用户四项裁定（2026-11-11）：**LICENSE=MIT** / **只备工程资产，发布暂缓**（不建发布目录/不建远端/不装 gh）/ **N7=中文主体+英文 README/摘要** / **N12 第二示例暂缓**。按盘点清单 §3 序执行：

1. **N2 vendor 合规**：dagre/cytoscape-dagre 补注 MIT 全文许可头（上游 dist/构建无头；原始代码字节未改，仅前置注释；node --check + self_test 10/10 验证）；新增 skill 级 `assets/vendor-LICENSES.md`（版本锁定：dagre **0.8.5** 与上游 v0.8.5 dist 字节级哈希一致 / cytoscape **3.30.4** 文件内版本字符串 / cytoscape-dagre 版本未确证按 sha256 锁定 + 许可全文 + 补注登记）；套件根 `THIRD-PARTY-LICENSES.md`（三库 MIT 全文 + pip 依赖许可注记 rdflib BSD-3-Clause / owlready2 LGPL-3.0 + 方法论致谢）。许可头随单文件 HTML 分发旅行（VENDORS 注入），满足 MIT 副本声明要求。
2. **N4 bootstrap**：`requirements.txt`（owlready2==0.51 钉住——引擎行为按 0.51 登记〔限制⑧〕；rdflib>=7.6.0,<8）+ `scripts/bootstrap.sh`（python≥3.9/pip/Java≥25/node 检查 + 可选验收）+ `.github/workflows/tests.yml`（python 3.9/3.12 矩阵 × temurin 25 × node 20；**写而不本地跑**，发布后随仓库启用）。
3. **N5 统一验收**：`scripts/run_suite_tests.py`（T0-T10 编排，examples 虚构载体为 fixture，一切输出落临时目录零副作用，--skip-java 降级档，exit 0/1/2）替代手工命令组合；首跑 **PASS 11 / FAIL 0 / SKIP 0**，三态验证 ✓；CI 消费同一入口。
4. **N3 平台中立**：model SKILL.md 铁律 4 抽象为「生成/审计两角色须不同模型，禁止同模型自审」（opus/sonnet 降为 Claude Code 参考实现注记，S3/S4 同步）；新增 `agents/README.md`（五 agent 一览 + 异构纪律 + 适配说明，双语）；model/simulate README 配套 agents 节增指针。三 skill PATCH 升版（model **1.4.1** / review **1.2.1** / simulate **1.2.1**，CHANGELOG 登记）。
5. **N7 i18n**：`README.en.md`（英文门面：定位/三件套/quickstart/环境/测试/许可/敏感纪律/致谢）+ 三 skill README 各增 English Summary 节；**执行资产保持中文**（无翻译漂移风险）。
6. **LICENSE=MIT**（套件根，版权署名 Sean-xhz，发布时可调整）+ 方法论来源致谢（《本体驱动的AI数据管理》编写组）。
7. **暂缓项登记**：发布动作（发布目录/远端/push）待用户决定；N12 第二跨域示例留开源后迭代；Pages/docs 站点随发布批次；**T4 示例 signature 重生成**改留后续引擎维护批次（bnode 域标签确定性修复属引擎变更，须独立 smoke+全链复验，不在本批工程资产范围；计数口径验收持续有效）。
8. **重冻结验收**：权威↔快照字节级 diff 一致（skills×3+agents×5）；统一入口 PASS 11 / FAIL 0 / SKIP 0 + 零副作用（无缓存残留）；新资产敏感词扫描零命中；套件 **99 文件**（README 2+LICENSE 1+THIRD-PARTY 1+requirements 1+scripts 2+CI 1+agents 6+examples 33+skills 52）。examples/ 未改动。

## v4 变更记录（2026-11-11，课题 1 前置盘点 Phase B 批次，内核纯净化重构）

1. **三受众拆分（C1/N11）**：每个 skill 确立三层文档——`SKILL.md`=LLM 执行契约（纯净化，构建期 Phase 编号/裁定日期/修复史全部迁出）/ `README.md`=人类手册（快速上手/环境约定/边界）/ `CHANGELOG.md`=构建档案（版本史+实证证据登记，开源发行可选携带）。新增 6 文件：model CHANGELOG + reasoner-limits、review README + CHANGELOG、simulate README + CHANGELOG（model README 重写）。CHANGELOG 中的历史 vault 路径仅为溯源记录，不构成运行依赖。
2. **路径参数化（C2/N6）**：run 根目录三级解析（调用显式传入 > 环境变量 `ONTOLOGY_RUNS_ROOT` > README 部署默认）；脚本调用统一 `<skill根>/scripts/…` 约定（Claude Code 与独立套件两种部署形态同构）；「git 忽略区/追踪区」泛化为「受控目录（不进版本控制/不进入对外分发通道）/可分发」，vault git 惯例降为 README 使用建议。**行为变更**：review `self_test.py` 删除 vault 硬编码缺省路径——fixture 必须经 `--runs` 或 `ONTOLOGY_SELFTEST_RUNS` 显式传入，都缺 → exit 2 带指引（本次冻结中修复了「指引文案称 exit 2 实际 exit 1」的退出码缺陷，三态实测验证）。
3. **引擎限制内核化（M4）**：新增 `ontology-model/references/reasoner-limits.md`（限制①-⑭编号稳定 + SWRL 规范 v2 摘要 + 三级降级链 + L2/L3 分工 + 削减实验矩阵 A-E，自包含）；全部外部文档引用（原 vault 构建区 `L3-reasoner环境与用法.md`，含脚本注释松引用）切换至内核。
4. **覆盖矩阵（M3）**：7 类语义×三态（编译进 TTL / md 扩展位登记 / 不承接）显式表进 model SKILL.md 边界节与 README；扩展位路线图单列（无排期承诺，启用条件=消费场景硬需求+G1 范围评审）。
5. **呈现纪律规范化（R1/R2）**：review SKILL.md 图示选型凝练为规范性结论（硬门禁四条+自建 cytoscape），三外采实测明细迁 CHANGELOG；R2 由多轮修复史重写为四组规范条款（编号稳定，self_test E8/E10 断言标签同步按条款编号引用），plain_swrl() 角色定名算法契约全保留。
6. **A/B 协议补强（S4/N9/N10）**：题库编制契约成文（出题素材白名单/编制分工/gold 冲突裁定分支/冻结双哈希）；实验参数建议化（题量 10-15、盲评≥2 人、评分维度可调须登记，历史 run 口径不回改）；T2 编译双路径（自然语言画像→compiler agent / 结构化画像→主会话直构，check_instance 统一硬闸门）。
7. **版本体系（N1）**：三 skill SKILL.md frontmatter 加 `metadata.version`（model **1.4.0** / review **1.2.0** / simulate **1.2.0**，semver；skill schema 不支持顶层 `version` 属性，VS Code 诊断捕获后移入 metadata，版本号语义不变）；子协议版本独立登记不联动（应答契约 v1.1、题库 schema 1.0、golden-cases schema 1.0、SWRL 规范 v2）。
8. **其余裁定落地**：N8 敏感前置检查改外置词表机制表述（泛化模式内置 closeout_check，真实词表经 `--patterns` 传入、永不入 skill 资产）；脚本文件头构建任务史净化（引擎行为注释日期锚点保留）；agents/fibo-guide 的 KC 来源括注按「溯源非运行依赖」边界保留。
9. **重冻结验收**：权威↔快照字节级 diff 一致（skills×3+agents×5）；套件内 T1-T10 全过（见下表，T4 按计数口径）+ py_compile 全过 + 运行零副作用（无缓存文件残留）；套件 **90 文件**（README 1+agents 5+examples 33+skills 51）。examples/ 未改动。

## v3 变更记录（2026-11-10，课题 1 前置盘点 Phase A 批次，用户四项裁定落地）

1. **方法论内核化（C3 裁定）**：新增 `ontology-model/references/methodology-core.md`——把 vault 28 张方法论卡（KC-20261013-001~028）中管线执行依赖的判据细节按 Stage 焙为**自包含内核**（逐条括注来源卡 ID，附录 28 卡溯源表）；SKILL.md 全部「读 KC-xxx」执行引用切换为内核章节；methodology-index 降级为深度溯源索引并修正卡片来源路径。**套件脱离 vault 可独立执行**。
2. **图 6-1 口径修正（M1）**：按用户提供的原书图核对，7 类合计 **29 子项**（2/7/3/1/5/4/7）确认；tpl-29-sentences 子项表实为编译导向重构（合计 32 子项），删除历史「读图 28 差 1」错误防御表述。
3. **结构化映射通用化（M2 裁定）**：structured-input-mapping 重写为**通用四步法**（章节语义识别判据表→run 级映射表→机械映射→缺口分级），原十一节表降为附录示例并进一步中性化。
4. **盲测降级（M6 裁定）**：主路径=生成式建模（入口 (a)/(b)）；盲测重定位为「辅助验证模式」（以历史人工方案为对照基准校准能力时启用），非日常建模入口。
5. **画像受控双轨（S1 裁定）**：what-if 模拟在受控前提（输出只写受控目录/产物不外发/个人标识一律去除）下**接受真实案例输入**；虚构画像收窄为对外分发产物与无受控目录场景；compiler agent/prompt/报告模板联动修订（「画像虚构红线」→「个人标识去除红线」）。
6. **交付通道中立（C4）**：三处协作平台绑定描述全删——交付/页面分发/盲评回收均改「方式由调用环境自定」，保留内部分级与 scores JSON 归一契约；三 skill 零残留（grep 验证）。
7. **重冻结验收**：权威↔快照字节级 diff 一致（skills×3+agents×5）；套件内 T1 self_test 10/10（`--runs` 指向 `examples/票据贴现/建模run`）/ T2 golden-cases --check 16 用例 / T8 demo1 物化实跑推断 3/3 与快照一致（ruleR1/ruleR3/ruleR7）/ T10 品牌名 0 命中 / py_compile 全过；新改文件载体词与敏感词扫描零命中；套件 **84 文件**（README 1+agents 5+examples 33+skills 45）。

## v2 变更记录（2026-11-10 重冻结）

1. **通用化清理（65 处/18 文件）**：skills/agents 描述中与构建时/验收时具体载体耦合的定制化表述全部泛化为「虚构载体/真实载体/基准 run」通用措辞；模板与 prompt 中的**虚构配例按设计保留**（示例纪律）；FIBO 指南保留其金融域公共标准扩展定位。硬编码清理含：ab-responder 角色设定去企业背景、`ab_score.py --carrier` 缺省值改「虚构示例载体」（复现历史表单须显式传入原载体名）、ontology-model description 从「金融场景」泛化为「业务场景（金融、保险、供应链、制造等行业域）」。
2. **套件改进（A/B 报告 §4 改进项落实）**：`simulate_reason.py` 新增 `--render-md`（物化结果经 label_map 确定性渲染为业务语言 md，不过 LLM）；A/B 应答契约升级 **v1.1**——本体臂材料双轨注入（渲染层+原始 JSON）+三臂统一表述纪律（业务语言作答、结构记法只入依据括注）。协议 v1.1 下轮 run 生效，历史两 run 数字按 v1.0 口径不回改。
3. **重冻结验收**：T1-T3/T7/T8/T10 + ab_score smoke 套件内重跑全过（T8 推断三元组 3/3 与快照一致，render-md 渲染验证 ✓）；权威 vs 套件 skills/agents 字节级一致 diff 校验 ✓；套件 83 文件（README+agents 5+examples 33+skills 44）。

## 定位与权威关系

- **运行权威** = vault 的 `.claude/skills/ontology-{model,review,simulate}/` 与 `.claude/agents/`（Claude Code 加载路径）；**本目录 = 发行快照**（冻结副本，课题 1 开源时以此迁出）。两侧漂移时以运行权威为准，快照须重新冻结并更新本文件日期。
- `skills/` 子目录结构与 `.claude/skills/` 同构——脚本内跨 skill 相对 import（`../../ontology-model/scripts` 等）在套件内原样可解析（已实跑验证，见下）。
- **平台定位（N3）**：脚本层平台无关（python3）；agents 层为 Claude Code 参考实现（frontmatter `model: opus/sonnet` 为别名注记）——异构质检纪律平台中立（生成/审计两角色须不同模型），其他平台适配见 `agents/README.md`。
- **文档分层纪律（防堆砌，v7）**：`SKILL.md`=薄执行契约（阶段/闸门/铁律/指针）；可迭代领域规范在各 skill `references/`（methodology-core / reasoner-limits / presentation-discipline / ab-protocol 等——条款编号稳定，迭代在 reference 内发生，SKILL.md 不叠加条款）；`README.md`=人类手册；`CHANGELOG.md`=构建档案（执行不依赖）。

## 三件套

| skill | 定位 | 管线 |
|---|---|---|
| **ontology-model** | 「7+1」29 句话描述集 → W3C 规范 TTL 本体（RDF/OWL/SKOS/SWRL） | S0-S6 + G1-G3 人工闸门 + 双模型异构质检（generator/auditor）+ L1-L3 机械校验 + 黄金用例业务验收，8 件套交付 |
| **ontology-review** | 建模成果 → 业务专家可读的单文件审阅页（图示+规则双通道+批注） | R0-R5：提取（TTL 权威/建模方案表专家语言层）→ cytoscape 单文件 HTML → 专家批注 → 意见单回流（G1/S2 或入口 (c) 重编译） |
| **ontology-simulate** | 专家复核过的本体 → what-if 物化推演 + A/B 三臂实证 | T0-T6：画像+诉求 → 实例编译（零臆造+check 闸门）→ 物化推理（双快照 diff+规则归因）→ 业务解读；A/B 协议：本体臂/描述集臂/裸臂 + 机械判据 + 专家盲评（AG2 终审） |

配套 agents（`agents/`）：ontology-generator / ontology-auditor（双模型异构质检）、ontology-whatif-compiler / ontology-whatif-interpreter（模拟编译与解读）、ab-responder（A/B 三臂应答，臂别无关）。

## 目录导览

```text
本体能力套件/
├── skills/            # 三 skill 冻结副本（SKILL.md 执行契约 + README 人类手册 + CHANGELOG 构建档案 + assets/references/scripts）
├── agents/            # 五 agent 定义冻结副本 + README（角色一览/异构纪律/平台适配，双语）
├── examples/票据贴现/  # 全虚构发行示例（可对外）：建模 run + 审阅与意见 + 模拟 demo
├── scripts/           # bootstrap.sh（环境引导）+ run_suite_tests.py（统一验收入口，N5）
├── requirements.txt   # Python 依赖（owlready2==0.51 钉住 + rdflib>=7.6,<8）
├── docs/              # GitHub Pages 站点（index.html 门面 + demo.html 审阅页在线预览）
├── .github/workflows/ # CI 矩阵（tests.yml）+ Pages 部署（pages.yml）——发布后启用
├── LICENSE            # MIT（主许可）
├── THIRD-PARTY-LICENSES.md  # 第三方许可汇总（捆绑 JS 三库 + pip 依赖注记 + 方法论致谢）
├── README.md          # 本文件（中文）
└── README.en.md       # 英文门面（N7）
```

## 环境依赖

- python3（≥3.9）+ `rdflib` + `owlready2`（L1/L2 校验、提取、物化）——**`requirements.txt` 钉住实证版本**（owlready2==0.51，引擎行为按该版本登记）；一键引导=`bash scripts/bootstrap.sh`（依赖检查+安装+可选验收）
- Java + Pellet/HermiT 推理机 jar（L3 一致性与 SWRL 物化；**Pellet 需 Java ≥25**、HermiT ≥17；jar 随 owlready2 pip 包内置；引擎版本/JRE 要求/路径发现与限制登记见 `skills/ontology-model/references/reasoner-limits.md`）
- node（可选，仅 review `self_test.py` 的模板 JS 语法检查项，缺失降级 skip）
- CI：`.github/workflows/tests.yml`（python 3.9/3.12 矩阵 × temurin Java 25 × node 20，消费统一验收入口；发布后随仓库启用）

## 验收状态（2026-11-12 v8 重冻结后套件内实跑）

**统一入口（N5）**：`python3 scripts/run_suite_tests.py`（T0-T10 编排，examples 为 fixture，零副作用，`--skip-java` 降级档；exit 0/1/2）——v8 复跑 **PASS 11 / FAIL 0 / SKIP 0**（含 T0 py_compile 13 脚本；T4 全量一致+双跑确定性；T1 self_test E1-E10 10/10）；`--skip-java` 档 PASS 10 / SKIP 1 exit 0、坏套件根 exit 2，三态验证 ✓。CI 消费同一入口。

| # | 项 | 结果 |
|---|---|---|
| T1 | review `self_test.py`（票据 run 全链） | 10/10 PASS（`--runs` 显式传入；无参/坏目录 exit 2 三态验证 ✓） |
| T2 | `run_golden_cases.py --check`（16 用例 schema） | exit 0 |
| T3 | `validate_ontology.py`（L1+L2） | exit 0 |
| T4 | `extract_signature.py` 产物 vs 冻结 signature | 双跑字节一致 + 冻结件全量一致（类 10/对象 9/数据 13/规则 5，见注） |
| T5/T6 | `check_instance.py` 正例 / 反例拦截 | exit 0 / exit 1 ✓ |
| T7 | 跨 skill import（run_golden_cases+review_extract 套件内解析） | ok |
| T8 | `simulate_reason.py` demo1 物化实跑（Pellet） | exit 0，推断 3/3（ruleR1/ruleR3/ruleR7）与快照一致，零回写断言 PASS |
| T9 | `closeout_check.py`（建模 run 收卷：齐套+敏感扫描） | exit 0 |
| T10 | 品牌名 grep 契约（虚构载体） | 0 命中 ✓ |

> T4 注：v6 引擎维护批次已修复 `parse_ttl` bnode 非确定性并重生成冻结 signature——历史三类漂移（union 字段/bnode 域标签/`?` 前缀）消除，验收由计数口径升级为**全量一致 + 双跑字节确定性**（2026-11-11）。review.json ×2 与审阅页 ×2 同步重生成（见 v6 变更记录）；check_instance/simulate_reason 消费兼容由 T5/T6/T8 实证。

验收记录见各 skill `CHANGELOG.md` 实证证据登记。

## 许可与致谢

- **主许可=MIT**（`LICENSE`，用户裁定 2026-11-11；版权署名 Sean-xhz，发布时可调整）。
- **第三方许可**：`THIRD-PARTY-LICENSES.md`（捆绑 JS 三库 MIT 全文 + pip 依赖许可注记 + 方法论来源致谢）；skill 级版本锁定登记=`skills/ontology-review/assets/vendor-LICENSES.md`（dagre 0.8.5 字节级核验 / cytoscape 3.30.4 / cytoscape-dagre sha256 锁定）。
- **方法论来源**：《本体驱动的AI数据管理》（编写组著）公开方法论，经卡片蒸馏重编译为自包含执行内核（逐条来源括注）；套件不复制原书文本。

## 敏感纪律（红线）

1. `examples/` 只放**全虚构**载体（票据贴现）；真实业务载体 run 的任何产物**永不入套件**、永不外发。
2. skill/agent 资产永不写真实业务数据与人名；模板配例一律虚构中性。
3. 套件不含任何 API 凭据；对外发布前须再过一遍 `closeout_check.py` 敏感扫描。
