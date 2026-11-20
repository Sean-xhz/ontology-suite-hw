# 本体能力套件（Ontology Capability Suite）

> 异构文档进料 → 业务场景自动化本体建模 → 可视化专家审阅 → 模拟验证与 A/B 实证的四件套能力套件。
> 载体中立，适用各行业域（金融、保险、供应链、制造等）。中文 ｜ [English](README.en.md)

## 这是什么

一条**可复现、可校验、可审计**的管线，把自然语言业务知识转化为符合 W3C 语义规范的本体（RDF/OWL/SKOS/SWRL，Turtle 输出），让零工程背景的业务专家可直接审阅，并用实证回答「形式化到底带来多少增量」——而不是依赖 LLM 即兴发挥。

| skill | 定位 | 管线 |
|---|---|---|
| **ontology-ingest** | 异构文档（PDF/图片/Excel/Word/PPT）→ 萃取原料包（清洁保真 MD + canonical manifest + attachments），model S1 的结构化前置进料 | I0-I3：准入与敏感判定 → I1 机械解析（渲染/inventory/substrate，纯 pip 确定性 CLI）→ I2 整页布局感知转录（primary，只读 vision agent）→ I3 机械组装 + 交叉校验 + IG1 轻停等闸门；解析层照录不脱敏（脱敏在 model S1→S2） |
| **ontology-model** | 「7+1」29 句话描述集 → W3C 规范 TTL 本体 | S0-S6 + G1-G3 人工闸门 + 双模型异构质检（generator/auditor 须不同模型）+ L1-L3 机械校验 + 黄金用例业务验收，8 件套交付 |
| **ontology-review** | 建模成果 → 业务专家可读的单文件审阅页（六板块图示 + 规则双通道 + 批注 + L1-L2 拖拽编辑） | 双源提取（TTL 权威 + 建模方案专家语言层 + supply 供给层）→ 离线 cytoscape 单文件 HTML → 专家批注 / D4 编辑产 patch → 意见单机械回流 / patch 交 model R2 引擎执行 |
| **ontology-simulate** | 专家复核过的本体 → what-if 物化推演 + A/B 三臂实证 | 画像 + 诉求 → 合规实例编译（零臆造闸门）→ Pellet 物化（推断层分离 + 规则归因）→ 业务语言解读；A/B：本体臂/描述集臂/裸臂 + 机械判据 + 专家盲评（AG2 终审） |

配套 agents（`agents/`）：ontology-vision-extractor（ingest I2 整页转录，只读）、ontology-generator / ontology-auditor（双模型异构质检）、ontology-whatif-compiler / ontology-whatif-interpreter（模拟编译与解读）、ab-responder（A/B 三臂应答，臂别无关）。脚本层平台无关；agent 层为 Claude Code 参考实现，异构纪律平台中立，其他平台适配见 `agents/README.md`。

## 快速上手

```bash
# 1. 环境引导：检查 python3/pip/Java/node，安装依赖，跑完整验收
bash scripts/bootstrap.sh --run-tests

# 2. 或单独跑验收电池（examples/ 虚构载体为 fixture，零副作用）
python3 scripts/run_suite_tests.py             # T0-T15，exit 0 = 全过
python3 scripts/run_suite_tests.py --skip-java # 无 Java 环境降级档

# 3. 统一 CLI 门面（机械 backbone；LLM 编排外接）
python3 scripts/ontology_cli.py --help         # 能力地图：ingest / model / review / simulate / suite
python3 scripts/ontology_cli.py suite doctor   # 只读环境自检
python3 scripts/ontology_cli.py ingest parse doc.pdf sheet.xlsx --output-dir ./pack
python3 scripts/ontology_cli.py model validate examples/票据贴现/建模run/ontology.ttl
python3 scripts/ontology_cli.py model shapes ontology.ttl --output-shapes shapes.ttl   # R4 TTL→SHACL 派生
python3 scripts/ontology_cli.py model shacl data.ttl shapes.ttl --strict               # R4 实例数据完整性
python3 scripts/ontology_cli.py model queries ontology.ttl --output-json q.json        # D3c TTL→SPARQL 查询模板库

# 4. 浏览器打开示例审阅页（离线、零依赖）
#    examples/票据贴现/建模run/审阅页.html
```

