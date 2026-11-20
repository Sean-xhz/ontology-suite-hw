# SPARQL Read 查询模板派生契约模板（D3c，query-templates schema 1.0）

> **用途**：D3c SPARQL 取知层的接口契约——`scripts/derive_sparql.py` 从 `ontology.ttl`（TBox）**机械派生** `query-templates.json`（canonical 模板库）+ `query-templates.md`（人类目录）。这是 model 覆盖矩阵「7 CRUD 查询类」SPARQL 扩展位的 **Read 取知形式化激活**：下游 Agent「经 SPARQL 取知」（methodology-core §8.1）的静态交付物。纯 rdflib 内置 SPARQL 1.1（`prepareQuery` 语法自检 + `graph.query` 可执行），无 Java、无 LLM、**零新增依赖**（rdflib 已在核心 tuple）。与 `derive_shacl.py`（R4）完全同构：TTL-direct 派生、非权威可再生、零回写、确定性 canonical。
> **前置判据**：本层是**机械 backbone**——TBox→SELECT 模板映射全确定性，无 LLM 调用。**业务查询意图**（如票据 §7.2「给定票号返回背书链」、§7.5「贴现池组合查询」）由主会话 md 补写、S6 黄金用例消费（structured-input-mapping §二第1步「查询模板随规则消费场景补写」口径不变）；CLI 只产**结构脚手架**（原子 SELECT 模板），组合拼接 + ORDER BY + 具体业务阈值绑定 = 主会话职责。查询模板库归 ontology-model（覆盖矩阵扩展位在 model，owns 全部派生层）；simulate 是实例级模拟协议（动态），本库是静态取知交付物（互补消费形态），**不 import simulate 代码**（反向分层禁止）。
> **纪律权威**：TTL 是权威（G1 冻结+S3 编译+S4 审计+L3 返修定版），查询模板库**非权威·可再生**（源 TTL 不变则模板字节不变）。**TTL-direct 派生**（否决 signature.json 路线）——与 derive_shacl 同纪律：不改 `extract_signature`/`parse_ttl`/`review_extract`（避 T4 冻结签名漂移），rdf_list/union/子类闭包/derived 判定算法本地重实现（不 import review_extract/simulate，避 model→review/simulate 反向分层）。查询词汇（类/属性/受控值/facet/derived/hasKey）同源 TTL，与 signature 消费链词汇一致。

---

## 0. 定位与纪律（不可绕过）

| 纪律 | 含义 |
|---|---|
| **模板库非权威·可再生** | `query-templates.json`/`.md` 是 TTL 的机械派生取知脚手架，非独立权威。源 TTL 变更（含 R2 patch 晋升）后**须重派生**。 |
| **零回写** | 源 TTL sha256 前后断言；输出 realpath 碰撞守卫（`--output-json`/`--output-md`/`--report` 解析后不得等于源 TTL→exit 2）；默认输出落 **cwd**，不进 run 目录、不进 skill 目录。 |
| **确定性** | JSON `json.dump(sort_keys=True, ensure_ascii=False, indent=1)` + 尾换行；MD LF；**零 now()/datetime/random/mtime**；templates 按 (kind, target_id) 全排序；FILTER 枚举值排序；prefix header 排序固定；template_id 确定性后缀命名（非内容哈希，照 derive_shacl shape IRI 先例）；**禁 bnode 随机标签泄漏**（溯源用内容标识）。源 TTL 不变则模板字节不变（T15a 双跑全量字节等无豁免）。 |
| **TTL-direct 不动签名提取** | 不改 `extract_signature`/`parse_ttl`/`review_extract`（避 T4 冻结签名漂移 + review/simulate 连锁）。derive_sparql 直接 rdflib Graph 遍历 TBox；rdf_list/union/子类闭包/derived 判定算法本地重实现（不 import review_extract/simulate，避反向分层，照 derive_shacl L37-39）。 |
| **IRI 注入守卫 + 参数化** | 嵌入查询的 IRI 过 `IRI_UNSAFE_RE`（拒空白/引号/尖括号，照 derive_shacl L84-85）；**实例数据值永不进查询文本**——标识/枚举值/数值阈值一律参数化 `?var`，合法值域作 params 元数据（受控枚举值是 TBox 词汇，登记于 params.enum_values 非硬编码进 FILTER）。 |
| **Read 取知 MVP** | 只产 SELECT 模板（7 kind）；**C/U/D（SPARQL UPDATE）不产**——ABox 实例 CRUD 与后续 R6 实例化管道重叠，票据示例 §7.4 删除悬置须 G1 确认（不补造），登记 extension_slots 不预占后续。 |
| **通用性 + 敏感** | 不耦合任何真实载体；本模板配例全虚构中性（票据贴现域）；skill 资产永不写真实业务数据；真实业务 run 产物受控目录。 |

