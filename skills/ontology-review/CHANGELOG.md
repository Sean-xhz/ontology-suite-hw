# ontology-review CHANGELOG

> **版本约定**：semver（MAJOR.MINOR.PATCH）——MAJOR=执行契约不兼容变更（R 阶段/闸门/回流契约改变）；MINOR=新增能力或条款；PATCH=措辞与修正。frontmatter `metadata.version` 为当前版本（skill schema 不支持顶层 version 属性，登记于 metadata）。子协议版本（意见 JSON schema）在对应版本条目登记，不随 skill 版本号联动。
> **本文件=构建档案层**（C1/N11 三受众拆分：SKILL.md=执行契约 / README.md=人类手册 / CHANGELOG.md=档案）。执行不依赖本文件；「实证证据登记」节为从执行资产迁出的构建史与证据链，开源发行可选携带。历史指针中的 vault 构建区路径仅为溯源记录，不构成运行依赖。

## 1.2.4（2026-11-12）— 纯净化：部署表述泛化

- **README 受控区惯例泛化**：「vault 环境惯例：受控区=git 忽略区（如 `03 当前工作/`）」改为中性表述「受控区=不进版本控制的目录（如版本控制忽略区）」——套件对外分发不暴露本地目录结构。执行契约零改动。
- **版本判据**：措辞修正 → PATCH。

## 1.2.3（2026-11-11）— 文档结构治理：呈现纪律抽出 references（防堆砌）

- **R2 呈现纪律独立成文**：新增 `references/presentation-discipline.md`——五组规范性条款（信息分层/主题归组/记法与交互/plain_swrl() 角色定名算法契约/模板实现硬约束）自 SKILL.md R2 原样迁出，**条款编号（②③④⑤⑥⑦及 b/c 后缀）不变**（全链稳定引用位）；文件头立防堆砌纪律（呈现规范迭代一律在该文件内，SKILL.md 只留指针）+ 编号稳定规则（修订不改编号/废止保留编号不复用）；union 共享属性呈现观察项登记入「待迭代观察项」节（parse_ttl 修复前后等价，非回归）。
- **SKILL.md R2 瘦身**：保留命令+七区概述+硬门禁指针（通俗翻译零占位符），条款全文改指针。self_test.py E8/E10 断言标签编号不变（仅 docstring/注释指针更新），机械回归零影响。
- **README/资产索引联动**：目录结构补 references/ 行；人类手册呈现描述补指针。
- **版本判据**：条款搬家、语义零变更、执行契约（R 阶段/闸门/回流）零改动 → PATCH。

## 1.2.2（2026-11-11）— 引擎维护批次：parse_ttl 确定性修复（T4 signature 重生成前置）

- **bnode 非确定性修复（输出表示修正）**：rdflib bnode 标签跨进程随机，原实现经 `local()` 泄漏入输出——object_properties.domain/range、data_properties.domain（及合并层 owner 回退）具名字段改为只承载具名 IRI localname；匿名类表达式（owl:unionOf 等）→ 空串，联合成员经 domain_union/range_union 承载（2026-11-09 union 字段成为匿名值域唯一权威通道）；inverseOf 同步具名守卫。check_instance.domain_ok 语义不变（union 优先/空 domain 视为不限）——非 union 匿名值域旧行为必误报、新行为视为不限，严格改进。
- **rules.variables 语义修正**：原实现误遍历 body/head 的 atom 列表收集 atom bnode 标签（语义错误+跨进程随机）；改从已解析 atom 实参导出本规则真实变量名（? 前缀，与 arguments 记法一致，排序去重）。该字段当前消费链无下游读取（模板/plain_swrl/self_test 均不消费）——修正为输出诚实性与确定性。
- **确定性纪律成文**：输出禁含 rdflib bnode 随机标签；具名字段只承载具名 IRI；匿名表达式 → 空串+结构化成员字段。双跑字节一致成为硬验收（套件 T4 升级）。
- **版本判据**：缺陷修复+输出表示修正，消费端全兼容（check_instance 正反例/self_test E1-E10/simulate_reason label_map 实证），执行契约（R 阶段/闸门/回流）零改动 → PATCH（版本约定「措辞与修正」）。
- **联动重生成（套件 examples 虚构载体）**：票据_signature.json（历史三类漂移消除：union 字段补齐/bnode 域标签→空串/SWRL 变量 ? 前缀记法采用）+ review.json ×2 + 审阅页 ×2（页面标题经 --run-name 保持「票据贴现_20261026」场景标识；页面同步至当前模板含 N2 许可头；meta.run_dir 更新为套件 examples 路径=fixture 自包含溯源）。套件 T4 验收由计数口径升级为全量一致+双跑确定性。