每个 skill 由其 `SKILL.md` 执行契约驱动（LLM 编排入口），`README.md` 为人类手册；可迭代领域规范在各 skill `references/`（条款编号稳定，迭代在 reference 内发生）；`CHANGELOG.md` 为版本历史。Claude Code 触发：`/ontology-ingest`、`/ontology-model`、`/ontology-review`、`/ontology-simulate`。独立部署：四 skill 保持同级（跨 skill 相对 import），`ONTOLOGY_RUNS_ROOT` 指向 run 目录。

## 统一 CLI 入口

`scripts/ontology_cli.py` 把四件套的**确定性机械脚本**聚合为统一命令面。LLM 编排层（I0-I3 / S0-S6 管线、IG1 / G1-G3 / SG1-SG2 / AG1-AG2 人工闸门、双模型生成-审计、vision 转录）**不在 CLI 内**，由外部编排器承担；CLI 只暴露可独立运行的机械能力。

```bash
python3 scripts/ontology_cli.py <group> <action> [args...]
```

| group | action | 底层能力 |
|---|---|---|
| **ingest** | `parse` | I1 异构文档机械解析→萃取原料包（纯 pip，识图由 vision agent 外接） |
| **model** | `validate` / `consistency` / `topology` / `golden` / `patch` / `shapes` / `shacl` / `queries` | L1+L2 校验 / L3 一致性 / S5 文本拓扑 / S6 黄金用例 / R2 增量 patch / R4 TTL→SHACL 派生 / R4 实例数据完整性 / D3c TTL→SPARQL Read 查询模板库 |
| **review** | `extract` / `page` / `ingest` / `selftest` | 双源提取 + supply / 单文件审阅页 / 意见单回流 / E1-E14 自测 |
| **simulate** | `signature` / `check` / `reason` / `ab-score` | 编译签名 / 实例零臆造校验 / what-if 物化 / A/B 判据评分 |
| **suite** | `test` / `doctor` | 统一验收电池 T0-T15 / 只读环境自检 |

**薄分发纪律**：每个子命令把剩余参数原样转发底层脚本（subprocess），退出码透传，脚本行为零改变——各脚本仍可独立运行，CLI 只是便利门面。脚本路径相对套件根（`__file__` 自动定位，与 cwd 无关）；跨 skill import 由各脚本自身的相对 `sys.path` 垫片承接。未知 group/action 或脚本缺失 = exit 2。

## 目录导览

```text
本体能力套件/
├── skills/            # 四 skill（SKILL.md 执行契约 + README 人类手册 + CHANGELOG 版本历史 + assets/references/scripts）
├── agents/            # 六 agent 定义 + README（角色一览/异构纪律/平台适配，双语）
├── examples/票据贴现/  # 全虚构示例载体（可对外）：建模 run + 审阅与意见 + 模拟 demo
├── scripts/           # ontology_cli.py（统一 CLI）+ bootstrap.sh（环境引导）+ run_suite_tests.py（统一验收入口）
├── requirements.txt   # Python 依赖（精确钉住实证版本）
├── docs/              # GitHub Pages 站点（index.html 门面 + demo.html 审阅页在线预览）
├── .github/workflows/ # CI 矩阵（tests.yml）+ Pages 部署（pages.yml）
├── LICENSE            # MIT（主许可）
├── THIRD-PARTY-LICENSES.md  # 第三方许可汇总（捆绑 JS 三库 + pip 依赖注记 + 方法论致谢）
├── README.md          # 本文件（中文）
└── README.en.md       # 英文门面
```

