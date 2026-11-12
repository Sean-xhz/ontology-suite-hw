# 推理机引擎限制与验证分工（L3 执行参考）

> **用途**：`check_consistency.py`（L3 一致性）、`run_golden_cases.py`（S6 验收）、ontology-simulate `simulate_reason.py`（what-if 物化）执行与失败归因的**自包含引擎限制登记**。本文件为规范性条款+证据锚点，不依赖外部文档；编译侧硬规范权威=`assets/prompt-generator.md`（SWRL 规范 v2 / datatype 硬规范 / 编译形态约束），结构层含义见 `references/structure-patterns.md` §七。
> **适用引擎版本**：Pellet 2.3.1 / HermiT（老版 OWLAPI），均经 owlready2 0.51 通道。**引擎或 owlready2 版本变更时须逐项复核本文件限制**（复核方法=§六削减实验）。
> **来源**：2026-10-26 ~ 2026-11-02 多轮 run 实测裁定（虚构载体端到端试跑 + 真实规模载体生产级验收 + HermiT 对照复测）；实验矩阵明细与裁定史见本 skill `CHANGELOG.md` 实证证据登记。

## 一、环境要求与发现

| 组件 | 要求 |
|---|---|
| python3 | 3.9+ |
| rdflib / owlready2 | L1/L2 解析与 L3 通道（owlready2 纯 Python 慢速模式功能不受影响） |
| JRE | HermiT 需 Java ≥17；**Pellet 需 Java ≥25**（内置 Jena class file 69.0；JRE 17 报 UnsupportedClassVersionError） |

- `find_java()` 自动选本机最高版本；环境变量 `OWL_JAVA_EXE` 可显式覆盖（脚本不写任何 dotfile）。
- L3 环境不可用 → exit 2，降级 L2 并登记 manifest，不阻塞交付（SKILL.md S4 纪律）。

## 二、限制清单（编号①-⑭ 为全链稳定引用位，不得重排）

**① 原生解析器不支持 Turtle**：owlready2 `_guess_format` 只认 RDF/XML、N-Triples、OWL/XML。**处置**：rdflib 先解析源文件 → serialize 成 RDF/XML 临时文件 → 喂 owlready2（脚本已内置）。

**② 本地路径禁加 `file://` 前缀**：会改走 urllib 下载分支且嗅探失败（表象="NTriples parsing error"）。纯绝对路径走本地打开分支，中文/空格路径原生 OK。

**③ owl:imports 必须在转换前剥离**：否则 owlready2 尝试联网下载远程 imports 直接失败（MVP 纪律本就不联网解析 imports；IRI 格式由 L2 检查）。

**④ Pellet+SWRL 可用，前提=具名变量**：SWRL 变量必须声明为具名 `swrl:Variable` 个体（写法见 §三）。bnode 包装层写法（每个 argument 是互不共享的空白节点）变量同一性失效，Pellet 报 `is not a URI node`；裸 URI 无声明则 OWLAPI 拒绝解析。ObjectPropertyAtom 与 swrlb built-in（字面量 argument）Pellet 全量执行成功（虚构载体 5 规则实测：ObjectPropertyAtom+add、lessThan 字面量参数均工作）。〔证据：2026-10-26 双引擎对照实验；旧「Pellet+SWRL=坏」结论为误判，真根因即包装层序列化〕

**⑤ HermiT 不支持 swrl:ObjectPropertyAtom 与 builtin 字面量列表项**：老版 OWLAPI 翻译失败（`rdf:first triple is a literal triple`）。ClassAtom 形态规则可被消费并检出「规则→disjoint 类冲突」型不一致；HermiT 对 bnode 包装层与具名变量均容忍（包装层问题只在 Pellet 档暴露）。

**⑥ HermiT datatype 支持不全**：部分 xsd datatype（如 `xsd:date`）抛 UnsupportedDatatypeException，须传 `ignore_unsupported_datatypes=True`。**该参数会掩盖 datatype 值空间问题——HermiT 档结果不得用于枚举/facet 验证**。

