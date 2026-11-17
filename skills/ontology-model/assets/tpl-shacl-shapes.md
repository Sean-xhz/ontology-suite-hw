# SHACL shapes 派生与校验契约模板（R4，shapes schema 1.0）

> **用途**：R4 SHACL 约束校验层的接口契约——`scripts/derive_shacl.py` 从 `ontology.ttl`（TBox）**机械派生** `shapes.ttl` + `derivation-report.json`；`scripts/validate_shacl.py`（pyshacl 引擎）用 shapes 校验实例数据 TTL 产违规看板。SHACL（封闭世界**数据完整性**）补 OWL（开放世界**逻辑一致性**）盲区：限制⑩下 Pellet 剥离 facet 具名 datatype 后推理器侧永不校验实例值，check_instance E08 对具名 facet datatype 只发 W08 放行——R4 是套件内**首个实例级 facet/基数/唯一性强制器**，纯 Python 无 Java（skip-java 环境也可跑），是 R6 实例化管道前置地基。
> **前置判据**：本层是**机械 backbone**——TBox→SHACL 映射与图匹配校验全确定性，无 LLM 调用。「意见→shape」语义翻译不在内（外接编排器承担）。shapes 是 TBox 侧验证契约，归 ontology-model（已 owns 全部验证层）；simulate→model import 方向已存在，反向禁止。
> **纪律权威**：TTL 是权威（G1 冻结+S3 编译+S4 审计+L3 返修定版），shapes **非权威·可再生**（源 TTL 不变则 shapes 字节不变）。**TTL-direct 派生**（非从 29 句话描述集）——TTL 含描述集没有的精确化（正则位数/hasKey 替代/枚举内联化/qualified cardinality 裁量），从描述集派生会绕过裁定链、重新引入已消解歧义；provenance 经 `rdfs:comment` 源句编号不断链。

---

## 0. 定位与纪律（不可绕过）

| 纪律 | 含义 |
|---|---|
| **shapes 非权威·可再生** | `shapes.ttl` 是 TTL 的机械派生验证契约，非独立权威。源 TTL 变更（含 R2 patch 晋升）后**须重派生**；R2 `replace_literal` 改 oneOf 枚举后 shapes 手动重派生=操作纪律。 |
| **零回写** | 源 TTL sha256 前后断言；输出 realpath 碰撞守卫（`--output-shapes`/`--report` 解析后不得等于源 TTL→exit 2）；默认输出落 **cwd**，不进 run 目录。validate_shacl 只读 data/shapes。 |
| **确定性** | canonical-copy-rebind（`to_canonical_graph`→逐三元组 copy 新 Graph→rebind 原前缀→serialize turtle）+ 无时间戳溯源头；report 排序无时间戳；**禁 bnode 随机标签泄漏**（unmapped construct 用内容标识非裸 bnode，v6 纪律）。**序列化前绝不喂 pyshacl**——`validate` 会向 shapes 图注入 owl 公理破坏确定性（实证 2026-11-17）；validate_shacl 每次从文件 fresh parse。 |
| **TTL-direct 不动签名提取** | 不改 `extract_signature`/`parse_ttl`/`review_extract`（避 T4 冻结签名漂移 + review/simulate 连锁）。derive_shacl 直接 rdflib Graph 遍历 TBox；rdf_list/union 算法本地重实现（不 import review_extract，避 model→review 反向分层）。 |
| **shape IRI 碰撞守卫** | shape IRI（`:<Cls>Shape` / `:<Cls>Shape_<prop>`）与源图具名 IRI 交集→**exit 1**（防派生构件覆盖源构件语义）。 |
| **通用性 + 敏感** | 不耦合任何真实载体；本模板配例全虚构中性（票据贴现域）；skill 资产永不写真实业务数据。 |

## 1. TBox → SHACL 映射表（派生契约）

