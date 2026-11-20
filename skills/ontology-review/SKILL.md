---
name: ontology-review
metadata:
  version: 1.3.1
description: 本体审阅页生成与专家意见回流——把 ontology-model 产出的 8 件套转成业务专家（零工程背景）可直接浏览器打开的单文件审阅页（六板块图示+规则双通道+批注+L1-L2 拖拽编辑），意见导出后机械回流入口 (c) 或下轮 G1/S2；D4 编辑产 patch 交 ontology-model R2 机械执行。触发：「专家审阅本体」「审阅页」「批注回流」「本体可视化审阅」「本体拖拽编辑」。
---

# ontology-review：本体审阅页与意见回流

## 定位与边界

把 ontology-model 的 8 件套交付物转化为**业务专家可自主审阅**的单文件 HTML（离线、零依赖、中文），并把专家批注**机械回流**到管线（不手抄）。

- **审阅与修改分离承载**：专家做批注与业务裁量，形式化修改走 ontology-model 入口 (c) 重编译——意见永不直接改 TTL
- **双通道规则呈现**：SWRL 原子结构（TTL 提取，结构权威）+ 自然语言陈述（建模方案，专家语言）逐条对齐——单通道各有盲区
- **不做**：本体编辑（入口 (c) 管）、实例级 what-if 推演（ontology-simulate 管）、多人在线协作
- **图示选型**：自建 cytoscape 单文件——外采组件实测不满足硬门禁（SWRL 呈现/hasKey 可见/内联 oneOf 不变形/中文 label）
- **路径约定**：脚本调用以 `<skill根>` 指本 skill 根目录（Claude Code 环境=`.claude/skills/ontology-review/`；独立套件=`skills/ontology-review/`）；跨 skill 脚本经相对路径 import，部署时三 skill 保持同级
- 版本历史=`CHANGELOG.md`（执行不依赖）；人类手册=`README.md`

## R0 输入定位

1. 确认 run 目录（ontology-model 8 件套所在）：`ontology.ttl` + `建模方案.md` 两件为最低输入（其余件增强审阅上下文）
2. 敏感级判定（对齐 ontology-model `references/sensitivity-rules.md`）：**真实业务本体（真实载体 run）→ 审阅页只生成到 run 目录内受控区（不进版本控制/不进入对外分发通道），不外发不推送**；虚构载体 run → 可入版本控制目录、可对外
3. 工作目录默认 run 目录旁（产物：review.json / 审阅页.html）

## R1 数据提取（双源）

```bash
python3 <skill根>/scripts/review_extract.py <run目录> [--output review.json] \
    [--term-dict 术语词典.md ...]
```

- TTL 层（权威）：类/对象属性/数据属性（含 oneOf 枚举值）/hasKey/SWRL 规则原子结构/SKOS 概念（definition + comment）
- md 层（专家语言）：建模方案实体表/关系表/公理七族表（约束侧六族+R 推导族）
- **表头跨 run 漂移已归一**：实体表列按关键词认列（`属性/属性标准名`→属性名，`类型/取值`↔`类型取值`→类型，`约束要点`，`消费级`），不写死列名；多余列进 `extras`（如某 run 特有的「硬软分类」列）
- **转义管道**：md 单元格内 `\|`（pattern 正则、枚举值常见）不切列
- **SKOS 定义三源**：TTL `skos:definition` 优先 → 缺则术语词典 md 回填（`--term-dict` 可多次；缺省自动取 run 内 `术语词典*.md`，基线 run 的词典请显式传）→ 仍缺标 `definition_missing`（页面显示「⚠ 词典未定义」，多为结构节点）
- **规则按业务编号分组**：同一规则的编译变体（引用通道 `ruleR1` / 字面量展开通道 `ruleR1c` / 拆分变体 `ruleR15a…`）共享 md 行，逐 TTL imp 出卡会重复——按 md 编号聚合，前端同卡展示并标通道
- **类层级分组**：`class_groups`（按继承根分组 + 组内先序 + depth），供页面分组缩进呈现
- **D2/D4 供给层（schema 1.1）**：`parse_ttl` 唯一新顶层键 `supply`（`build_supply` 纯函数集中图访问）→ merge 分发为 review.json 表面字段（`iri_map`/`literal_meta`/`enum_literals`/`enum_editable`/`parents_guard`/`atom_meta`/`broader_list`/`axiom_graph`/`supply_meta`），供六板块图示与 D4 编辑项编码；`meta.sources.ttl.sha256_full`（64 位）供 D4 基线哈希。**既有输出字节不动**（signature 白名单不取 supply，T4 零漂移）
- 降级纪律：md 解析失败→构件标 `md_missing` 显式报错不静默（TTL 结构仍在）；**衍生类**（规则结论类，如 :ValidApplication）自动识别为 `derived` 不误报缺失；空族（如敏感族设计空置）不报错
- exit 1 = TTL 解析失败（致命，停）；md 告警 = 降级继续（页面会显示 ⚠）