## 环境依赖

- **python3（≥3.9）** + `rdflib` + `owlready2` + `pyshacl` + 解析六库 `pypdf`/`pypdfium2`/`python-docx`/`openpyxl`/`python-pptx`/`Pillow`（见 `requirements.txt`，精确钉住——输出字节稳定性版本敏感，升级须重跑双跑确定性）。一键引导=`bash scripts/bootstrap.sh`。
  - **owlready2==0.51**（引擎行为按该版本登记）；**pyshacl==0.29.1**（R4 SHACL 层，纯 Python 无 Java，与 Java 推理机两条正交环境轴）。
  - **pypdfium2 安装须 `--only-binary=:all:`**（wheel 自带 pdfium 二进制，避旧 pip 选 sdist 触发下载超时）。
  - **LibreOffice 可选**（office→PDF 全视觉渲染增强，MPL-2.0 独立子进程不感染 MIT；无则 office 退 substrate-only 纯 pip 主路径仍工作）。
  - **解析库可选性**：缺库时 `ingest parse` 降级 exit2+pip 提示，不阻塞 model/review/simulate（doctor 可选 WARN 档）。fitz/PyMuPDF 零代码路径（AGPL 不引入），pypdf[crypto]（AES）可选 extra 默认未装。
- **Java** + Pellet/HermiT 推理机 jar（L3 一致性与 SWRL 物化；**Pellet 需 Java ≥25**、HermiT ≥17；jar 随 owlready2 pip 包内置）。无 Java 时降级 L2 并登记，不阻塞交付；R4 SHACL 与 D3c SPARQL 纯 Python 无 Java 也可跑。引擎版本/限制/降级链见 `skills/ontology-model/references/reasoner-limits.md`。
- **node**（可选，仅 review `self_test.py` 模板 JS 语法检查项，缺失降级 skip）。
- **CI**：`.github/workflows/tests.yml`（python 3.9/3.12 矩阵 × temurin Java 25 × node 20，消费统一验收入口）。

## 验收电池

`python3 scripts/run_suite_tests.py`（T0-T15 编排，examples 虚构载体为 fixture，一切输出落临时目录零副作用，`--skip-java` 降级档；exit 0/1/2）。CI 消费同一入口。

| # | 项 | 覆盖 |
|---|---|---|
| T0 | py_compile | 全部脚本语法 |
| T1 | review `self_test.py` | E1-E14（E11-E14=D2/D4 供给与导出契约）；`--runs` 显式传入，无参/坏目录 exit 2 |
| T2 | `run_golden_cases.py --check` | 黄金用例 schema |
| T3 | `validate_ontology.py` | L1+L2 结构校验 |
| T4 | `extract_signature.py` vs 冻结 signature | 全量 JSON 相等 + 双跑字节确定性 |
| T5/T6 | `check_instance.py` 正例/反例 | exit 0 / exit 1 拦截 |
| T7 | 跨 skill import | 套件内相对 import 解析 |
| T8 | `simulate_reason.py` 物化实跑（Pellet） | 推断三元组 + 规则归因 + 零回写断言 |
| T9 | `closeout_check.py` | 收卷齐套 + 敏感扫描 |
| T10 | 品牌名 grep 契约 | 虚构载体 0 命中 |
| T11 | `incremental_patch.py`（R2） | 注解/结构正例、L2 反例、回归翻转、MAJOR 守护政策、sha 错配、双跑确定性 |
| T12 | `derive_shacl.py`+`validate_shacl.py`（R4） | 派生确定性 + 计数锚、conform 正例、facet/基数/枚举/hasKey 反例、check_instance 互补对偶、契约错 |
| T13 | D2/D4 审阅页端到端 | supply→产页 token、五类 patch→R2 引擎、sha12/裸文本反例、回归翻转 G1、内容哈希 patch_id 双跑、merge+supply 隔离 |
| T14 | `parse_documents.py`（ingest I1） | 四文本格式 schema + substrate/rendered、图片直供、契约错、扫描页整页渲染、双跑字节等、零回写、边界矩阵、清洁 md、inventory ground truth、接缝 affordance 准备态 |
| T15 | `derive_sparql.py`（D3c） | 派生双跑字节等 + 计数锚、prepareQuery 语法 valid、graph.query 执行正例、derived 分流、参数化零泄漏 + IRI 守卫、契约错、零回写（纯 rdflib 内置 SPARQL 1.1，无 Java） |

