# 增量 patch 契约模板（R2 编辑操作 JSON，schema 1.0）

> **用途**：R2 增量 patch 引擎（`scripts/incremental_patch.py`）的输入契约——把「对本体的结构化编辑意图」编码为 patch JSON，引擎机械执行产 **draft TTL + patch-report.json**（不覆盖权威）。本模板是**编排器接口层**：意见→编辑操作的语义翻译由外接编排器（LLM 翻译审阅意见 / D4 拖拽前端 / 手工）承担，R2 只机械执行 + 校验 + 回归守护，不做业务裁量、不含 LLM 调用。
> **前置判据**：简单修改（label/注解/受控值/增删类属性/规则级编辑）走 R2 增量通道，不触发全量重建；**规则编码变更（MAJOR）无回归守护时转入口 (c) 全量审计**——R2 不是绕过闸门的捷径。
> **纪律权威**：意见单 schema（ontology-review `assets/tpl-opinion-schema.md` §四.2）「意见不改本体文件，一切形式化修改走入口 (c)」——R2 产 draft 非权威，晋升仍走入口 (c)，该纪律**零改动**。

---

## 0. 定位与纪律（不可绕过）

| 纪律 | 含义 |
|---|---|
| **draft 非权威** | R2 产 `draft TTL` + `patch-report.json`，report 固定携带 `entry_c:{status:"pending_audit", authoritative:false}`。draft→权威仍走入口 (c) S4 审计→G2/G3→人工晋升，**R2 永不执行晋升**。 |
| **零回写** | baseline TTL + golden JSON + patch 输入三文件 sha256 前后断言；输出 realpath 碰撞守卫（`--output-draft`/`--report` 解析后不得等于任一输入→exit 2）；默认输出落 **cwd**，不进 baseline 所在 run 目录。 |
| **MAJOR 守护硬前提** | 规则编码变更（MAJOR）+ 无 `--golden`→blocked exit 1（转入口 (c)）；MAJOR + 无 Java→blocked；MINOR/PATCH + 无 Java→降级登记凭 L1/L2 放行。 |
| **bnode 不可寻址** | 跨 parse 的 bnode 标签随机（实证 remove no-op），契约**禁 `_:` 项**（exit 2）。SWRL 编辑走规则级 `remove_rule`/`replace_rule`（整片段按硬规范 v2 具名变量），绕开 atom 级 bnode 手术。 |
| **单 parse 工作图** | baseline parse 一次→三元组复制到 draft 图（bnode 对象共享），所有操作在同一工作图解析执行；任一操作失败 abort 不产 draft。 |
| **通用性 + 敏感** | 不耦合任何真实载体；本模板配例全虚构中性（票据贴现域）；skill 资产永不写真实业务数据。 |

## 1. patch JSON 接口（schema 1.0）

```json
{
  "schema_version": "1.0",
  "patch_id": "P-20261117-001",
  "baseline": { "path": "ontology.ttl", "sha256": "<64hex 必填，错配 exit 2>" },
  "source": { "channel": "opinion|d4|manual", "ref": "意见 target / D4 会话 id", "opinion_targets": ["rule:ruleR3"], "author": "可选" },
  "base_version": "1.2.1",
  "bump": "auto|major|minor|patch",
  "notes": "可选",
  "operations": [ /* 非空 */ ]
}
```

| JSON 字段 | 必填 | 说明 |
|---|---|---|
| `schema_version` | ✓ | 固定 `"1.0"` |
| `patch_id` | ✓ | 本次 patch 标识（report/draft 头注释溯源） |
| `baseline.path` | ✓ | 基底本体 TTL 路径（权威，只读） |
| `baseline.sha256` | ✓ | baseline 文件 sha256（64 位十六进制）；**错配 exit 2**（防陈旧 patch——baseline 已变则 patch 失效） |
| `source.channel` | ✓ | `opinion`（审阅意见翻译）/ `d4`（拖拽前端）/ `manual`（手工） |
| `source.ref` / `opinion_targets` / `author` | 可选 | 溯源登记：意见 target（如 `rule:ruleR3`）/ D4 会话 id / 作者 |
| `base_version` | 可选 | 基线版本声明（引擎以 `owl:versionInfo` 实读为准，此字段仅登记） |
| `bump` | 可选 | 缺省 `auto`（引擎检测）；显式 `major/minor/patch` override，低于 auto 检测→report warning（auto 值始终登记） |
| `operations` | ✓ | 非空操作列表，见 §3 |

