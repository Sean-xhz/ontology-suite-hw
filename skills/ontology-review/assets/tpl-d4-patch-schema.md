# D4 拖拽编辑导出契约（审阅页前端 → R2 patch JSON，channel=d4）

> **用途**：ontology-review 审阅页 D4 拖拽编辑（L1-L2 TBox）的**前端导出契约**——把专家在页面上的轻量形式化编辑（改 label/comment/受控值/继承归属/属性域值域）确定性映射为 R2 增量 patch JSON（`source.channel="d4"`），交外接编排器跑 R2 CLI 机械执行。本契约是 ontology-model `assets/tpl-patch-schema.md`（R2 引擎输入契约，schema 1.0）**编排器接口层的 D4 具体实现**：R2 引擎零改动，本文件只定义前端→patch 的映射、守卫、导出/回读纪律。
> **路径甲**：前端产 patch JSON → 编排器跑 R2 CLI 校验 + L1/L2 闸门 + 回归守护 → draft 非权威 + report → 入口 (c) S4 晋升。**浏览器不跑 CLI**（G6，保单文件 HTML 零依赖离线铁律，禁 pyodide/WASM/CDN）；实时性=提交时 CLI 校验，非浏览器秒级预检。
> **纪律权威**：意见单 schema（`tpl-opinion-schema.md` §四.2）「意见不改本体文件，一切形式化修改走入口 (c)」——D4 patch 与意见单是**并行的两类产物**（意见=语义批注走 ingest_opinions；D4 patch=结构化编辑意图走 R2），draft→权威仍走入口 (c)，该纪律**零改动**。呈现条款见 `references/presentation-discipline.md` ②c/①c/③d/⑦e。

---

## 0. 定位与边界（不可绕过）

| 纪律 | 含义 |
|---|---|
| **L1-L2 TBox only** | L1=侧面板改 label/comment/oneOf 受控值；L2=拖节点改 subClassOf 归属、拖边改 objectProperty domain/range。**ABox 实例值编辑 + L3 规则编辑（atom→整条规则 turtle 重翻译，MAJOR）延后**——本页不产 remove_rule/replace_rule/add_class/add_property。 |
| **target 白名单** | 编辑目标限 `class` / `object_property` / `data_property`。**硬禁 rule / skos**——MAJOR 陷阱：rule 目标 label 编辑→diff s=swrl:Imp→`rule_touched=true`→MAJOR 须 golden 守护，L1 轻量编辑不得触发（实证背书）。 |
| **draft 非权威** | D4 只产 patch JSON（编辑意图），不产 TTL。R2 产 draft + report，report 固定 `entry_c:{status:"pending_audit",authoritative:false}`。晋升走入口 (c) S4 审计→G2/G3→人工，**D4/R2 永不执行晋升**。 |
| **浏览态零回归** | D4 编辑模式是 header toggle 叠加层；关闭态批注/导出意见行为与 1.2.x 完全一致。D4 草稿态独立 localStorage（`STORE_KEY+"-d4"`），旧意见数据零碰撞。 |
| **legacy 降级** | review.json `schema_version<1.1`（无 supply）→ D4 编辑模式禁用 + 显式「数据层未升级，请重跑 review extract」hint；D2 各图同口径 hint，不静默空图。 |
| **通用性 + 敏感** | 不耦合任何真实载体；本契约配例全虚构中性（票据贴现域）；skill 资产永不写真实业务数据。**D4 patch JSON 含字面量值→真实载体 patch 不出本地**（同意见 JSON 分级，R0 敏感判定延伸，见 §8）。 |

## 1. D4 草稿态（localStorage）

键 = `STORE_KEY + "-d4"`（STORE_KEY 同意见单，按 run 隔离）。值：