## 1. TBox → SELECT 模板映射表（派生契约，7 kind）

| kind | 触发词汇 | SPARQL 句式骨架 | 参数 / 备注 |
|---|---|---|---|
| `class-list` | 每个**非 derived** 具名类 | `SELECT ?s WHERE { ?s a/rdfs:subClassOf* <Cls> }` | 子类闭包 property path `*`（含自身+后代，R-c 对齐，rdflib 1.1 支持）；直接变体 `?s a <Cls>` 见 notes |
| `key-lookup` | 类 `owl:hasKey`（单键） | `SELECT ?s WHERE { ?s a/rdfs:subClassOf* <Cls> . ?s <keyProp> ?key . FILTER(?key = ?id) }` | params `?id`（datatype 取 keyProp range）；标识精查脚手架（票据 §7.2①「给定票号」结构位）；复合键→gap |
| `property-get` | 每个 `owl:DatatypeProperty` | `SELECT ?s ?v WHERE { ?s <dp> ?v }`（单 domain 类加 `?s a <domain>`） | 字面量取值；union domain 展平注记；与 enum-filter/facet-filter 互补（基础检索 vs 过滤） |
| `enum-filter` | 数据属性 range = 内联匿名 `owl:oneOf` | `SELECT ?s WHERE { ?s <dp> ?v . FILTER(?v = ?val) }` | params `?val`（datatype string，**enum_values=排序受控值域**元数据）；受控值过滤脚手架 |
| `facet-filter` | 数据属性 range = 具名**数值** facet datatype（min/max facets） | `SELECT ?s WHERE { ?s <dp> ?v . FILTER(?v >= ?min && ?v <= ?max) }` | params `?min`/`?max`（datatype 取 base，notes=TBox facet 界）；数值范围脚手架（票据 §7.5 金额≥10万结构位，业务阈值主会话绑定）；pattern-only facet→gap（regex FILTER 留扩展） |
| `op-join` | 每个 `owl:ObjectProperty` | `SELECT ?s ?o WHERE { ?s <op> ?o . ?s a <domain> . ?o a <range> }` | domain→range traversal/JOIN（背书链结构位）；单 domain/range 加类型过滤，union→裸 traversal + 注记；inverseOf 注记（逆路径查询主会话组合） |
| `derived-query` | **derived** 类（SWRL head ClassAtom classPredicate） | `SELECT ?s WHERE { ?s a/rdfs:subClassOf* <DerivedCls> }` | **derived_flag=true** + notes「需先物化（Pellet）；derived 类禁入实例输入（check_instance E04）但可查推理结论；联动 ontology-simulate what-if」 |

**template_id 约定**：`q-<kind>-<target localname>`（类模板）/ `q-<kind>-<prop localname>`（属性模板）/ `q-key-lookup-<Cls>-<keyProp>`（键模板）。确定性后缀命名，全排序。每模板挂 `source_locator`（类/属性 IRI）+ `provenance`（rdfs:comment 源句编号，best-effort 照 derive_shacl SOURCE_RE）。

**prefix header**：固定排序前缀块（`PREFIX : <base>` + `PREFIX rdfs:` + `PREFIX xsd:` + 源图相关前缀排序），每模板 sparql 文本自带完整 header（独立可执行）。

## 2. 设计取舍（实证驱动）

| 取舍 | 问题 / 依据 | 处置 |
|---|---|---|
| **D-a TTL-direct** | signature.json 路线需先跑 `simulate signature` 两步链、缺 facet 值、model 上游消费下游产物略逆分层 | 直接读 ontology.ttl 本地解析词汇，`model queries ontology.ttl` 一步自包含；facet 值可取（数值 FILTER）；零 T4 漂移；查询词汇同源 TTL 与 signature 一致。偏离 backlog「signature→」字面，取舍登记于此（照 derive_shacl TTL-direct 先例） |
| **D-b Read 取知 MVP** | 全 CRUD 的 ABox C/U/D 与后续 R6 实例化管道重叠；票据 §7.4 删除悬置（不补造） | 只产 7 类 SELECT；C/U/D 登记 extension_slots（create/update 留后续 R6，delete 示例悬置须 G1）；对齐 methodology §8「Agent 经 SPARQL 取知」 |
| **D-c 子类闭包 property path** | 个体仅类型化子类（`:b a :Discountable`），严格 `?s a :Bill` 漏检 | class-list/derived-query/key-lookup 用 `a/rdfs:subClassOf*`（零或多步，含自身+具名后代闭包，R-c 对齐）；rdflib SPARQL 1.1 property path 原生支持，无需推理机 |
| **D-d derived 类分流** | derived 结论类（SWRL head）禁入实例输入（check_instance E04），但**查询推理结论正是取知核心** | derived 类不产 class-list，改产 derived-query（derived_flag=true + 需先物化注记）；执行需 Pellet 物化（T15 只断言语法 valid + 注记，物化执行属 simulate） |
| **D-e 参数化 + IRI 守卫** | SPARQL 注入风险；实例数据值硬编码破坏模板复用性与确定性 | 标识/枚举值/数值阈值一律 `?var` 参数化；受控枚举值域作 params.enum_values 元数据（排序）；嵌入 IRI 过 IRI_UNSAFE_RE，不安全→gap 不产模板 |