## 1.2.1（2026-11-11）— Phase C 开源工程（N2 vendor 合规 + N7 i18n）

- **N2 vendor 合规**：vendor-dagre.min.js / vendor-cytoscape-dagre.js 补注 MIT 全文许可头（上游 dist/构建不带许可头；原始代码字节未改动，仅前置注释；许可文本逐字取自上游 LICENSE，经 jsdelivr npm 包渠道获取）；cytoscape.min.js 上游自带许可头未改动。新增 `assets/vendor-LICENSES.md`（版本锁定登记：dagre **0.8.5** 与上游 v0.8.5 dist 字节级哈希一致 / cytoscape **3.30.4** 文件内版本字符串 / cytoscape-dagre 版本未确证按 sha256 锁定 + 三库许可全文 + 补注登记）。许可头随单文件 HTML 分发旅行（build_review_page VENDORS 注入），满足 MIT 副本声明要求。补注后验证：node --check 两文件 + self_test 10/10（E7 构建/E9 语法）。
- **N7 i18n**：README 增 English Summary 节；目录结构 assets 注记补 vendor-LICENSES.md 登记件。

## 1.2.0（2026-11-11）— Phase B 内核纯净化（课题 1 前置）

- **C1/N11 三受众拆分**：SKILL.md 纯净化为执行契约；README.md 新建（人类手册）；本 CHANGELOG 建立。
- **R1 选型依据凝练**：SKILL.md 定位节只保留规范性结论（自建 cytoscape+硬门禁四条），三外采组件实测明细迁本文件 A 节。
- **R2 呈现纪律规范化**：由「多轮反馈修复史」重写为规范性条款组（信息分层/主题归组/记法与交互/模板实现硬约束四组），条款编号（②③④⑤⑥⑦及 b/c 后缀）保持稳定——self_test E8/E10 断言标签同步改按 R2 条款编号引用；plain_swrl() 角色定名算法契约全保留；三轮修复史迁本文件 B 节。
- **C2 路径参数化**：脚本调用改 `<skill根>/scripts/…` 约定；self_test.py 删除 VAULT/DEFAULT_RUNS 硬编码——fixture run 必须经 `--runs` 或环境变量 `ONTOLOGY_SELFTEST_RUNS`（os.pathsep 分隔）显式传入，都缺 → exit 2 带指引（**行为变更**：旧版缺省自动跑 vault 内基准 run，新版无隐式默认）。
- **N6 受控目录表述**：「git 忽略区/追踪区」泛化为「受控目录（不进版本控制/不进入对外分发通道）/可分发」，vault git 惯例降为 README 使用建议。
- **N1 版本体系**：frontmatter 加 `metadata.version`（schema 合规修正：顶层 version 属性不被 skill schema 支持，VS Code 诊断捕获后移入 metadata，版本号语义不变）；本文件建立（历史版本回溯登记见下）。
- **脚本构建期编号净化**：review_extract docstring「课题2 风险1」注记改通用表述；review.json `meta.extractor` 字段由「v1.0（课题2 Phase 1）」改「review_extract.py（ontology-review skill）」（**输出元数据措辞变更**，无断言/下游契约依赖）；引擎行为注释日期锚点保留。

## 1.1.0（2026-11-10）— Phase A + 套件 v2/v3 通用化

- **C4 交付通道中立**：协作平台绑定描述删除（R3 分发方式由调用环境自定）；保留「虚构载体可分发/真实载体仅本地」分级。
- **载体中立化清理**（套件 v2/v3 共享批次）：构建/验收历史注记改通用措辞，敏感纪律本体全保留；模板与示例表述载体中立。

## 1.0.0（2026-11-10）— skill 上线（课题 2 Phase 1）