| TBox 构件 | SHACL 发射 | 备注 |
|---|---|---|
| `owl:DatatypeProperty` range = 具名 facet datatype（`rdfs:Datatype` + `onDatatype` + `withRestrictions`） | 逐 facet（`xsd:pattern/minExclusive/minInclusive/maxExclusive/maxInclusive/minLength/maxLength`→同名 `sh:`）+ `sh:nodeKind sh:Literal`；base==string→`sh:datatype xsd:string`；base∈数值容忍集→**不发** `sh:datatype`（R-d） | facet Literal term 原样保留 datatype（`"0"^^xsd:decimal`） |
| `owl:DatatypeProperty` range = xsd 基型 | `sh:datatype`（非数值容忍集）+ `sh:nodeKind sh:Literal` | integer/string/date/dateTime/boolean 正常发 |
| `owl:DatatypeProperty` range = 内联匿名 `owl:oneOf` | `sh:in`（rdf:list，字面量 term 原样）+ `sh:nodeKind sh:Literal` | 与 check_instance E07 + Pellet 内联 oneOf 三保险 |
| `owl:FunctionalProperty`（数据/对象） | `sh:maxCount 1` | 与 Restriction 派生**幂等合并**同 PropertyShape IRI |
| `owl:ObjectProperty` range = 类 | `sh:class` 子类闭包 `sh:or`（R-c）+ `sh:nodeKind sh:IRI` | union range 展平全部后代为一个 sh:or |
| `rdfs:domain` = `owl:unionOf` 匿名类 | 逐成员类建 NodeShape（多 targetClass） | 如 unifiedSocialCreditCode domain unionOf(Acceptor,Holder) |
| Restriction `someValuesFrom` C | `sh:minCount 1` + class 约束（R-c）+ nodeKind IRI | 必填基数 |
| Restriction `allValuesFrom` C | class 约束（R-c） | 值域 |
| Restriction `maxQualifiedCardinality` n `onClass` C | `sh:qualifiedMaxCount n` + `sh:qualifiedValueShape`（C 定义类展开，R-a） | 限定基数 |
| Restriction `minQualifiedCardinality` n `onClass` C | `sh:qualifiedMinCount n` + `sh:qualifiedValueShape`（R-a） | |
| Restriction `cardinality`/`minCardinality`/`maxCardinality` n | `sh:minCount`/`sh:maxCount` n | 裸基数 |
| Restriction `hasValue` v | `sh:hasValue` v（原 term） | |
| `owl:hasKey` (单键) | NodeShape `sh:sparql` 类内唯一键 SELECT（R-c 闭包 UNION）+ `sh:message` | 复合键→unmapped |
| `owl:inverseOf` | R-b 路径构造（见 §2），**不物化逆三元组** | 推理机职责，仅用于路径 |

**NodeShape/PropertyShape IRI 约定**：`:<Cls>Shape`（`sh:targetClass <Cls>`）/ `:<Cls>Shape_<prop>`（`sh:path`）。同 (cls,prop) 多来源约束（对象属性派生 + Restriction 派生 + Functional）自然 AND 合并到同一 PropertyShape IRI（`path_for`/`add_class_constraint` memoize 防重复 bnode）。

## 2. 四设计裁定（实证驱动，正确性必需非可选优化）

| 裁定 | 问题（实证） | 处置 |
|---|---|---|
| **R-a 定义类展开** | `sh:qualifiedValueShape [sh:class :ApplicationUnderReview]` 在**输入数据图**（未物化）漏检——定义类是推理产物，输入个体不显式 `rdf:type` 它（E8/E9 conforms=True 假阴性） | onClass 为定义类时展开 `owl:equivalentClass`：intersectionOf 逐成员 AND（具名成员→class 约束、hasValue Restriction→`sh:property[path+hasValue]`、someValuesFrom→minCount+class、allValuesFrom→class）；unionOf→sh:or 子展开；**深度上限 3**，超出/不支持形态→unmapped |
| **R-b 逆路径** | 数据断言 `targetsBill` 而公理挂 `hasDiscountApplication`（inverseOf）——不做逆路径则输入侧失效（E9） | 凡带 `owl:inverseOf` 的属性，path=`sh:alternativePath(p, [sh:inversePath q])`。**构造要点**：alternativePath 须**独立 rdf:list 节点 + sh:alternativePath 谓词包裹**——path 节点本身不可建成 rdf:list（否则 pyshacl `value_nodes_from_path` 先查 rdf:first 误判序列路径→空集→约束静默失效，实证 2026-11-17）；≥2 项（pyshacl 规格） |
| **R-c 子类闭包** | 个体仅类型化子类（`:app a :AcceptableApplication`），严格 `sh:class` 要求显式 rdf:type→误报/漏检（E14/E15） | 所有 sh:class 发射点改「具名子类闭包 sh:or」（闭包从 TTL 具名 subClassOf 传递计算，排序）；与 check_instance E06 ancestors 对齐（**SHACL 不得比它更严**）；hasKey SPARQL `?other` 类型匹配同用闭包 UNION（子类类型化个体不漏检）。`inference="rdfs"` 拒绝入 MVP（闭包副作用+性能+确定性风险），登记未来选项 |
| **R-d 数值 datatype 容忍** | `compile_instance_ttl` 把 JSON int 编码 `xsd:integer`，严格 `sh:datatype xsd:decimal` 对 integer 字面量误报（E11/E12） | decimal/double/float range **不发 sh:datatype**，只发 facet + `sh:nodeKind sh:Literal`。实证 `sh:minExclusive "0"^^xsd:decimal` 对 integer 字面量数值提升比较成立（int 500000 conform / int -5 违反）。**金额 JSON 数值契约**见 §6 |