```json
{
  "session_id": "d4-<run>-<base_sha12>-<nonce>",
  "base_sha256_full": "<64hex，= review.json meta.sources.ttl.sha256_full>",
  "base_version": "<supply_meta.ontology_version>",
  "edits": [
    { "edit_id": "e1", "kind": "label|comment|enum|subclass|domain|range",
      "target_kind": "class|object_property|data_property",
      "target_id": "<localname>", "target_iri": "<全 IRI>",
      "before": "<旧值/旧项编码>", "after": "<新值/新项编码>",
      "ts": "<ISO>", "ts_local": "<北京时间>",
      "status": "staged|exported" }
  ]
}
```

- `session_id` 含 base_sha12：基线刷新（重跑 extract）→ sha 变 → 旧会话 edits 失效（防陈旧 patch，铁律 5）。
- `status`：`staged`=待导出（可撤销）；`exported`=已导出锁定（不可再改，须新会话）。
- **串行纪律**：一次只一个待导出 patch；export 后全部 staged→exported 锁定；基线刷新后开新会话。sha 错配→引擎 exit 2→前端提示「基线已变，请重跑 extract 刷新页面后重新编辑」。

## 2. patch JSON 组装（⑦e，复用 export Blob 先例）

```json
{
  "schema_version": "1.0",
  "patch_id": "P-d4-<内容哈希12hex>",
  "baseline": { "path": "ontology.ttl", "sha256": "<base_sha256_full 64hex>" },
  "source": { "channel": "d4", "ref": "<session_id>" },
  "base_version": "<supply_meta.ontology_version>",
  "bump": "auto",
  "operations": [ /* 由 staged edits 确定性映射，见 §3 */ ]
}
```

| 字段 | D4 取值 | 引擎对齐 |
|---|---|---|
| `schema_version` | 固定 `"1.0"` | R2 schema 1.0 不变 |
| `patch_id` | **内容哈希**（§2.1） | 同编辑→同 id→draft 双跑字节等（T11f 教训：缺省 P-adhoc 含时间戳破确定性） |
| `baseline.sha256` | `base_sha256_full`（**64hex**，G1） | validate_patch fullmatch 64 位小写 hex；12 位截断→exit 2 |
| `source.channel` | 固定 `"d4"` | R2 已预留 d4 通道（tpl-patch-schema §1 L41） |
| `source.ref` | `session_id` | 溯源登记 |
| `base_version` | `supply_meta.ontology_version` | 引擎以 owl:versionInfo 实读为准，此字段仅登记 |
| `bump` | 固定 `"auto"` | 引擎检测（label/comment=PATCH；enum/subclass/domain/range=MINOR） |

### 2.1 patch_id 内容哈希（确定性，跨语言可复刻）

```
canonical = canonicalJSON({ "baseline": base_sha256_full, "operations": operations })
patch_id  = "P-d4-" + SHA256(UTF8(canonical))[0:12]
```

- **canonicalJSON**：递归排序对象键（数组保序），紧凑序列化（无空白），字符串 JSON 转义，Unicode 字面量（ensure_ascii=False）。等价 Python `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',',':'))`。
- **SHA256**：前端内置紧凑同步 SHA-256 实现（纯 JS，零依赖，避 Web Crypto secure-context 不确定性）；E14 用 Python hashlib 复刻断言双建字节等。
- operations 按 staged 顺序映射（§3）；同编辑集 + 同顺序→同 canonical→同 patch_id→draft 头注释稳定→双跑字节等。

## 3. 操作映射表（L1-L2 五类，全部内存实证 exit 0）

> 项编码遵循 R2 §2：**JSON 字符串恒 IRI**（D4 一律产**全 IRI** `startswith base_ns`，G3——不用裸 localname/前缀名，避默认 ns 歧义）；**字面量=dict** `{value,lang|datatype}`（G2——old 全等编码取 `literal_meta`/`enum_literals` 精确 lang/datatype，裸文本对 @zh 字面量 0 匹配→exit 2）。`_:` 项一律禁（R2 exit 2）。