## R2 页面生成

```bash
python3 <skill根>/scripts/build_review_page.py <review.json> [--run-name 场景名]
```

单文件 `审阅页.html`（cytoscape/dagre 内嵌，~0.8-1.2MB）：七区（①类图 ②类与属性 ③关系 ④公理约束六族 ⑤规则双通道 ⑥SKOS 术语 ⑦意见汇总）+ 批注 UI（意见/建议/三级严重度，localStorage 暂存，导出 `审阅意见.json`）。

- **D2 六板块图示**（schema 1.1 供给）：①类继承树（可折叠）/③属性域值域图（含 union 枢纽）/④公理约束图（TTL 构件提取，md 形式化表达 best-effort overlay，md_only 显式）/⑤规则流图（枢纽→body/head atom→变量）/⑥SKOS 层级图（多父）/⑦批注图锚点（跨图定位）；每图配 print 回退边表（信息不丢）。legacy review.json（无 supply）→ 图示降级 hint、D4 禁用
- **D4 编辑模式（L1-L2 TBox）**：header toggle 进入；L1 侧面板改 label/comment/oneOf 受控值，L2 拖节点改 subClassOf 归属、点属性边双下拉改 domain/range；守卫（parents_guard 匿名父不可删/G8 oneOf 重名禁用/target 白名单排除 rule/skos）；编辑产 `d4-patch.json`（`channel=d4`，内容哈希 patch_id）交 R4b 机械执行——**浏览态批注/导出意见零回归**。契约见 `assets/tpl-d4-patch-schema.md`

**呈现纪律**：规范性条款见 `references/presentation-discipline.md`（信息分层/主题归组/记法与交互/plain_swrl() 角色定名算法契约/模板实现硬约束五组 + D2/D4 新条款①b/①c/②c/③c/③d/④b/⑤c/⑥b/⑦d/⑦e；条款编号为全链稳定引用位，self_test E8/E10 按此断言；**通俗翻译零占位符为硬门禁**）。呈现规范的迭代一律在该文件内进行，SKILL.md 只留指针（防堆砌）。

## R3 专家审阅（AG1 停等）

1. 页面交付：单文件本地打开为默认；分发方式由调用环境自定——虚构载体可经任意内部通道分发；**真实业务载体仅本地**（用户自开浏览器，文件不出机器）
2. 专家操作：浏览七区 → 点「批注」记录意见 → 「导出意见 JSON」回传
3. **停等**：等意见 JSON 回收（或专家明确「无意见」）——闸门不代签；首轮审阅同时收集可用性反馈（能否看懂/批注是否顺畅/缺什么）
4. 意见为空也是有效结论（审阅通过）——登记后走 R5 收尾

## R4 意见回流（双通道分流）

```bash
python3 <skill根>/scripts/ingest_opinions.py <审阅意见.json> [--output 审阅意见单.md]
```

severity 分流（契约见 `assets/tpl-opinion-schema.md` §二）：
- **严重（业务错误）→ 入口 (c)**：本轮重编译——把意见单+建议修改连同 29 句集/建模方案交 ontology-generator 修订 → L1-L3 校验 → 审计。**修订后必须重跑 R1-R2 出新审阅页复核**（round-trip 闭环）
- **重要（语义偏差）→ 入口 (c) 或下轮 G1/S2**（按修订成本裁量，呈用户裁定）
- **建议（优化）→ 下轮 G1/S2**：登记待办，下次 run 消费
- 忠实转录纪律：ingest 不改写不概括不合并；敏感内容如实登记由用户裁定脱敏