## 3. gaps / extension_slots 登记契约（不承接显式登记，禁静默丢弃）

query-templates.json `coverage.gaps[]` 逐条 `{gap_id, kind, locator, note}`（locator 用内容标识，禁裸 bnode）：

| kind | 触发 | 理由 |
|---|---|---|
| `hasKey-composite` | 复合 hasKey（多键）/非 URIRef 键 | MVP 只承接单键类内（照 derive_shacl） |
| `hasKey-iri-unsafe` | 键/类 IRI 含不安全字符 | 无法安全嵌入 SPARQL |
| `pattern-facet-no-regex` | 数据属性 range = pattern-only facet（无数值界） | regex FILTER 留扩展（key-lookup 已覆盖标识类） |
| `no-domain` | 属性无 rdfs:domain | property-get/op-join 降级裸 traversal + 注记 |
| `anonymous-range` | 对象属性 range 为匿名类表达式 | op-join 降级裸 traversal + 注记 |
| `isolated-class` | 类无实例消费场景登记（best-effort） | 登记待主会话确认消费意图 |

**extension_slots（设计边界，非 gaps 逐条）**：`{create: "ABox 实例创建留后续 R6 实例化管道", update: "ABox 实例更新留后续 R6", delete: "票据示例 §7.4 删除悬置须 G1 确认（不补造）"}`。组合查询（多模板拼接 + ORDER BY + 业务阈值）= 主会话职责非 CLI；图库就绪后 SPARQL 精查（methodology §8.7）留后续；rdflib SPARQL 引擎能力边界（property path * 支持，复杂联邦查询/FULLTEXT 不支持）登记。

## 4. CLI 与 exit 三态

```bash
# 派生（纯 rdflib 内置 SPARQL，无 Java/无 LLM/零新增依赖）
python3 <skill根>/scripts/derive_sparql.py <ontology.ttl> \
    [--output-json PATH] [--output-md PATH] [--report PATH]
# CLI 门面
python3 scripts/ontology_cli.py model queries <ontology.ttl> [--output-json PATH] [--output-md PATH]
```

| 脚本 | exit 0 | exit 1 | exit 2 |
|---|---|---|---|
| derive_sparql | 派生成功（gap 登记不阻塞） | 模板 IRI 碰撞 / 零回写断言失败 / prepareQuery 语法自检失败 | 文件缺失 / TTL 解析失败 / 输出==输入 / 无 base ns |

- `--output-json`（默认 cwd/query-templates.json）/ `--output-md`（默认 cwd/query-templates.md）/ `--report`（默认 cwd/derivation-report.json，可选覆盖报告）。
- **prepareQuery 语法自检**：每模板 sparql 经 `rdflib.plugins.sparql.prepareQuery` 解析（不执行、不篡改图），失败→exit 1（派生阻断，照 derive_shacl IRI 碰撞 exit 1 口径）。
- **执行验证属 T15 / 主会话**：derive_sparql 只产模板 + 语法自检；`graph.query()` 执行验证在 T15c（fixture 实例）与主会话消费链路手测，不在派生器内（派生器零实例依赖）。

**报告 schema**：query-templates.json `{schema_version, source_ttl, ttl_sha, base_iri, prefixes{}, templates[]{template_id,kind,title,target{class,property},sparql,params[]{name,datatype,note,enum_values?},derived_flag,source_locator,provenance,notes}, counts{classes,object_properties,data_properties,templates_total,by_kind{}}, coverage{mapped_classes[],unmapped_constructs[],gaps[]}, extension_slots{}, derivation{script_version,library,source_sha256}}`。derivation-report.json（可选）`{schema_version, source_ttl, source_sha256, base_ns, counts, kind_counts, mapped[], unmapped[], decisions[]}`（照 derive_shacl report 体例）。子协议 query-templates schema 1.0 独立登记，不随 skill 版本联动。