## 许可与致谢

- **主许可=MIT**（`LICENSE`）。
- **第三方许可**：`THIRD-PARTY-LICENSES.md`（捆绑 JS 三库 cytoscape/dagre/cytoscape-dagre MIT 全文，许可头随单文件 HTML 分发旅行 + pip 依赖许可注记 + 方法论来源致谢）；skill 级版本锁定登记=`skills/ontology-review/assets/vendor-LICENSES.md`。
- **方法论来源**：建模方法论内核（`skills/ontology-model/references/methodology-core.md`）源自《本体驱动的AI数据管理》（*Ontology-Driven AI Data Management*，编写组著）公开方法论，经蒸馏重编译为自包含执行判据。套件不复制原书文本。

## 敏感纪律（红线）

1. `examples/` 只放**全虚构**载体（票据贴现）；真实业务载体 run 的任何产物**永不入套件**、永不外发。
2. skill/agent 资产永不写真实业务数据与人名；模板配例一律虚构中性。
3. 套件不含任何 API 凭据；对外发布前须再过一遍 `closeout_check.py` 敏感扫描。
4. **D4 patch 含字面量值**——真实载体编辑导出的 `d4-patch.json` 不出本地（同意见 JSON 分级）；对外分发产物一律虚构。

## 已知问题与待迭代

- **ab_score enum_values 键名不一致（登记不修）**：`ontology-simulate/scripts/ab_score.py` 读 `enum_values` 键，而 `extract_signature` 提取键为 `oneOf_enum`→A/B 机械判据的受控值词汇表恒空。正确修法=改 ab_score 一行（simulate 独立 PATCH）；**切勿改 `oneOf_enum` 迁就它**——会破冻结签名（T4）+ check_instance E07 消费。
- **D4 handle 节点拖拽重连（post-MVP）**：cytoscape 3.30 核心无边端点重连 API，当前采用无障碍回退双下拉路径（点属性边→侧面板 domain/range 双下拉，同语义同 ops）；handle 方块拖拽重连留后续迭代。
- **D4 编辑级别边界**：当前仅 L1-L2 TBox（label/comment/oneOf 受控值/subClassOf 归属/domain/range）；ABox 实例值编辑 + L3 规则编辑 defer 后续。
- **D4 离线闭环交互断档（待排期）**：当前路径下产 `patch-report.json` 须跳出审阅页跑一条 R2 CLI 命令——真实场景专家只有页面、无命令运行环境。后续改为浏览器内执行 CLI（pyodide/WASM 内嵌纯 rdflib R2 核心，页内产 draft+report，专家全程不离页；L3/golden 回归需 Java 仍外接或降级），与单文件零依赖铁律的张力届时权衡。回读区已加文件类型守卫：误选导出补丁 `d4-patch.json` 不再静默 `?`，改为「这是补丁不是报告」提示 + 操作预览 + 产报告 CLI 指引。
- **大图性能（post-MVP）**：六 cytoscape 实例在虚构 fixture 无压力；真实大本体可选 nav 懒初始化，登记不阻塞。
- **ingest 完整四通道**：talk ASR / code SQL DDL / diagram / 专有 DB 连接器为后续扩展位（见 `skills/ontology-ingest/references/parsing-limits.md`，无排期承诺）；SPARQL C/U/D（UPDATE）留后续实例化管道。