| 编辑 | kind | 映射操作 | bump | 守卫 |
|---|---|---|---|---|
| **改 label** | label | `modify_label{target:<全IRI>, label:<新值>}`（lang 省略，引擎继承旧 @zh） | PATCH annotation-only | target 白名单 |
| **改 comment（已存在）** | comment | `replace_literal{s:<全IRI>, p:"rdfs:comment", old:<dict全等>, new:<dict>}` | PATCH | before 取 literal_meta 精确 {value,lang,datatype} |
| **加 comment（缺失）** | comment | `add_triple{s:<全IRI>, p:"rdfs:comment", o:{value:<新值>}}` | PATCH | literal_meta.comment==None→add 路径 |
| **改 oneOf 受控值** | enum | `replace_literal{p:"rdf:first", old:<dict全等>, new:<dict>}`（**s 省略**，全图唯一匹配） | MINOR | **G8**：enum_editable.editable=false→禁用（§4） |
| **改继承（reparent）** | subclass | `remove_triple{s:<child全IRI>, p:"rdfs:subClassOf", o:<旧父全IRI>}` + `add_triple{s:<child全IRI>, p:"rdfs:subClassOf", o:<新父全IRI>}` | MINOR | **parents_guard**（§5） |
| **根类加父** | subclass | `add_triple{s:<child全IRI>, p:"rdfs:subClassOf", o:<新父全IRI>}`（add-only） | MINOR | parents_guard：0 具名父 |
| **改 domain/range** | domain/range | `remove_triple{s:<prop全IRI>, p:"rdfs:domain"\|"rdfs:range", o:<旧类全IRI>}` + `add_triple{s:<prop全IRI>, p:同上, o:<新类全IRI>}` | MINOR | 仅具名 domain+range 边；union 边禁用（§5） |

- **enum s 省略原理**：oneOf 枚举字面量挂 bnode list cell（`rdf:first`），bnode 不可寻址（R2 §0）；`replace_literal` s 省略→`(None,rdf:first,old)` 全图唯一匹配（G8 预检保唯一，0/多→exit 2）。
- **subclass/domain/range 用 remove+add 对**：R2 无「改宾语」原子操作，remove 旧三元组 + add 新三元组等价改归属/域值域；remove 目标必须存在（缺失 exit 2），before 取 supply 精确旧项。
- **不产 add_class/add_property/remove_rule/replace_rule**：超出 L1-L2 TBox scope（延后）。

## 4. G8 守卫：oneOf 重名预检（enum_editable）

`supply.enum_editable[prop_id] = [{value, editable, reason}]`（与 oneOf_enum 同序）：

- **预检算法**（build_supply）：全图 `(None, rdf:first, Literal(v))` 计数 + 跨属性重名索引。某枚举值 v 在全图 rdf:first 位置出现 >1 次（跨属性重名或同属性重复）→ `editable=false, reason="重名不可消歧（全图 N 处），转入口 (c)"`。
- **前端**：`editable=false` 的 chip 灰显 + tooltip reason + 禁点；专家须改该值→走入口 (c) 意见通道（R2 s 省略匹配会 0/多→exit 2，前端预检拦截避无效提交）。
- **fixture 实证**：票据贴现 8 枚举值全唯一→全 editable=true；E14 合成重名注入→禁用断言。

## 5. parents_guard + union 守卫（L2 拖拽）

### 5.1 parents_guard（subclass 拖节点，①c）

`supply.class_parents[class_id] = {named:[localname…], anon:int}`（具名父列表 + 匿名父计数）：

| 父形态 | 拖拽行为 | 映射 |
|---|---|---|
| 恰 1 具名父 + 0 匿名父 | **reparent**（可拖） | remove 旧父 + add 新父 |
| 0 具名父（根类） | **add-only 加父**（可拖） | add 新父（不 remove） |
| >1 具名父 | **禁用**转入口 (c) | 多父删哪条歧义，R2 不可裁量 |
| 匿名父>0 且涉删 | **禁用**转入口 (c) | G4：匿名 Restriction 表达式 R2 不可寻址（`_:` 禁） |

