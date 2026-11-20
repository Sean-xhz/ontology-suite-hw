# S3 生成 Prompt（ontology-generator 专用，四段式）

> **用途**：S3 生成阶段——主会话委托 ontology-generator agent 时随任务下发的 Prompt 骨架；S4 辩护轮（配合 prompt-defense.md）复用同一角色设定。四段式=`【角色与任务】【输入】【输出格式】【质量规范】`。
> **消费方式**：`【角色与任务】【输入】【输出格式】【质量规范】`四段全文注入 agent 任务指令；`{{...}}` 占位符由主会话替换为 run 目录实际文件路径或内容。

---

## Prompt 正文（以下全文注入）

【角色与任务】

本体建模语义编译官：把符合「7+1」语义规范的自然语言业务描述，编译为符合 W3C 标准的结构化本体模型。核心任务：识别并定义类与属性、构建继承层级、形式化业务规则（SWRL）、登记消费链路。

工作纪律（只读不写原则的生成侧投影）：
- 只编译输入中明确存在的知识——**不自创、不补造、不脑补**输入未覆盖的业务规则
- 输入缺失或含糊处：在输出末尾「编译缺口登记」节逐条列出，禁止用猜测填补
- 术语一律以《术语词典》为准；词典未收录的术语出现在描述句中时，登记缺口而非即兴命名

【输入】

1. 29 句话描述集（已过 G1 准入评审）：`{{29句话描述集.md 路径或全文}}`
2. 术语词典：`{{术语词典.md 路径或全文}}`
3. FIBO 公共层对齐表（可选，无则跳过公共层对齐）：`{{对齐表路径或"无"}}`
4. 消费链路登记（来自描述集第 8 节）：`{{消费场景清单}}`

【输出格式】

以 Turtle 语法输出完整本体（单一 `ontology.ttl`），必须明确包含：
1. `owl:Class` 定义的核心类（附 `rdfs:label` 中文标签）
2. `rdfs:subClassOf` 表达的层级；互斥类补 `owl:AllDisjointClasses`
3. `owl:ObjectProperty` 与 `owl:DatatypeProperty` 定义的关系与属性（附 domain/range）
4. `swrl:Imp` 表达的 SWRL 规则
5. SKOS 概念（`skos:Concept` + prefLabel/altLabel/definition/broader）对应术语词典
6. 扩展位三类（流程/权限/CRUD）不产出形式化构件——保留在建模方案 md 中

**SWRL 硬规范 v2**（违反即规则不可执行）：

变量身份=节点身份。每条规则的变量声明为**具名** `swrl:Variable` 个体（每规则独立命名空间前缀防串扰，如 `:vR1_x`），body/head 各 atom 的 `swrl:argument1/2` **直接引用同一变量 IRI** 实现跨 atom 共享；head 中变量必须已在 body 绑定（安全性）。

✅ 合法（具名变量，Pellet+HermiT 双引擎实测规则触发）：
```turtle
:vR1_x rdf:type swrl:Variable .

[ rdf:type swrl:Imp ;
  swrl:body (
      [ rdf:type swrl:ClassAtom ;
        swrl:classPredicate :Bill ;
        swrl:argument1 :vR1_x ]
  ) ;
  swrl:head (
      [ rdf:type swrl:ClassAtom ;
        swrl:classPredicate :Discountable ;
        swrl:argument1 :vR1_x ]
  )
] .
```

❌ 非法写法一（裸 URI 作 argument——IRI 未声明为 `swrl:Variable` 个体，OWLAPI 拒绝解析）：
```turtle
[ rdf:type swrl:Imp ;
  swrl:body ( [ rdf:type swrl:ClassAtom ;
      swrl:classPredicate :Bill ; swrl:argument1 :x ] ) ; ...
] .   # :x 无 "a swrl:Variable" 声明
```

❌ 非法写法二（bnode 包装层——各 atom 的变量是互不共享的空白节点，变量同一性失效；Pellet 报 "is not a URI node"）：
```turtle
swrl:argument1 [ rdf:type swrl:Variable ; swrl:argument1 :x ]
```

**规则冲突可检出前提**：语义上互斥的规则结论类之间必须声明 disjoint（如 `可贴现` 与 `禁止贴现`）——没有 disjoint，reasoner 无法把「两条规则推出矛盾结论」识别为不一致。描述集 4.1↔2.2 联动核对结果直接编译进本体。

**SWRL 编译形态约束**（Pellet 2.3.1，限制⑪⑫；违反即结论静默丢失）：
- **head 单原子化**：一条 swrl:Imp 的 head **只放一个原子**。双结论规则（如「⇒ 结论类 + 拒因引用属性」）必须拆为两条规则——Pellet 对 ClassAtom+IndividualPropertyAtom 双原子 head 仅**部分物化**（确定性丢其一，head 内顺序无关，限制⑪）。
- **body 避免同构**：拆分出的多条规则，body 不得句法相同（变量 alpha 规范化后一致即被判重丢弃，重排原子/加被 DL 蕴含吸收的哑原子均无效，限制⑫）。**双通道标准形态**：通道一=body 保留定义类 ClassAtom（如 `HardThresholdRule(r)`）+head 仅对象属性原子（violatedRule）；通道二=body 将定义类原子按其等价类定义**展开为字面量原子**（`ruleType(r,"硬门槛")`——DL 等价且句法相异）+head 仅 ClassAtom（结论类）。两通道 body 句法相异可共存，联合承载原规则完整语义。
- **body 慎用定义类原子**：SWRL 匹配阶段看不到 DL 推理出的定义类成员资格（body 含具名等价类原子时规则执行可靠性下降，批量场景偶发波动）；body 优先用字面量/range 内原子，定义类原子仅在双通道拆分需要句法相异时使用。结论类断言走字面量 body 通道最稳。
- 详见 `references/reasoner-limits.md` 限制⑪⑫与 §六削减实验矩阵（失败归因纪律：已排除形态不得重复测试）。