## 3. unmapped 登记契约（不承接显式登记，禁静默丢弃）

derivation-report `unmapped[]` 逐条 `{construct, kind, reason}`（construct 用内容标识，禁裸 bnode 随机标签）：

| kind | 触发 | 理由 |
|---|---|---|
| `SWRL-rule` | `swrl:Imp` | 规则前提/结论=推理机职责，非实例数据约束（签名 rules 面不用于实例断言） |
| `TransitiveProperty`（及 Symmetric/Asymmetric/Irreflexive/Reflexive） | 属性特征声明 | 闭包/语义=推理机职责，SHACL 不承接（range shape 仍派生） |
| `AllDisjointClasses` | 互斥类公理 | 多为 derived 结论类，输入侧 E04 禁断言，属推理后校验 |
| `unconsumed-equivalentClass` | 定义类等价公理未被 qualified cardinality 消费 | MVP 不单独物化 |
| `hasKey-composite` | 复合 hasKey（多键）/非 URIRef 键 | MVP 只承接单键类内 |
| `defined-class-too-deep` | 定义类展开深度>3 / 含不支持形态 | 防无限递归 |
| `anonymous-onClass` / `anonymous-value-class` | qualified cardinality onClass / someValuesFrom 目标为匿名类表达式 | MVP 不展开 |
| `no-domain` | 属性无 rdfs:domain | 无法定位 targetClass |
| `unsupported-restriction` / `unknown-datatype-range` / `unsupported-range` | 无可映射约束形态 / range 非 xsd 基型或 facet datatype / 匿名非 oneOf range | 登记待扩展 |
| `hasKey-iri-unsafe` | 键/类 IRI 含不安全字符 | 无法安全嵌入 SPARQL |

**MVP 不承接（设计边界，非 unmapped 逐条）**：跨字段/过程约束（日期≥15天/到期>出票/状态机迁移，应用层超出 SHACL 单图）；`sh:closed`（instance.json→TTL 编译已丢未知字段，属 JSON schema 层）；property chain；minLength/maxLength（generic 支持但 fixture 无素材验收）。

## 4. CLI 与 exit 三态

```bash
# 派生（纯 rdflib，无 Java/无 pyshacl）
python3 <skill根>/scripts/derive_shacl.py <ontology.ttl> \
    [--output-shapes PATH] [--report PATH]
# 校验（rdflib + pyshacl==0.29.1）
python3 <skill根>/scripts/validate_shacl.py <data.ttl> <shapes.ttl> \
    [--json-output FILE] [--derivation-report FILE] [--strict] [--focus IRI]
```

| 脚本 | exit 0 | exit 1 | exit 2 |
|---|---|---|---|
| derive_shacl | 派生成功 | shape IRI 碰撞 / 零回写断言失败 | 文件缺失 / TTL 解析失败 / 输出==输入 / 无 base ns |
| validate_shacl | 无 error（非 strict 下 warning/info 放行） | 有 error（strict 下 warning 也致 1） | 文件缺失 / TTL 解析失败 / pyshacl 缺失（pip 指引） |

- `--strict`→`allow_warnings=False`（warning 也 exit 1）；非 strict→`allow_warnings=True`；`allow_infos=True` 恒（info 永不致失败）。
- `--focus IRI`→只校验指定 focus node（pyshacl `focus_nodes=[IRI]`）。
- `--derivation-report`→违规逐条挂源句编号（sourceShape→mapped→provenance，**best-effort**：sh:sparql/qualifiedValueShape 的 sourceShape 为 bnode 时可能 miss）。
- validate_shacl 显式 `advanced=True`/`inference=None`/`inplace=False`（输入侧断言数据口径，owlrl/rdfs 备选登记不启用）。