- **环检查**（前端 stage 前）：新父祖先闭包不含自身、新父≠自身、双方具名类。违→拒 stage + 提示。
- **fixture 实证**：Bill 匿名父 2（someValuesFrom hasAcceptor / maxQualifiedCardinality）→不可 reparent；Discountable/NonDiscountable 恰 1 具名父 Bill→可 reparent；根类 Bill/Holder/Acceptor…0 具名父→add-only 安全。

### 5.2 union 守卫（domain/range 拖边，③d）

- 仅**具名 domain+range** 的 `e-op-*` 边可编辑（parse_ttl domain/range 具名守卫已在位）。
- **union 边**（domain_union/range_union 匿名值域）→ handle 禁用 + tooltip「匿名值域转入口 (c)」（G4 同口径）。
- cytoscape 3.30 核心无边端点重连→编辑态 tap 边生成 2 临时 handle 节点（grabbable 方块 + 虚线临时边），dragfree 命中类节点→确认弹窗→stage；**无障碍回退**：tap 边→侧面板 domain/range 双下拉（同语义同 ops）。

## 6. report 回读（离线闭环，⑦e）

D4 抽屉 `<input type="file">` FileReader 读编排器产出的 `patch-report.json`→渲染：

| report 块 | UI 呈现 |
|---|---|
| `verdict` | released（绿）/ blocked（红） banner |
| `version{base,new,bump_applied,rule_touched}` | 版本 bump 徽标（PATCH/MINOR/MAJOR） |
| `diff.named_summary` + `added_n/removed_n` | 变更可读摘要（专家语言） |
| `blocked_reasons[]` | **blocked draft UI**（exit 1 仍产 report，tpl-patch-schema §5 L118）→逐条修复指引 + 入口 (c) 提示 |
| `validation.l1_l2.new_errors[]` | L1/L2 新增 error 清单（结构非法→修编辑） |
| `regression.verdict` + `newly_failed[]` | 回归翻转检出（pass→fail 用例→业务语义须复核） |
| `zero_writeback.assert_ok` | 零回写断言状态 |
| `entry_c.status` | 「待入口 (c) 审计」常驻提示（draft 非权威） |

- **exit 三态对齐**（R2 §5）：exit 2（输入错，不产 draft）→前端提示修 patch（sha 错配/项编码/目标缺失）；exit 0（released）→绿 banner + 晋升指引；exit 1（blocked，draft+report 仍产）→红 banner + blocked_reasons 修复指引。
- report 回读是**离线检视**（FileReader 本地读，不上传）；编排器跑 CLI 在浏览器外（G6）。

## 7. 编排器序列（文档化，浏览器不跑 CLI——G6）

```text
1. review extract <run>            → review.json（schema 1.1，含 supply + sha256_full）
2. review page <run>               → 审阅页.html（D2 六图 + D4 编辑层）
3. 专家浏览器开页 → D4 编辑模式 → L1/L2 编辑 → stage（localStorage 草稿态）
4. export patch.json               → 下载 patch JSON（channel=d4，patch_id 内容哈希）
5. 编排器跑 R2 CLI（浏览器外）：
   ontology_cli.py model patch <run>/ontology.ttl patch.json \
       --golden <run>/golden-cases.json [--with-l3] \
       --output-draft <工作区>/draft.ttl --report <工作区>/patch-report.json
   晋升前终检：--regression-full（D4 提交前终检，受影响子集→全集）
6. report 回读（D4 抽屉 FileReader）→ 检视 verdict/bump/diff/blocked_reasons/regression
7. 入口 (c) S4 审计 → G2/G3 人工闸门 → 人工晋升 draft→权威（历史注释合并=人工职责）
8. 重跑 review extract/page 复核（round-trip：晋升后本体→新审阅页确认编辑生效）
```

