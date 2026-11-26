# builtin × 引擎支持矩阵（IT-06）

> 结构化替代 reasoner-limits 限制⑬⑭的 builtin 维度散文条目（限制编号①-⑭为全链稳定引用位不变，本文件是 builtin 维度的结构化视图，非新增编号）。
> **内容以我方 L3 实测裁定为准**——不抄 OntoMind SwrlBuiltinCatalog 的 OXIRS/JENA 口径（引擎栈不同，其矩阵内容【存疑待验证】）。
> 引擎版本：Pellet 2.3.1 / HermiT（老版 OWLAPI），均经 owlready2 0.51 通道。**引擎或 owlready2 版本变更须逐项复核**（复核方法=reasoner-limits §六削减实验）。

## 一、引擎级 builtin 支持总则

| 引擎 | swrlb builtin 支持 | 依据 | 定位 |
|---|---|---|---|
| **Pellet 2.3.1** | ✅ 支持（字面量 argument） | 限制④（add/lessThan 字面量参数虚构载体实测全量执行成功） | `swrl_verified` 唯一来源 |
| **HermiT** | ❌ 全不支持 | 限制⑬（含 swrlb 原子加载即抛 `built-in atoms are not supported yet`，与规则条数无关） | 仅 DL 层对照（SWRL 剥离版） |

**结论**：`swrl_verified` 只能由 Pellet 给出；HermiT 档定位=DL 交叉验证（equivalentClass/disjoint/一致性），不执行任何 builtin 规则。工具链无第二 SWRL 引擎，限制⑪⑫「是否 Pellet 特有」不可对照。

## 二、builtin 类别 × Pellet 支持（实测分级）

| 类别 | builtin 例 | Pellet | 实测依据 |
|---|---|---|---|
| 比较 | equal / notEqual / lessThan / greaterThan / lessThanOrEqual / greaterThanOrEqual | ✅ 实测 | 限制④⑬（lessThan/greaterThan/equal 虚构+真实载体实测） |
| 算术·add | add | ✅ 实测 | 限制④（add 字面量参数实测） |
| 算术·其他 | subtract / multiply / divide / mod / pow / abs / ceil / floor / round | ⚠️ 未实测 | 标准 swrlb 定义存在，本工具链未逐项验证 |
| 字符串 | stringConcat / contains / startsWith / endsWith / substring / stringLength / normalize / upperCase / lowerCase / encodeForURI / replace / translate / tokenize | ⚠️ 未实测 | 同上 |
| 布尔 | booleanAnd / booleanOr / not | ⚠️ 未实测 | 同上 |
| 日期时间 | date / dateTime / yearMonthDuration / dayTimeDuration / addDayTimeDuration / addYearMonthDuration / subtractDates 等 | ⚠️ 未实测 | 同上 |
| 列表 | listConcat / listIntersection / listSubtraction / member / length / first / rest / sublist | ⚠️ 未实测 | 同上 |
| URI | resolveURI / anyURI | ⚠️ 未实测 | 同上 |

> **诚实纪律**：✅实测=本工具链 run 实证；⚠️未实测=标准 swrlb 定义存在但本工具链未逐项验证，**不作确定支持结论**——用前须削减实验实测（reasoner-limits §六）。不抄外部矩阵内容充数。

## 三、builtin 规则形态约束（与 builtin 支持正交）

builtin 支持 ≠ 规则可靠物化。含 builtin 的规则仍受以下形态约束（reasoner-limits 限制⑪⑫⑭）：

- **限制⑪**：head 多原子部分物化 → head 单原子化（双结论规则拆两条）。
- **限制⑫**：句法相同 body 去重丢弃 → 双通道 body 句法相异（主规则类原子 body + 派生规则字面量展开 body）。
- **限制⑭**：孤立单规则单值场景 builtin 数值规则 canonical 序下确定性不物化 → 多规则并发压力用例承载语义验收；孤立场景 FAIL 先跑 canonical 档两次确认确定性 + 削减实验，不盲改。

## 四、消费方

- **prompt-generator**：builtin 白名单注入（优先✅实测类；⚠️未实测类用前实测）+ 形态约束（§三）。
- **validate_ontology L2-SWRL-BUILTIN**：机械列出每规则使用的 builtin（info 级清单，供引擎兼容性审查；HermiT 档任何 builtin 均不执行）。
- **S6 --engine 对照**：HermiT 档 builtin 规则 FAIL=预期能力边界（限制⑬），非缺陷。