- R0-R5 管线：review_extract 双源解析（TTL 结构权威 + md 表专家语言层）→ build_review_page 七区单文件审阅页（cytoscape 图示+规则双通道+批注 UI，浏览器直开零依赖）→ AG1 专家审阅停等 → ingest_opinions 意见单（忠实转录）→ 双通道回流（严重→入口 (c) 本轮重编译；建议→下轮 G1/S2）。
- self_test.py 机械回归层 E1-E10（专家实审反馈的回归用例化）。
- AG1 专家试点通过：虚构示例载体 demo 页 + 真实载体本地页（真实载体敏感纪律：仅本地）。

---

## 实证证据登记（构建史档案，自执行资产迁出）

### A. 图示选型实测明细（原 SKILL.md 定位节，2026-11-11 迁出）

- **硬门禁四条**：SWRL 规则呈现 / hasKey 可见 / 内联 oneOf 枚举不变形 / 中文 label 渲染。
- **三外采组件实测**（Phase 0，各加载虚构示例载体 ontology.ttl）：OntoInk / WebVOWL / Reactodia 全不满足硬门禁——生态空白在规则层（现存工具只覆盖类图/实例图层），图示组件可外采但规则维度必然自建。终裁=自建 cytoscape 单文件 HTML。
- **WebProtégé 出局证据**（课题 2 前置调研）：round-trip 实测 SWRL hollowing + inverseOf 丢失——在线协作编辑平台不可承载「审阅+修改」一体，故本 skill 审阅与修改分离承载（意见回流走入口 (c)）。
- 实测清单原始档案=vault 构建区 `00 构建资料/课题2-Step0-图示与物化实测清单.md`（溯源记录，不构成运行依赖）。

### B. R2 呈现纪律三轮修复史（2026-11-05 真实载体 AG1 实审，2026-11-11 迁出）

- **第一轮**（①-⑦）：①属性名空值（首列取名+表头归一）与实体表切列（转义管道）；②类平铺无层次→继承根分组；③④宽表撑破窄屏→横向滚动+动态列；⑤规则逐 TTL imp 出卡重复→按业务编号合并标通道；⑥空定义静默「—」→显式 ⚠；⑦批注无反显→回填编辑态。
- **第二轮**（①②③⑧）：①单条覆盖不满足多意见场景→同构件多条批注+北京时间双时间戳；②缩进无色条→30px/层+层级色条（**旧版 18px 缩进因 CSS 同特异性被 `.rulecard{margin}` 覆盖从未生效，注入自测捕获**——`.rulecard.depth-N` 提权纪律由此固化）；③批注列需拖到最右→sticky 右置+长表折叠（**评估裁定选折叠不选分页**：审阅常需上下行对照，分页切断对照）；⑧业务专家读不懂 SWRL 结构→plain_swrl() 通俗逻辑层（确定性模板翻译，不过 LLM）。
- **第三轮**：通俗翻译 ?1 类占位符仍有人脑对照成本→角色名词代入零占位符（三遍定名算法）；**截断 line-clamp 直接挂 td 覆盖 `display:table-cell` 破坏表格网格（内容纵叠/表头错位）→必须挂 td 内层 div**（`.tbl-wrap .clip`）。
- 纪律沉淀：每个真实失败=一条 self_test 断言；修复史不再留在执行契约，规范条款以当前有效形态登记于 SKILL.md R2。

### C. self_test 断言 ↔ 反馈轮次映射（原 docstring 标签，2026-11-11 迁出）

| 断言 | 来源轮次 |
|---|---|
| E2/E3 | 一轮①（属性名空值/转义管道切列） |
| E4 | 一轮⑤（规则重复卡） |
| E5 | 一轮②（分组层次） |
| E6 | 一轮⑥（空定义静默） |
| E8 | 一轮③④⑦ + 二轮①②③⑧（呈现结构在位） |
| E10 | 二轮⑧建层、三轮去占位符 |

### D. AG1 试点与回归基准

- AG1 专家试点（2026-11-10 通过）：虚构示例载体 demo 页（可分发）+ 真实载体本地页（仅本地，敏感纪律）；试点同时收集可用性反馈（能否看懂/批注是否顺畅/缺什么）。
- 机械回归基准 fixture=虚构示例载体建模 run（套件 `examples/` 内同源副本）；1.2.0 起经 `--runs`/`ONTOLOGY_SELFTEST_RUNS` 显式传入（C2 行为变更登记）。