**⑦ `OwlReadyInconsistentOntologyError` 是三用途异常**：空消息=检出不一致（**正向结果**，exit 1）；消息以 `Java error message is:` 开头且含 `Ontology is inconsistent`=Pellet 检出不一致的消息形态（同为正向结果）；其他 `Java error message is:`=JVM 运行失败（继续降级）。脚本必须三分处理，否则把阳性检出差错为环境失败。

**⑧ sync_reasoner_* 签名**：owlready2 0.51 为 `sync_reasoner_pellet(x=None, ...)` / `sync_reasoner_hermit(x=None, ...)`，x **位置传** World/Ontology（无 `world=` 关键字参数）；版本属性是 `owlready2.VERSION`（无 `__version__`）。

**⑨ 具名枚举 datatype 是 Pellet 陷阱（模式层）**：`rdfs:Datatype`+仅 `owl:oneOf`（无 onDatatype）→ Pellet **值空间判空**，引用它的 `owl:hasValue` 定义类静默 ≡⊥；补 `owl:onDatatype xsd:string` → Pellet 拒跑（"Trying to use a literal as an individual"）。**唯一兼容形态=range 内联匿名 `[ owl:oneOf (...) ]`**，推荐节点补 `rdf:type rdfs:Datatype`（OWL 2 DataOneOf 标准映射，实测同样兼容）。HermiT 对此不敏感（限制⑥参数掩盖）——只有 Pellet 全量档能暴露。已编译侧固化：prompt-generator datatype 硬规范 + validate_ontology L2-DATATYPE 检查。〔证据：2026-10-26 四变体最小重现实验 m1a/m1b/m1c/m1d，见 §六矩阵 A〕

**⑩ facet 具名 datatype 的 Pellet 实例层假不一致**：限制⑨只覆盖模式层（individuals=0）——facet 类具名 datatype（xsd:pattern/minExclusive）模式层 Pellet 全量 consistent=true；但**个体断言字面量值后**，Pellet Jena loader 忽略 facet 三元组（Unsupported axiom 告警）而 datatype 推理对该值空间判空 → 个体字面量 ∉ 值空间 → range 违反 → **整个体层假不一致**（任何断言该属性字面量的用例均触发；日期/string range 不受影响）。**处置**：实例级推理加载前剥离具名 datatype——只剥 URIRef 节点的 `rdf:type rdfs:Datatype` 声明三元组及所有以该 IRI 为主/宾的三元组（含 range 引用）；**内联匿名 bnode oneOf 必须保留**（Pellet 实例层对内联 oneOf range 有真实强制力：受控值外断言剥离后仍检出不一致=真阳性）。facet 实例校验职责转 L2 脚本+数据管线；**本体文件不因 Pellet 限制改动**（facet datatype 是合法 OWL 2 形态，HermiT/Protégé 正常消费）。实现=`run_golden_cases.py::strip_named_datatypes()`（默认开启，`--no-strip` 仅调试档）。〔证据：2026-10-27 虚构载体 S6 首跑 11/15 期望一致用例全炸，削减实验 C1-C6/C1'/C4' 定位，见 §六矩阵 B〕

**⑪ SWRL head 多原子部分物化**：`swrl:head` 含 ClassAtom+IndividualPropertyAtom 两原子时，Pellet realize 仅物化其一（确定性复现，非随机）：body 为字面量原子形态→存类原子丢属性原子；body 含定义类 ClassAtom→存属性原子丢类原子；head 内原子顺序无关（换序证伪）。小本体（≤3 规则）三形态全过、builtin 存在时执行路径不同——缺陷仅在规则数多/body 含定义类原子的真实规模本体暴露。**深层规律**：SWRL 匹配阶段看不到 DL 推理出的定义类成员资格（增量装配实验：body ≤7 个普通原子全稳，加入定义类原子后 head 另一原子丢失）。**处置=编译形态约束（生成侧规避）**：head 单原子化——双结论规则 `body ⇒ C(a) ∧ P(a,r)` 拆为两条规则（与限制⑫联用双通道形态）。〔证据：2026-11-02 真实规模载体（26 规则/32 用例）9 组削减实验矩阵定位，见 §六矩阵 C〕

