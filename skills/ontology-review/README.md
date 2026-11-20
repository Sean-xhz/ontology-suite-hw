# ontology-review：本体审阅页与专家意见回流 skill

> 把 ontology-model 产出的 8 件套转成**业务专家（零工程背景）可直接浏览器打开**的单文件审阅页（六板块图示+规则双通道+批注+L1-L2 拖拽编辑），专家意见导出后机械回流建模管线；D4 编辑产 patch 交 ontology-model R2 机械执行。
> 当前版本见 SKILL.md frontmatter；版本历史见 `CHANGELOG.md`。
> **本文件=人类手册**（三受众拆分：SKILL.md=LLM 执行契约 / README=人类手册 / CHANGELOG=版本历史）。

## 一、解决什么问题

本体建模成果（TTL+建模方案）对业务专家有两道门槛：SWRL 规则读不懂、构件全貌看不到。本 skill 提供：

1. **可读呈现**：七区单文件 HTML（离线、零依赖、中文）——类图/类与属性/关系/公理约束六族/规则双通道/SKOS 术语/意见汇总；规则三层呈现（业务陈述→通俗逻辑→SWRL 结构折叠）；呈现规范条款见 `references/presentation-discipline.md`
2. **六板块图示（D2）**：类继承树（可折叠）/属性域值域图（含 union 枢纽）/公理约束图（TTL 构件提取+md 形式化表达 overlay）/规则流图（枢纽→body/head 原子→变量）/SKOS 层级图（多父）/批注跨图锚点定位——业务专家不必在表格间人脑拼接逻辑链；每图配 print 回退边表（打印信息不丢）
3. **可批注**：任意构件点「批注」记录意见/建议/三级严重度，localStorage 暂存，导出意见 JSON
4. **可轻量编辑（D4，L1-L2 TBox）**：编辑模式下改 label/comment/oneOf 受控值（L1 侧面板）、拖节点改 subClassOf 归属、点属性边双下拉改 domain/range（L2）；守卫（匿名父不可删/oneOf 重名禁用/规则与 SKOS 不可编辑）；编辑产 `d4-patch.json` 交 ontology-model R2 引擎机械执行产 draft（非权威）+ report，抽屉离线回读检视——**不直改 TTL**，晋升仍走入口 (c) 审计+人工闸门
5. **可回流**：意见单机械生成（忠实转录不概括），按严重度分流回 ontology-model——意见永不直接改 TTL

**审阅与修改分离承载**：专家做批注与业务裁量，形式化修改走 ontology-model 入口 (c) 重编译（在线协作编辑平台有 round-trip 丢构件风险）。D4 是分离承载下的**轻量形式化补充**——专家可在页面直接做 L1-L2 小改并产 patch，但 patch 仍经 R2 机械执行+入口 (c) 审计晋升，「意见/编辑不直改本体」纪律不变。ABox 实例值编辑与 L3 规则编辑 延后。

## 二、快速上手

```bash
# 1. 双源提取（TTL 结构权威 + 建模方案 md 专家语言层）
python3 <skill根>/scripts/review_extract.py <run目录> [--term-dict 术语词典.md ...]
# 2. 生成单文件审阅页（~0.7-1.1MB，cytoscape/dagre 内嵌）
python3 <skill根>/scripts/build_review_page.py <run目录>/review.json [--run-name 场景名]
# 3. 浏览器打开 审阅页.html → 专家批注 → 导出 审阅意见.json
# 4. 意见回流（生成意见单，供入口 (c) 或下轮 G1/S2 消费）
python3 <skill根>/scripts/ingest_opinions.py <审阅意见.json>
# 5.（可选 D4）专家编辑模式 → 导出 d4-patch.json → 交 model R2 机械执行（浏览器不跑 CLI）
python3 <model skill根>/scripts/incremental_patch.py <run>/ontology.ttl d4-patch.json \
    --golden <run>/golden-cases.json --output-draft <工作区>/draft.ttl --report <工作区>/patch-report.json
#    → 抽屉回读 report 检视 → 晋升前 --regression-full 终检 → 入口 (c) S4 审计 → 人工晋升 → 重跑 1-2 复核
```

`<skill根>`=本 skill 根目录（Claude Code 环境=`.claude/skills/ontology-review/`；独立套件=`skills/ontology-review/`）。最低输入=`ontology.ttl`+`建模方案.md` 两件；术语词典可显式传入回填 SKOS 定义。

**意见分流**（severity 三级）：严重（业务错误）→入口 (c) 本轮重编译，修订后必须重出审阅页复核（round-trip 闭环）；重要（语义偏差）→入口 (c) 或下轮 G1/S2（呈用户裁定）；建议（优化）→下轮 G1/S2 登记待办。

## 三、专家审阅闸门（AG1）