## 2. 项编码契约（全位置统一）

操作参数中的「项」（s/p/o/target/id/rule/old/new 等）按以下规则解析：

| 形态 | 解析 | 例 |
|---|---|---|
| **JSON 字符串** | 一律 **IRI 引用**（永不解释为字面量） | 全 IRI `http://example.org/bill-discount#Bill` / 前缀名 `rdfs:label` / 裸 localname `Bill`→默认 ns `:Bill` |
| **字面量 dict** | `{"value":..., "lang":...}` 或 `{"value":..., "datatype":...}` | `{"value":"已递交","lang":"zh"}` / `{"value":"100000","datatype":"xsd:integer"}` |
| **JSON number/bool** | 仅 **o 位**允许→xsd 类型字面量 | `100000`→`xsd:integer` / `true`→`xsd:boolean` |
| **`_:` 项** | **一律拒绝**（exit 2） | bnode 跨 parse 不可寻址 |

- 裸 localname 与意见单 id、黄金 expect 记法**同 convention**（默认 ns = baseline `@prefix :` 声明）。
- 前缀名须在 baseline `@prefix` 声明中存在，未知前缀→exit 2。
- `datatype` 值本身按 IRI 解析（`xsd:integer`→XSD.integer）。

## 3. 操作目录（MVP 8 种）

| op | 参数 | 语义/校验 | bump |
|---|---|---|---|
| `add_triple` | s, p, o | 幂等（已存在→noop 登记）；s/p 须 IRI | 按 diff |
| `remove_triple` | s, p, o | 目标必须存在，缺失 exit 2（附 (s,p) 实际宾语助自纠） | 按 diff |
| `replace_literal` | s(可选), p, old, new | s 省略→`(None,p,old)` **全图唯一**匹配，0/多→exit 2（oneOf 枚举改值高频形态，字面量挂 bnode list cell，p 常为 `rdf:first`） | 按 diff（枚举改值=MINOR） |
| `modify_label` | target, label, lang(可选) | 清旧 `rdfs:label` 单值化；lang 缺省继承旧值 | **PATCH** |
| `add_class` | id, label?, comment?, subclass_of? | id 已声明→exit 2；编译为 type/label/comment/subClassOf（subclass_of 可为数组） | **MINOR** |
| `add_property` | id, kind∈{object,datatype}, domain?, range?, label?, comment?, characteristics?[] | 编译为声明三元组；characteristics 如 `owl:FunctionalProperty` | **MINOR** |
| `remove_rule` | rule(IRI) | 必须 `swrl:Imp`；级联删（body/head bnode 链 + 孤儿变量清理） | **MAJOR** |
| `replace_rule` | rule(IRI), ttl(片段) | 片段**禁前缀声明** / 恰 1 `swrl:Imp` 且 IRI 匹配 / **变量全具名**（硬规范 v2 机械检查）；旧级联删 + 新并入 | **MAJOR** |

**SWRL 编辑走规则级**：atom 全是 bnode，atom 级手术不进 MVP。`replace_rule` 由编排器按硬规范 v2（`references/reasoner-limits.md` SWRL 规范节 + `assets/prompt-generator.md`）提供完整 turtle 片段（具名 `swrl:Variable`、单 head），复用 baseline 前缀语境，绕开 bnode 寻址。

## 4. 虚构配例（票据贴现域，全虚构中性）

### 4.1 modify_label（PATCH，annotation-only）