**⑫ 句法相同 body 的规则被去重丢弃**：两条 swrl:Imp 的 body 经变量规范化（alpha 转换）后句法相同时仅一条执行、另一条静默丢弃；body 原子重排、加被 DL 蕴含吸收的哑原子、删减其他规则均不能规避（句法级判重）。**句法相异但 DL 等价**的 body 可共存互不干扰。**修正形态（双通道标准形态）**：主规则=类原子 body+head 仅 IndividualPropertyAtom（violatedRule 拒因通道）；派生规则=同 body 的定义类等价展开字面量变体（如 `HardThresholdRule(r)` → `ruleType(r,"硬门槛")`）+head 仅 ClassAtom（结论类通道）——两通道 body 句法相异规避判重、head 单原子规避部分物化。**残留观察项**：主规则通道（类原子 body）批量执行偶发波动（根因=限制⑭第一段，已查明）；派生规则通道（字面量 body）全程零波动——结论类判定可靠性高于拒因引用；对拒因完整性有硬要求的生产场景 S6 验收做 **≥2 轮全量复跑**。〔证据：同矩阵 C；双通道形态真实规模载体实测 3/3+全量稳定〕

**⑬ HermiT 实例层双拒绝**：①本体含 swrlb 内置原子（greaterThan/equal 等）时 HermiT 加载即抛 `IllegalArgumentException: built-in atoms are not supported yet`（与规则条数无关）；②datatype 支持不全（限制⑥同源）。两参数齐备后 HermiT 仅可做 **DL 层对照**（SWRL 剥离版实测：DL 驱动用例与 Pellet 完全同构，规则驱动用例 FAIL=预期能力边界）。**结论**：`swrl_verified` 只能由 Pellet 给出；HermiT 档定位=DL 交叉验证（equivalentClass/disjoint/一致性）；工具链无第二 SWRL 引擎，限制⑪⑫「是否 Pellet 特有」不可对照。执行器 `run_golden_cases.py --engine hermit` 已内置上述参数组合。〔证据：2026-11-02 HermiT 对照复测（SWRL 剥离版 32 用例：DL 驱动 20 条全过/规则驱动 12 条 FAIL）〕

**⑭ builtin 数值规则物化的两段根因**：
- **第一段·执行器序列化非确定性（已根治）**：rdflib parse 对 SWRL RDF-list bnode 生成随机 uuid 标签（不受 PYTHONHASHSEED 控制），XML 序列化跨进程漂移 → owlready2 实体 id 依加载顺序分配 → Pellet 规则处理顺序漂移 → builtin 规则物化结果随机翻转（同一输入跨进程 PASS/FAIL 漂移；**漂移期一切「规避形态有效」结论均为假象**）。**修复=canonical 确定性档**：基底 RDF Dataset Canonicalization（`rdflib.compare.to_canonical_graph` 确定性重标 bnode，实测 5308 三元组/1138 bnodes 一次性 ~59s）→ NT 文本缓存 → 用例小图（个体全具名）NT 拼接；修复后跨进程结果完全可复现。实现=`run_golden_cases.py::canonicalize_base()`（默认开启；simulate_reason 复用，缓存 `.sim-cache/<ttl_sha>.nt`）。
- **第二段·Pellet 确定性引擎缺陷（登记不修）**：canonical 序下（raw/asc/desc 三排序对照），10 原子 body 含定义类原子+builtin 的规则拒因通道在**孤立单规则单值场景**确定性不物化（3 连全 FAIL）；显式类断言亦无效——失灵在 body 整条规则激活层面（限制⑪深层规律的新表现）。多规则并发+多字段画像语境与 11 原子含类型原子规则稳定。**九形态规避全排除**（见 §六矩阵 D）。**处置**：孤立场景用例转 exempt 第四类「执行环境限制」，语义验收由**多规则并发压力用例**承载（多规则产品+多字段画像=生产常态）；生产级改写选项=主通道 body 字面量展开化（去定义类原子）或切换生产级推理机，按条件触发裁定。
- **S6 验收纪律**：黄金集必含多规则并发压力用例作为 builtin 数值规则的语义验收主载体；孤立单规则用例 FAIL 先跑 canonical 档两次确认确定性、再做削减实验。**L2 启发式观察项（裁定登记）**：对限制⑭形态（body 含定义类原子+swrlb builtin 数值比较）暂不加生成期 L2 告警——该形态是合法且高频的业务规则编译形态，启发式误报率不可控；生成侧约束由 prompt-generator SWRL 规范+并发压力用例验收纪律承载；后续 run 再现同类孤立场景 FAIL 时再评估启发式脚本化。〔证据：2026-11-02 真实规模载体九形态削减实验+canonical 三排序对照〕

