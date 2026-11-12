# ontology-review：本体审阅页与专家意见回流 skill

> 把 ontology-model 产出的 8 件套转成**业务专家（零工程背景）可直接浏览器打开**的单文件审阅页（类图+规则双通道+批注），专家意见导出后机械回流建模管线。
> 当前版本见 SKILL.md frontmatter；版本历史与构建档案见 `CHANGELOG.md`。
> **本文件=人类手册**（三受众拆分：SKILL.md=LLM 执行契约 / README=人类手册 / CHANGELOG=构建档案）。

## 一、解决什么问题

本体建模成果（TTL+建模方案）对业务专家有两道门槛：SWRL 规则读不懂、构件全貌看不到。本 skill 提供：

1. **可读呈现**：七区单文件 HTML（离线、零依赖、中文）——类图/类与属性/关系/公理七族/规则双通道/SKOS 术语/意见汇总；规则三层呈现（业务陈述→通俗逻辑→SWRL 结构折叠）；呈现规范条款见 `references/presentation-discipline.md`
2. **可批注**：任意构件点「批注」记录意见/建议/三级严重度，localStorage 暂存，导出意见 JSON
3. **可回流**：意见单机械生成（忠实转录不概括），按严重度分流回 ontology-model——意见永不直接改 TTL

**审阅与修改分离承载**：专家做批注与业务裁量，形式化修改走 ontology-model 入口 (c) 重编译（在线协作编辑平台有 round-trip 丢构件风险，选型实测见 CHANGELOG）。

## 二、快速上手

```bash
# 1. 双源提取（TTL 结构权威 + 建模方案 md 专家语言层）
python3 <skill根>/scripts/review_extract.py <run目录> [--term-dict 术语词典.md ...]
# 2. 生成单文件审阅页（~0.7-1.1MB，cytoscape/dagre 内嵌）
python3 <skill根>/scripts/build_review_page.py <run目录>/review.json [--run-name 场景名]
# 3. 浏览器打开 审阅页.html → 专家批注 → 导出 审阅意见.json
# 4. 意见回流（生成意见单，供入口 (c) 或下轮 G1/S2 消费）
python3 <skill根>/scripts/ingest_opinions.py <审阅意见.json>
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

**机械回归**：`python3 <skill根>/scripts/self_test.py --runs <fixture run目录>`（E1-E10 确定性断言；fixture 也可经环境变量 `ONTOLOGY_SELFTEST_RUNS` 传入，多目录用系统路径分隔符）。套件环境 fixture=`examples/` 虚构示例载体的建模 run；真实载体只本地跑。exit≠0 不得收卷。

## 五、边界（不做）

- 本体编辑（ontology-model 入口 (c) 管）
- 实例级 what-if 推演（ontology-simulate 管）
- 多人在线协作（单文件+异步意见 JSON 承载）

## 六、目录结构（skill 根）

```
ontology-review/
├── SKILL.md                  # R0-R5 执行契约（LLM 编排入口）
├── README.md                 # 本文件（人类手册）
├── CHANGELOG.md              # 版本历史+构建档案（执行不依赖）
├── references/               # presentation-discipline.md（R2 呈现纪律规范性条款，编号稳定，迭代唯一入口）
├── assets/                   # review-page-template.html（七区+批注 UI 模板）
│                             # / tpl-opinion-schema.md（意见契约）
│                             # / vendor-cytoscape*.js / vendor-dagre*.js（内嵌库，MIT）
│                             # / vendor-LICENSES.md（版本锁定与许可登记，N2）
└── scripts/                  # review_extract.py（双源提取）/ build_review_page.py（页面生成）
                              # / ingest_opinions.py（意见单，忠实转录）/ self_test.py（E1-E10 回归）
```

## 七、姊妹 skill

- **ontology-model**：上游产 8 件套；意见回流目标通道（入口 (c) 重编译 / 下轮 G1/S2）
- **ontology-simulate**：下游 what-if 推演与 A/B 三臂实证（同一冻结基线）

## English Summary

**ontology-review** turns the modeling output (TTL + scheme document) into a single-file, offline, zero-dependency HTML review page that business experts (no engineering background) can open directly in a browser: class graph (cytoscape/dagre, MIT-licensed, embedded with license headers), dual-channel rule presentation (business statement → plain logic → foldable SWRL structure), and a per-construct annotation UI. Expert opinions export as JSON and flow back mechanically into the modeling pipeline (opinion sheet → entry (c) recompilation or the next G1/S2 round) — opinions never edit the TTL directly. Pipeline: `review_extract.py` (dual-source: TTL authoritative + scheme md expert-language layer) → `build_review_page.py` → expert annotation → `ingest_opinions.py`. Mechanical regression: `self_test.py --runs <fixture>` (E1-E10). Third-party library versions and licenses: `assets/vendor-LICENSES.md`. Execution contract: `SKILL.md`.