- 页面交付后**停等**专家意见 JSON 回收（或明确「无意见」）——闸门不代签；意见为空也是有效结论（审阅通过）
- 首轮审阅同时收集可用性反馈（能否看懂/批注是否顺畅/缺什么）
- 意见 JSON 内嵌本体 sha——回流时先核 sha 一致，基线漂移则提示重审（导出即基线）

## 四、环境与目录约定

**依赖**：python3（3.9+）+ rdflib；node 可选（仅 self_test E9 模板 JS 语法检查项，缺失降级 skip 并登记）。

**敏感纪律**（对齐 ontology-model `references/sensitivity-rules.md`）：

| 载体 | 审阅页落位 | 分发 |
|---|---|---|
| 真实业务本体 | 只生成到 run 目录内**受控区**（不进版本控制/不进入对外分发通道） | **仅本地**（用户自开浏览器，文件不出机器） |
| 虚构载体 | 可入版本控制目录 | 可经任意内部通道分发 |

受控区=不进版本控制的目录（如版本控制忽略区）；工作目录默认 run 目录旁。

**机械回归**：`python3 <skill根>/scripts/self_test.py --runs <fixture run目录>`（E1-E14 确定性断言，E11-E14=D2/D4 供给与导出契约；fixture 也可经环境变量 `ONTOLOGY_SELFTEST_RUNS` 传入，多目录用系统路径分隔符）。套件环境 fixture=`examples/` 虚构示例载体的建模 run；真实载体只本地跑。exit≠0 不得收卷。D4 patch→引擎端到端验收见套件 `scripts/run_suite_tests.py` T13（6 子例）。

## 五、边界（不做）

- 本体编辑的**权威晋升**（ontology-model 入口 (c) 管）——D4 仅产 patch+draft（非权威），不直改 TTL
- ABox 实例值编辑、L3 规则编辑（atom→整条规则 turtle 重翻译，MAJOR）——延后
- 实例级 what-if 推演（ontology-simulate 管）
- 多人在线协作（单文件+异步意见 JSON 承载）
- 浏览器内实时校验（D4 路径甲：提交时交 R2 CLI 机械校验，保零依赖离线铁律，禁 pyodide/WASM/CDN）

## 六、目录结构（skill 根）

```
ontology-review/
├── SKILL.md                  # R0-R5 执行契约（LLM 编排入口）
├── README.md                 # 本文件（人类手册）
├── CHANGELOG.md              # 版本历史（执行不依赖）
├── references/               # presentation-discipline.md（R2 呈现纪律规范性条款，编号稳定，迭代唯一入口）
├── assets/                   # review-page-template.html（七区+六图+批注 UI+D4 编辑模板）
│                             # / tpl-opinion-schema.md（意见契约，schema 1.1+anchor）
│                             # / tpl-d4-patch-schema.md（D4 导出契约：操作映射/守卫/编排器序列/敏感分级）
│                             # / vendor-cytoscape*.js / vendor-dagre*.js（内嵌库，MIT）
│                             # / vendor-LICENSES.md（版本锁定与许可登记）
└── scripts/                  # review_extract.py（双源提取+supply 供给层）/ build_review_page.py（页面生成）
                              # / ingest_opinions.py（意见单，忠实转录）/ self_test.py（E1-E14 回归）
```

## 七、姊妹 skill

- **ontology-model**：上游产 8 件套；意见回流目标通道（入口 (c) 重编译 / 下轮 G1/S2）
- **ontology-simulate**：下游 what-if 推演与 A/B 三臂实证（同一冻结基线）

## English Summary

**ontology-review** turns the modeling output (TTL + scheme document) into a single-file, offline, zero-dependency HTML review page that business experts (no engineering background) can open directly in a browser: six graph panels (class hierarchy tree, property domain/range graph with union hubs, axiom constraint graph, rule flow graph, SKOS concept hierarchy, cross-graph annotation anchors; cytoscape/dagre, MIT-licensed, embedded with license headers), dual-channel rule presentation (business statement → plain logic → foldable SWRL structure), and a per-construct annotation UI. Expert opinions export as JSON and flow back mechanically into the modeling pipeline (opinion sheet → entry (c) recompilation or the next G1/S2 round) — opinions never edit the TTL directly. A D4 edit mode (L1-L2 TBox: label/comment/controlled-value edits, subClassOf re-parenting by node drag, domain/range via edge dropdowns) exports a `d4-patch.json` consumed by ontology-model's R2 incremental patch engine (draft + report, never authoritative; promotion still goes through entry (c) audit + human gates). Pipeline: `review_extract.py` (dual-source + supply layer, schema 1.1) → `build_review_page.py` → expert annotation/edit → `ingest_opinions.py` / R2 patch. Mechanical regression: `self_test.py --runs <fixture>` (E1-E14); end-to-end D4 patch→engine in suite `run_suite_tests.py` T13. Third-party library versions and licenses: `assets/vendor-LICENSES.md`. Execution contract: `SKILL.md`.