## 三、SWRL Turtle 规范写法 v2（摘要；编译细节权威=prompt-generator.md）

**变量身份=节点身份**：变量声明为具名 `swrl:Variable` 个体（每规则独立命名前缀防串扰），atom 的 argument 直接引用同一变量 IRI 实现跨 atom 共享；head 变量必须已在 body 绑定：

```turtle
:vR1_x rdf:type swrl:Variable .

[ rdf:type swrl:Imp ;
  swrl:body ( [ rdf:type swrl:ClassAtom ;
      swrl:classPredicate :Holder ;
      swrl:argument1 :vR1_x ] ) ;
  swrl:head ( [ rdf:type swrl:ClassAtom ;
      swrl:classPredicate :Discountable ;
      swrl:argument1 :vR1_x ] ) ] .
```

规则语义冲突要被 reasoner 捕获，冲突结论类之间**必须有 disjoint 声明**（无 disjoint 则并存不构成矛盾）。

## 四、三级降级链与 swrl_verified 字段

```
① Pellet 全量        → 成功: swrl_verified="pellet"（完整 SWRL 执行）
② HermiT 全量        → 成功: swrl_verified="hermit-partial"（ClassAtom 规则被消费；
                        ObjectPropertyAtom/builtin 会导致本档失败进 ③）
③ HermiT 剥离 SWRL   → 成功: swrl_verified=false（仅 DL 层一致性；SWRL 语义冲突
                        转交 S4 双模型审计承接，登记 manifest）
全部失败             → exit 2，降级 L2（登记 manifest，不阻塞交付）
```

退出码：0=一致 / 1=检出不一致 / 2=环境不可用或解析失败。JSON 字段含 reasoner_used、consistent、inconsistent_classes、swrl_rules、swrl_verified、notes。

## 五、L2/L3 验证分工（互补不替代）

| 缺陷类型 | L2 脚本 | L3 reasoner |
|---|---|---|
| 循环继承（A⊑B⊑C⊑A） | ✅ L2-CYCLE | ✗（DL 中循环 subclass 非矛盾，L3 exit 0 属正确行为） |
| disjoint∧subClassOf | ✅ L2-DISJOINT | ✅ Pellet（ClassX≡⊥） |
| Functional+Transitive 等属性特征矛盾 | ✅ L2-PROP-CHAR | Pellet realize 亦可暴露 |
| SWRL 规则语义冲突（ClassAtom 型，具名变量） | ✗（结构合法零 error） | ✅ Pellet 全量（swrl_verified="pellet"）；HermiT 亦可 |
| SWRL 含 ObjectPropertyAtom+swrlb built-in | ✗ | ✅ Pellet 全量执行；HermiT ✗（literal 列表项翻译失败→降级③） |
| 具名枚举 datatype 值空间判空 | ✅ L2-DATATYPE | ✅ 仅 Pellet 暴露（HermiT 掩盖）——限制⑨ |
| facet datatype 实例层校验 | ✅ L2 脚本+数据管线承接 | ⚠️ Pellet 实例层假不一致（限制⑩）——执行器 strip 具名 datatype；内联 oneOf 枚举实例层真强制 |
| SWRL head 多原子 | ✅ 启发式 warning（L2-SWRL-FORM） | ⚠️ Pellet 部分物化（限制⑪）——生成侧 head 单原子化规避 |
| 句法相同 body 的多条 swrl:Imp | ✗（可选增强：同构 body warning） | ⚠️ Pellet 去重丢弃（限制⑫）——双通道 body 须句法相异 |
| builtin 数值规则跨进程可复现性 | ✗（L2 不涉及执行序） | ⚠️ 序列化非确定性已根治（canonical 档）；孤立场景确定性失灵=限制⑭第二段（并发压力用例承载验收） |

## 六、削减实验方法与矩阵登记（失败归因纪律）