## R4b D4 patch 机械执行（编排器外接，浏览器不跑 CLI）

D4 编辑导出的 `d4-patch.json` 是与意见单**并行的新产物类型**（不经 ingest_opinions），交 ontology-model R2 增量 patch 引擎机械执行：

```bash
python3 <model skill根>/scripts/incremental_patch.py <run>/ontology.ttl d4-patch.json \
    --golden <run>/golden-cases.json [--with-l3] \
    --output-draft <工作区>/draft.ttl --report <工作区>/patch-report.json
```

- 引擎产 draft（非权威）+ report；D4 抽屉 FileReader 回读 report（verdict/bump/new_errors/regression/zero_writeback）离线检视
- exit 0 released / exit 1 blocked（draft+report 仍产，修复指引）/ exit 2 输入错（sha 错配/裸文本 old，不产 draft）
- 晋升前终检 `--regression-full` → 入口 (c) S4 审计 → G2/G3 → 人工晋升 → 重跑 R1-R2 复核（round-trip）；输出落工作区 cwd 不进 run 目录（R2 零回写）
- **敏感分级**：D4 patch 含字面量值，真实载体 patch 不出本地（同意见 JSON 分级）；编排器序列与守卫详见 `assets/tpl-d4-patch-schema.md`

## R5 收尾登记

run-manifest 追加「审阅轮记录」节：审阅页版本（review.json sha）/专家身份（角色不记真名，敏感纪律）/意见统计（三级计数）/回流通道与处置结论/AG1 状态。收卷前跑 `<skill根>/scripts/self_test.py`（机械回归层 E1-E14；fixture run 经 `--runs` 或环境变量 `ONTOLOGY_SELFTEST_RUNS` 显式传入——虚构示例载体如套件 examples/，真实载体只本地跑）——exit≠0 不得收卷；再跑 ontology-model `closeout_check.py`（若产物入交付物区）。

## 铁律

1. **AG1 停等不代签**——专家结论（含「无意见」）必须真实回收；用户显式授权代跑时登记
2. **意见永不直改 TTL**——一切形式化修改走入口 (c) 管线（专家裁量/LLM 编译/闸门仲裁三层不塌陷）；D4 编辑亦不直改 TTL——产 patch 交 R2 机械执行产 draft（非权威），经入口 (c) 审计+人工闸门晋升
3. **真实本体不出本地**——真实业务载体 run 的审阅页不外发不推送不进版本控制
4. **双源不混权**——TTL 是结构权威（图/枚举/规则原子），md 是专家语言层；两源冲突时以 TTL 为准并在意见单登记提示
5. **导出即基线**——意见 JSON 内嵌本体 sha，回流时先核 sha 一致（基线漂移则提示重审）

## 资产索引

- `references/`：presentation-discipline.md（R2 呈现纪律规范性条款，编号稳定，self_test E8/E10 断言依据；呈现迭代唯一入口）
- `assets/`：review-page-template.html（单文件页模板，七区+六图+批注 UI+D4 编辑）/ tpl-opinion-schema.md（意见契约，schema 1.1+anchor）/ tpl-d4-patch-schema.md（D4 导出契约：patch_id 内容哈希/操作映射/G8+parents_guard 守卫/target 白名单/report 回读/编排器序列/敏感分级）/ vendor-cytoscape.min.js / vendor-dagre.min.js / vendor-cytoscape-dagre.js（内嵌库，cytoscape 3.30.4 MIT）
- `scripts/`：review_extract.py（双源提取+supply 供给层 schema 1.1，exit 0/1/2）/ build_review_page.py（单文件页生成）/ ingest_opinions.py（意见单生成，忠实转录）/ self_test.py（机械回归层 E1-E14，专家实审反馈的回归用例化，E10=通俗翻译零占位符断言/E11-E14=D2/D4 供给与导出契约断言，exit 0/1/2）
- `README.md`（人类手册）/ `CHANGELOG.md`（版本历史，执行不依赖）
- 姊妹 skill：ontology-model（上游产 8 件套+入口 (c) 回流通道）/ ontology-simulate（下游 what-if+A/B）