**报告 schema**：derivation-report `{schema_version, source_ttl, source_sha256, base_ns, counts{node_shapes,property_shapes,mapped,unmapped}, kind_counts, mapped[]{shape,source_construct,kind,provenance}, unmapped[]{construct,kind,reason}, decisions[]}`；violations-report `{schema_version, data, shapes, shapes_sha256, conforms, pass, strict, results[]{focus_node,result_path,source_shape,constraint_component,value,message,severity,source_sentences?}, counts{error,warning,info,total}}`。三子协议 schema 1.0 独立登记，不随 skill 版本联动。

## 5. 虚构票据配例（派生计数锚 + 校验三态）

虚构票据贴现 TBox（10 类/9 对象属性/13 数据属性/3 facet datatype/5 SWRL/4 hasKey）派生：

```text
node_shapes 5 / property_shapes 23 / mapped 34 / unmapped 7
kind_counts: data_property 14（USCC 双 domain）/ facet-datatype 3 / oneOf-in 2 /
             object_property 9 / restriction-someValuesFrom 1 /
             restriction-maxQualifiedCardinality 1 / hasKey-sparql 4
unmapped: SWRL-rule×5 + TransitiveProperty×1 + AllDisjointClasses×1
```

校验三态（运行时自建数据，golden 集不作正例——见 §6）：

| 例 | 数据 | 结果 |
|---|---|---|
| 正例 | 完整 Bill（hasAcceptor+currentHolder+billNumber `PJ[0-9]{12}` 合规+faceAmount **int 500000**）+Acceptor(AAA)+Holder+一笔 targetsBill 申请；变体申请仅类型化 AcceptableApplication | rc=0 conforms（R-d 数值容忍 + R-c 子类闭包双回归） |
| facet 越限 | faceAmount=-5 + billNumber="随便写" | rc=1 MinExclusive+Pattern；**对偶**：同场景 instance JSON 喂 check_instance→rc=0（W08 放行）=「Pellet 剥离放行/旧闸门放行/SHACL 检出」补洞三态 |
| 基数 | 无承兑人 / 两承兑人 / 两笔审核中申请经 targetsBill 指向同一 Bill | rc=1 MinCount / MaxCount / **QualifiedMaxCount**（R-a 展开+R-b 逆路径+R-c 闭包） |
| 枚举 | creditRating="BBB" | rc=1 In |
| hasKey | 两完整 Bill 同 billNumber | rc=1 SPARQL×2 |

## 6. 边界与分界（report 与文档明示）

- **金额 JSON 数值契约（R-d 配套）**：金额类 facts 须 **JSON 数值**（int→xsd:integer 被 R-d 容忍；float→xsd:decimal）。字符串金额（`"500000"`）→plain literal→`sh:minExclusive` 违反=检出正确但编译 agent 须避免误踩。
- **targetClass 无推理 limitation**：`sh:targetClass` 只匹配显式 `rdf:type`（无推理）——子类单独类型化个体**不获父类属性形状**（false negative 非 false positive，文档化）。R-c 闭包修复的是**值约束侧**（sh:class range/qualifiedValueShape）；完整子类 targeting 需 TBox 入数据图或 inference（MVP 不启用）。
- **与 check_instance 正交**：check_instance=签名词汇表封闭（防臆造/越权/类型错，E01-E10）；validate_shacl=数据完整性（facet/基数/键）。**T3 组合（编排器职责）**：check_instance（JSON 闸门）→ compile_instance_ttl → validate_shacl（数据完整性闸门）→ simulate_reason（物化推理）。三闸正交缺一不可。
- **与 S6 分界（SHACL 不接入 run_golden_cases）**：S6=推理验收（开放世界，golden 15 active 仅 2/15 conform——9 例缺承兑人=推理 fixture 设计使然，E13）；SHACL=输入完整性闸门（封闭世界）。语义正交，接入会炸 9/15。golden 集仅作可选 report-only 语料，不要求全集 conform。
- **空数据图平凡 conform**：无 focus=空真（JSON 侧 E01 已拦空 individuals，TTL 侧文档化）。
- **R2 耦合 MVP 解耦**：incremental_patch 不加 SHACL 回归（避 R2→pyshacl 依赖耦合）；登记未来 `--with-shacl` draft 重派生+受影响子集 delta。
- **性能**：派生=源图单遍 O(n)+shapes 小图 canonical ~200 triples 秒级（**不需源 TTL canonicalize**，区别于限制⑭ 60s 成本）；校验随数据×shapes 线性+每类一条 sparql。