**方法**：首跑失败禁止盲改本体/用例——①先跑 canonical 档两次确认确定性（排除漂移期假象）；②逐构件对照+剥离对照构造最小重现实验；③根因定案后按归属处置（模型缺陷→回 S3 / 用例错误→修用例 / 规则冲突→G2 / 执行环境限制→修执行器不改本体）；④实验副本与结果 json 落 run 目录 `实验/` 区登记可再生性。**已排除的规避形态不得重复测试**（下表为定案结论）。

| 矩阵 | 针对限制 | 实验形态 | 定案结论 |
|---|---|---|---|
| A · datatype 四变体（2026-10-26） | ⑨ | m1a 具名 oneOf / m1b 裸内联 / m1c 具名+onDatatype / m1d 内联+type | m1a 值空间判空（定义类≡⊥）；m1c 拒跑；m1b/m1d 兼容——推荐 m1d（标准映射） |
| B · facet 剥离对照（2026-10-27） | ⑩ | C1-C6/C1'/C4'：模式层 vs 实例层、具名 vs 内联、剥离 vs 保留 | facet 具名 datatype 实例层假不一致；内联 oneOf 保留有真强制力（受控值外断言检出=真阳性，「Pellet 可能忽略内联 oneOf」预警证伪） |
| C · SWRL 形态九组（2026-11-02） | ⑪⑫ | head 原子换序 / body 字面量 vs 定义类原子 / 小本体（≤3 规则）对照 / builtin 存在性 / 增量装配（body 逐加原子）/ alpha 改名 / 哑原子 / 原子重排 / 删减邻规则 | head 多原子部分物化（顺序无关）；句法级判重（重排/哑原子无效）；定义类原子触发匹配盲区；双通道形态（head 单原子+body 句法相异）为唯一稳定解 |
| D · 确定性九形态（2026-11-02） | ⑭ | 文件重序列化 / 排序 / 原子重排 / range 删除 / 多字段语境强化 / 前缀更换 / 显式类断言 / 邻位规则 / 值类型改 decimal；另 canonical raw/asc/desc 三排序对照 | 第一段根因=bnode 随机标签序列化漂移（canonical 根治）；第二段孤立场景失灵九形态规避全排除（登记不修，exempt+并发压力用例承载） |
| E · HermiT 对照（2026-11-02） | ⑬ | SWRL 剥离版 32 用例（DL 驱动 20/规则驱动 12） | DL 层与 Pellet 完全同构；规则驱动 FAIL=能力边界——HermiT 定位 DL 交叉验证，swrl_verified 只能 Pellet 给出 |

## 七、归因分类与升级路径判断

限制①-⑭按根因分三类，升级引擎/绑定层的影响各不同：

| 归因类 | 限制 | 根因层 | 升级是否解决 |
|---|---|---|---|
| A 绑定/序列化层 | ①②③⑦⑧、⑭第一段 | owlready2/rdflib 通道（非推理机） | 升级推理机无效；⑭第一段已 canonical 根治；⑧为版本钉住登记（API 签名），升级 owlready2 须复核签名与异常形态 |
| B 引擎实现缺陷 | ⑨⑩⑪⑫、⑭第二段 | Pellet 2.3.1 实现 bug/局限 | 社区 fork Openllet（Pellet 后继，最新 2.6.5/2019，维护 sporadic）可能修复部分，**无实证不得预设**；须按 §六 削减实验矩阵 A-D 逐项重测 |
| C 引擎能力边界 | ⑤⑥⑬ | HermiT 终版（1.4.x，无后续发行），builtin 从未实现 | 无升级标的；换引擎须实证 SWRL 全量能力后方可替代 Pellet 档 |

**④特殊**：具名变量要求本质是 W3C SWRL RDF 正确序列化形态（bnode 包装层本身非标），已由编译侧 SWRL 规范 v2 固化，跨引擎可移植，非引擎坑。

**升级纪律**：当前规避形态（内联匿名 oneOf / head 单原子化 / 双通道 body 句法相异）均为合法 OWL 2/SWRL 标准形态，引擎无关——换引擎不使规避形态成为债务。任何引擎或 owlready2 版本变更属独立引擎维护批次：§六 矩阵逐项复核 + 套件全量验收重跑 + 重冻结，不得以版本号推断修复。生产级推理机切换按限制⑭第二段「按条件触发裁定」通道。