- **输出落工作区 cwd，不进 run 目录**（R2 零回写：baseline TTL + golden JSON + patch 输入三文件 sha 断言；输出 realpath 碰撞守卫）。
- **ingest_opinions 零改动**：D4 patch 是与意见单并行的新产物类型，意见新字段（anchor）自动随附录（tpl-opinion-schema §五），无接收位需求。
- **CLI 零新增 action**：review extract/page/ingest/selftest + model patch 已覆盖 D4 全链（薄分发门面无新机械能力）。

## 8. 敏感分级（R0 延伸）

- **D4 patch JSON 含字面量值**（label/comment/枚举新值）→与意见 JSON 同分级：**真实载体 patch 不出本地**（只落 run 目录受控区，不进版本控制/不进入对外分发通道）；虚构载体 patch 可入版本控制。
- 本契约配例全虚构中性（票据贴现域）；skill 资产永不写真实业务数据。
- 真实载体 D4 编辑产物（patch.json/draft.ttl/patch-report.json）一律落 git 忽略区，不外发、不入对外示例（同 ontology-simulate 铁律 4/5 口径）。

## 9. 虚构配例（票据贴现域，全虚构中性）

### 9.1 L1 改 label（PATCH annotation-only）

```json
{
  "schema_version": "1.0", "patch_id": "P-d4-<运行时算>",
  "baseline": { "path": "ontology.ttl", "sha256": "<运行时算 64hex>" },
  "source": { "channel": "d4", "ref": "d4-bill-<sha12>-001" },
  "base_version": "1.2.1", "bump": "auto",
  "operations": [
    { "op": "modify_label", "target": "http://example.org/bill-discount#Bill", "label": "票据（贴现载体）" }
  ]
}
```
→ bump=PATCH；regression=skipped(annotation-only)；exit 0。lang 省略，引擎继承旧 @zh。

### 9.2 L1 改 oneOf 受控值（MINOR，G8 保唯一）

```json
{
  "schema_version": "1.0", "patch_id": "P-d4-<运行时算>",
  "baseline": { "path": "ontology.ttl", "sha256": "<运行时算 64hex>" },
  "source": { "channel": "d4", "ref": "d4-bill-<sha12>-002" },
  "base_version": "1.2.1", "bump": "auto",
  "operations": [
    { "op": "replace_literal", "p": "rdf:first",
      "old": { "value": "已划款" }, "new": { "value": "已付款" } }
  ]
}
```
→ bump=MINOR；s 省略（全图唯一匹配，G8 预检保唯一）；old 全等编码取 enum_literals（**plain，无 lang**——票据 fixture 受控值字面量无语言标签；若载体枚举带 @zh/datatype 则 old 须携对应 lang/datatype，G2 全等编码）；exit 0（回归中性，golden 引用 0 次实证选定）。

### 9.3 L2 改继承（MINOR，parents_guard 恰 1 具名父）

```json
{
  "schema_version": "1.0", "patch_id": "P-d4-<运行时算>",
  "baseline": { "path": "ontology.ttl", "sha256": "<运行时算 64hex>" },
  "source": { "channel": "d4", "ref": "d4-bill-<sha12>-003" },
  "base_version": "1.2.1", "bump": "auto",
  "operations": [
    { "op": "remove_triple", "s": "http://example.org/bill-discount#Discountable", "p": "rdfs:subClassOf", "o": "http://example.org/bill-discount#Bill" },
    { "op": "add_triple", "s": "http://example.org/bill-discount#Discountable", "p": "rdfs:subClassOf", "o": "http://example.org/bill-discount#Holder" }
  ]
}
```
→ bump=MINOR；Discountable 恰 1 具名父 Bill + 0 匿名父→reparent 安全；remove+add 对；exit 0。

> 配例仅为接口演示，编辑语义以实际 run 的描述集/词典为准；skill 资产内配例一律虚构。真实载体 patch 不出本地（§8）。