```json
{
  "schema_version": "1.0", "patch_id": "P-demo-label",
  "baseline": { "path": "ontology.ttl", "sha256": "<运行时算>" },
  "source": { "channel": "opinion", "ref": "label:Bill", "opinion_targets": ["label:Bill"] },
  "bump": "auto",
  "operations": [
    { "op": "modify_label", "target": "Bill", "label": "票据（贴现载体）", "lang": "zh" }
  ]
}
```
→ bump=PATCH；regression=skipped(annotation-only)（凭 L1/L2 放行，不付 JVM）；exit 0。

### 4.2 replace_rule（MAJOR，规则级编辑）

```json
{
  "schema_version": "1.0", "patch_id": "P-demo-rule",
  "baseline": { "path": "ontology.ttl", "sha256": "<运行时算>" },
  "source": { "channel": "opinion", "ref": "rule:ruleR3", "opinion_targets": ["rule:ruleR3"] },
  "bump": "auto",
  "operations": [
    { "op": "replace_rule", "rule": "ruleR3",
      "ttl": ":ruleR3 a swrl:Imp ; rdfs:label \"不可贴现判定（修订）\"@zh ; swrl:body ( :atomR3a :atomR3b ) ; swrl:head ( :atomR3h ) . :atomR3a a swrl:IndividualPropertyAtom ; swrl:propertyPredicate :hasAcceptor ; swrl:argument1 :vR3_bill ; swrl:argument2 :vR3_acc . :atomR3b a swrl:IndividualPropertyAtom ; swrl:propertyPredicate :creditRating ; swrl:argument1 :vR3_acc ; swrl:argument2 \"A\" . :atomR3h a swrl:ClassAtom ; swrl:classPredicate :NonDiscountable ; swrl:argument1 :vR3_bill . :vR3_bill a swrl:Variable ; :vR3_acc a swrl:Variable ." }
  ]
}
```
→ bump=MAJOR；**须 `--golden`**（否则 blocked exit 1 转入口 (c)）；变量 `:vR3_bill`/`:vR3_acc` 全具名（硬规范 v2）；片段无 `@prefix`（复用 baseline 前缀）。

> 配例仅为接口演示，规则语义以实际 run 的描述集/词典为准；skill 资产内配例一律虚构。

## 5. exit 三态 + report 概览

| exit | 含义 | 产物 |
|---|---|---|
| **2** | 应用前输入错（schema/sha 错配/parse 失败/项编码错/操作目标缺失/输出碰撞） | **不产 draft**，仅 stderr |
| **0** | released（L1/L2 闸门过 ∧ 回归无检出 ∧ 零回写 ok） | draft + report |
| **1** | blocked（L1/L2 新增 error / 回归检出翻转 / MAJOR 无守护 / L3 不一致 / 零回写失败） | draft + report（blocked draft 供检视/D4 UI 渲染） |

**patch-report.json 块**：`schema_version/patch_id/generated_at/baseline{path,sha256,version}/draft{path,sha256,version}/source/operations[{index,op,status:applied|noop|compiled,source:user|engine,detail}]/diff{added_n,removed_n,added_triples[],removed_triples[],named_summary}/version{base,new,bump_auto,bump_applied,rule_touched,rule_adjacent,reason}/validation{l1_l2{new_errors[],inherited_errors[],resolved_errors[],new_warnings[],gate_pass},l3|null}/regression{verdict,selected[{id,reason}],baseline{...},draft{...},newly_failed[],newly_error[],pass_rate_before/after}/zero_writeback{before/after,assert_ok}/verdict:released|blocked/blocked_reasons[]/entry_c{status:"pending_audit"}/notes[]`。

- diff 三元组经 `to_canonical_graph` 取确定性 cb 哈希标签（跨进程确定，report 无随机 bnode 标签泄漏）。
- regression.verdict ∈ `pass|fail|skipped(annotation-only)|skipped(no-intersection)|skipped(l1l2-blocked)|downgraded|not-requested|blocked`。

## 6. 版本 bump 判据 + 闸门政策