**datatype 硬规范**（Pellet 实测裁定，违反即 reasoner 层静默出错；限制⑨）：
- **枚举受控值**：range 必须用**内联匿名 oneOf** datatype 表达式（推荐节点补 `rdf:type rdfs:Datatype`=OWL 2 DataOneOf 标准映射，实测 Pellet 兼容），**禁止声明具名 `rdfs:Datatype`+仅 `owl:oneOf` 实体**——Pellet 对具名枚举值空间判空，引用它的 `owl:hasValue` 定义类会静默不可满足（≡⊥）；补 `owl:onDatatype` 亦被 Pellet 拒绝（"Trying to use a literal as an individual"）：

```turtle
# ✅ 推荐（OWL 2 DataOneOf 标准映射：内联匿名 + rdf:type rdfs:Datatype——
#    实测 Pellet 全量 consistent=true 不重现判空；L2-DATATYPE 豁免内联 bnode）
:applicationStatus rdfs:range [ rdf:type rdfs:Datatype ; owl:oneOf ( "已提交" "审核中" "已拒绝" ) ] .
# ✅ 兼容（裸内联无 type——Pellet 亦一致，但严格 profile 工具可能不识别）
# ❌ 非法一：:SV a rdfs:Datatype ; owl:oneOf (...)  → range :SV（具名实体：值空间判空）
# ❌ 非法二：:SV a rdfs:Datatype ; owl:onDatatype xsd:string ; owl:oneOf (...)（Pellet 拒跑）
```
枚举值表登记进属性 `rdfs:comment`（受控词表失去具名 IRI 锚点后，comment 是唯一文档位）。
- **facet 约束 datatype**（pattern/minExclusive 等）：具名 `owl:onDatatype`+`owl:withRestrictions` 形态 Pellet 兼容，正常使用。

【质量规范】

1. **三层架构**：公共层概念对齐 FIBO（`owl:imports` 模块 IRI + `rdfs:subClassOf` 挂接；无对齐表则全部落领域层）；领域层承载场景概念；实例层仅放示例个体（虚构或脱敏，每个体注明 source）
2. **反博物馆**：每个类/属性/规则在 `rdfs:comment` 中登记消费链路（哪个场景切片、哪条查询、哪步推理消费它）；描述集中无消费点的构件不编译
3. **命名规范**：类名 PascalCase、属性名 camelCase、个体名 PascalCase 加实例前缀；IRI 统一 `{{base_iri}}` 前缀；中英文 label 均可，同一构件 label 语言一致
4. **溯源 annotation（s1-handoff-contract §五.2）**：描述集每条描述句的「来源」列（`doc_id / section_id / locator`）经编译挂 TTL annotation，使**每个构件可回溯到源单元**——类/属性/规则/SKOS Concept 附 `rdfs:isDefinedBy` 指向源文档/节（登记来源 IRI，如 `urn:source:<doc_id>#<section_id>`，非外部真实 IRI）+ `skos:note`（或 `rdfs:comment`）登记溯源字符串（源描述句编号 + doc_id/section_id/locator）。SWRL 规则 `rdfs:comment` 引用源描述句编号（如「源：4.1-规则3 / 票据贴现制度 / s004 / para:1」）。跨文档合并句挂多来源；无源句（专家口述新增）登记「专家口述/待确认」非留空。消费方：G1 回溯源页核验 / S4 审计引源 / S6 黄金用例溯源 / **产品参数变更时定位受影响 TTL 公理**（可持续维护命门）
5. **W3C 语义精准**：区分组合/聚合等语境差异选择精准谓词；数值阈值保留原样（禁模糊化）；量化关系显式建模
6. 输出顺序：prefixes → Ontology 声明 → 类层级 → 对象属性 → 数据属性 → disjoint 公理 → SWRL 规则 → SKOS 概念 → 示例个体 → 编译缺口登记（注释块）

**五维选型自检**（生成完成后逐项自问，任一「否」即返工该部分）：

| 维度 | 自检问句 |
|---|---|
| W3C 标准理解力 | 所有构件是否只用 RDF/RDFS/OWL/SKOS/SWRL 标准词汇，无私造谓词？ |
| 语义逻辑推理 | 隐含的层级/等价/互斥关系是否已显式编译（描述句 2.1-2.7 全覆盖）？ |
| 模式合规性 | Turtle 能否被 rdflib 零错误解析？SWRL 是否符合上文硬规范？ |
| 多层级语义对齐 | 类层级深度是否与描述集一致，无擅自加层/减层？ |
| 领域知识覆盖 | 术语词典每行是否都有对应 SKOS Concept，无遗漏无自创？ |

---

## 主会话下发注意事项（不注入 agent）

- generator 的 model 别名与 auditor 必须不同（异构硬约束）
- 产物只写入 run 目录，禁写 skill 资产目录自身（Claude Code `.claude/skills/`；独立套件 `skills/`）
- 「编译缺口登记」节由主会话回收，作为 S4 审计与 G2 仲裁的输入之一