## 5. 虚构票据配例（派生计数锚 + 执行三态）

虚构票据贴现 TBox 最小 fixture（T15 运行时 tmp 生成，examples 零改动）：设 6 类（Bill / Acceptor / Holder / EndorsementRecord / DiscountApplication 非 derived + Discountable derived ⊑ Bill）/ 3 对象属性（currentHolder Bill→Holder Functional / hasEndorser EndorsementRecord→Holder / targetsBill DiscountApplication→Bill）/ 5 数据属性（billNumber pattern-facet+hasKey / faceAmount numeric-facet / applicationStatus enum / creditRating enum / unifiedSocialCreditCode string+hasKey）/ 1 SWRL（head ClassAtom Discountable）/ 2 hasKey（Bill billNumber / Acceptor unifiedSocialCreditCode）/ 2 facet datatype（BillNumberFormat pattern / PositiveAmount minExclusive 0 decimal）：

```text
class-list 5（非 derived 类）/ derived-query 1（Discountable）/
key-lookup 2 / property-get 5 / enum-filter 2 / facet-filter 1（faceAmount）/ op-join 3
templates_total 19
gaps: pattern-facet-no-regex×1（billNumber，key-lookup 已覆盖）
counts: classes 6 / object_properties 3 / data_properties 5
```

执行三态（T15c fixture 实例 graph.query）：

| 例 | 模板 + 绑定 | 结果 |
|---|---|---|
| class-list 正例 | `q-class-list-Bill`（fixture bill1 a Bill + bill2 a Discountable 子类） | 闭包返回 2 bindings（子类类型化个体不漏，D-c 回归） |
| key-lookup 正例 | `q-key-lookup-Bill-billNumber` 绑 ?id="PJ000000000001" | 返回 1 binding（bill1，标识精查） |
| op-join 正例 | `q-op-join-currentHolder`（直接 domain 过滤 ?s a Bill） | 返回 1 binding（bill1→holder1；bill2 仅 Discountable 子类不在直接 domain，与 class-list 闭包对照） |
| enum-filter 正例 | `q-enum-filter-applicationStatus` 绑 ?val="审核中" | 返回 1 binding（app1，受控值过滤） |
| derived-query 语法 | `q-derived-query-Discountable` prepareQuery 解析通过 | derived_flag=true + 需先物化注记（执行需 Pellet，T15 不执行） |
| 契约错 | 缺文件 / 坏 TTL / 输出==源 | 各 exit 2 不产包 |

## 6. 边界与分界（report 与文档明示）

- **机械/LLM 分界**：CLI 产原子结构脚手架（7 kind）；业务查询意图（票据 §7.2 背书链/受理结论/可贴现判定、§7.5 贴现池组合查询）= 主会话 md 补写，绑定模板参数 + 多模板拼接 + ORDER BY → S6 黄金用例消费。组合查询非 CLI 职责（「查询模板随规则消费场景补写」口径不变）。
- **与 simulate what-if 联动（互补消费形态，零代码依赖）**：simulate 物化实例（动态模拟协议）后，derived-query 模板可查推理结论（静态取知）；derived-query notes 指向 simulate。本库不 import simulate 代码（反向分层禁止），文档联动。
- **与 check_instance 正交**：check_instance=签名词汇封闭（防臆造/越权，实例输入闸门）；查询模板=取知脚手架（实例查询）。derived 类禁入输入（E04）但可查询结论——正交不冲突。
- **与 derive_shacl 同构正交**：derive_shacl 产 shapes.ttl（封闭世界数据完整性，validate_shacl 消费）；derive_sparql 产 query-templates.json（取知查询脚手架，Agent/主会话消费）。两者皆 TTL-direct 派生、非权威可再生、零回写、纯 rdflib、确定性 canonical。
- **rdflib SPARQL 引擎能力边界**：property path `*`/`+`/`?` 支持；复杂联邦查询（SERVICE）/FULLTEXT/聚合嵌套深度有限——MVP 只用基础 SELECT + FILTER + property path，超出登记扩展位。
- **性能**：派生=源图单遍 O(n)+模板字符串生成秒级（不需源 TTL canonicalize，区别于限制⑭ 60s 成本）；prepareQuery 语法自检每模板毫秒级；执行随数据图线性（T15 fixture 小规模）。
- **空 TBox 平凡产空库**：无类/属性→templates_total 0（gap 登记，不报错；JSON 侧主会话消费前确认非空）。