- **版本源** `owl:versionInfo`（单一 Ontology subject）；缺失→0.0.0 起算 + 登记；多值→exit 2 歧义。新版本由引擎生成操作写回 draft versionInfo（report operations 记 `source:"engine"`）。
- **bump 三段**：PATCH=annotation-only（label/comment/注解）；MINOR=结构变更（增删类/属性/受控值；含 rule-adjacent：diff 触及规则引用项但规则编码未动→MINOR + `rule_adjacent:true` + 建议 `--with-l3`）；MAJOR=规则编码变更（双通道检测：①diff p/o 触及 SWRL/SWRLB 词汇或 s 为 swrl:Imp/Variable；②strip_swrl 副本闭包命中——纯原子重排只动 rdf:first/rest，通道①漏检）。
- **L1/L2 delta 闸门**：Validator 双侧 findings 按 (check_id,location,message) 分 new/inherited/resolved；放行=draft parse_ok ∧ **new_errors==0**（baseline 自带 error 登记 inherited 不阻塞，对齐基线迭代细则⑥「零新增 error」）；`--strict` 提供绝对零 error 档。
- **L1/L2 已 blocked→回归短路**（结构非法 draft 的回归无决策价值，省 JVM）。

## 7. 回归子集选择（受影响子集，非全集）

```
full(--regression-full) → 全部非 exempt
annotation-only → []（skipped，凭 L1/L2 放行）
unanchored ∨ diff 触及 owl:imports/Ontology 级公理(除 versionInfo) → 全部非 exempt（global-change）
否则：
  受影响集 = diff URIRef（词汇过滤）+ bnode 反向 BFS 回溯具名 owner（oneOf cell→承载属性）
  保守扩展至不动点 = subClassOf/subPropertyOf 闭包 + equivalentClass/disjointWith/inverseOf 伙伴
                    + domain/range 双向一跳 + 规则引用闭包（union_g=baseline∪draft 覆盖已删边）
  纯全局用例（expect 仅 consistent/inconsistent）恒纳入（global-guard）
  其余 refs(case.ttl URIRef ∪ expect 类/属性裸名展开) ∩ 受影响集 ≠∅ → 纳入
  子集空 → skipped(no-intersection) + warning（L1/L2 已把关）
```
- baseline 回归侧**必须实跑**（不信任冻结 result，可能过期/引擎漂移）；闸门=无 pass→fail 翻转 ∧ draft 无新 error ∧ draft 通过率≥baseline；inherited fail 登记不阻塞；exempt 跳过。
- `--cache-dir`（sha 键 canonical NT 缓存）摊销大本体 canonicalization（~60s×2），缺省无缓存=零副作用。

## 8. 保真边界 + 风险（report 与文档明示）

- **注释丢失**：rdflib 序列化丢失原文件全部注释——draft 是机械中间产物，权威文件注释不动；版本溯源由 draft 头注释 + report 承载；**晋升时历史注释合并是编排器/人工职责**（文本级保注释 patch 否决：Turtle 文本手术脆弱，违机械 backbone 简单性）。
- **保守扩展过选**：MAJOR≈全集（方向敏感扩展=post-MVP）；枚举字面量变更 diff 整 oneOf 子树过报（bnode 链哈希全变，安全侧；named_summary 从操作日志补可读性）。
- **无并发锁**：baseline sha 检陈旧 patch，D4 串行提交。
- **引擎钉住**：rdflib >=7.6,<8（序列化确定性按 7.6 实证，升级须复核）；回归引擎仅 pellet（hermit 对照档 post-MVP）；owl:imports 黄金执行器不联网解析（既有限制，imports 变更强制全集 + 登记）。

## 9. CLI 调用

```bash
python3 <skill根>/scripts/incremental_patch.py <baseline.ttl> <patch.json> \
    [--golden cases.json] [--with-l3] [--output-draft PATH] [--report PATH] \
    [--bump auto|major|minor|patch] [--strict] [--regression-full] [--cache-dir DIR]
# 统一 CLI 门面（套件）：ontology_cli.py model patch <baseline.ttl> <patch.json> [...]
```
`<skill根>`=ontology-model skill 根目录（路径约定见 SKILL.md）。R2 独立可跑，统一 CLI 为薄分发门面（参数转发 + 退出码透传）。