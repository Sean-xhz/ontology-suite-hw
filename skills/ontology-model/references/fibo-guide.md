# FIBO 金融行业本体对接指南

> **用途**：S3 生成阶段的金融域公共层参考——金融场景建模优先复用 FIBO 既有类与惯例，避免重复发明金融通用概念。
> **仓库**：[edmcouncil/fibo](https://github.com/edmcouncil/fibo)（EDM Council 维护，金融行业事实标准本体）；在线浏览：`https://spec.edmcouncil.org/fibo/ontology`。
> **纪律**：MVP 不联网解析 owl:imports（机械校验只查 IRI 格式）；复用 FIBO 类时须在建模方案文档登记来源 IRI；不得修改 FIBO 原类名。

## 一、模块层级地图

依赖方向单向自底向上（下层不 import 上层）：

```
FND  基础层（Agreements/Parties/DatesAndTimes/Law/Quantities…——任何金融概念的根基）
 └─ BE  法律实体层（LegalEntities/Corporations/OwnershipAndControl——公司与股权）
     └─ FBC  金融商务层（DebtAndEquities/FinancialInstruments/ProductsAndServices/Markets）
         └─ 领域层：LOAN(贷款) / SEC(证券) / DER(衍生品) / IND(指标：利率汇率) /
                    CAE(公司行动) / MD(市场数据) / BP(业务流程) / ACTUS(现金流合约) / EXMP(示例)
```

实测惯例：`LOAN/LoansGeneral/Loans.rdf` 的 owl:imports 全部指向 FBC/FND + OMG Commons（上层本体注解词汇），不反向依赖。

## 二、借贷域可复用类清单示例（实测样例——仅此域预置）

> 本清单为借贷域实测样例（供首个金融场景对齐参考）；**其他域不预置类清单**，按 §四 检索方法现查现用，防止清单过时与领域偏见。

**FBC/DebtAndEquities/Debt.rdf**（57 类，核心）：
- 合约与设施：`CreditAgreement`（及子类 RepaidAtMaturity/RepaidPeriodically）、`CreditFacility`（Committed/Uncommitted/Retail）、`RevolvingLineOfCredit`、`Debt`
- 角色：`Debtor`/`Creditor`/`Lender`/`Borrower`
- 担保与偿付：`Collateral`、`Amortization`、`InterestPaymentTerms`

**LOAN/LoansGeneral/Loans.rdf**（核心）：
- `Loan`、`SecuredLoan`/`UnsecuredLoan`/`GuaranteedLoan`/`CollateralizedLoan`
- `ClosedEndCredit`/`OpenEndCredit`、`LoanToValueRatio`、`Servicer`、`PaymentHistory`

**LOAN 子模块**：`LoanApplications`（申请）/`LoanEvents`（贷后事件）/`LoansRegulatory`（监管口径）/`RealEstateLoans`（不动产贷款）。

## 三、引用与映射惯例（FIBO 官方 ONTOLOGY_GUIDE 实测）

| 意图 | 惯例 | 示例 |
|---|---|---|
| 直接复用 FIBO 类（领域类是其特化） | `owl:imports` 模块 IRI + `rdfs:subClassOf` 指向 FIBO 类 | 领域类「银税贷产品」⊑ fibo `Loan` |
| 仅术语对齐（同义/近义，不继承语义） | `skos:exactMatch`/`skos:broadMatch`（**仅属性级**，class 复用不走 skos） | 本地术语「授信额度」≈ fibo `CreditFacility` 相关概念 |
| IRI 规范格式 | `https://spec.edmcouncil.org/fibo/ontology/<域>/<模块>/<类名>` | `.../FBC/DebtAndEquities/Debt/CreditAgreement` |
| 版本引用 | Production=季度版（经 SME 审查+hygiene 测试），Development=随 commit 实时；版本化浏览加 `?version=2026Q2` 类查询参数 | 建模方案登记所用版本号 |

**分层落位建议**（公共-领域-实例三层）：FIBO 对齐物放**公共层**（金融通用概念）；场景特异概念放**领域层**（subClassOf 或 skos 映射挂接 FIBO）；具体产品/客户放**实例层**（新增产品只实例化）。

## 四、其他金融域的检索方法

1. 定位域目录：仓库根下大写目录名即域名（保险相关概念分散于 `FBC/ProductsAndServices`〔保险产品〕与 `BE/LegalEntities`〔保险人角色〕，无独立 INS 域——需组合检索）
2. 在线检索：`https://spec.edmcouncil.org/fibo/ontology` 搜索类名/关键词（支持中英文标签检索）
3. 仓库检索：GitHub 代码搜索 `repo:edmcouncil/fibo <关键词>`，或用 GitHub API 拉取目标 .rdf 文件解析 `owl:Class` 声明
4. 登记：复用的每个 FIBO 类在建模方案文档「公共层对齐表」登记：本地概念 | FIBO 类 IRI | 映射方式（subClassOf/skos:exactMatch/skos:broadMatch）| 理由

## 五、工具链惯例（FIBO 社区）

| 工具 | 用途 | 本 skill 采用 |
|---|---|---|
| Protégé | 图形编辑+导入验证器（FIBO 官方编辑工具；书中纪律：不作主建模工具，仅作导入验证） | S5 可选（无环境走 report_topology.py 降级） |
| SPARQL hygiene 测试 | FIBO CI 质量测试（`etc/testing/hygiene_parameterized/`） | 参考其检查思路，L2 脚本已覆盖核心项 |
| HermiT reasoner | DL 一致性检查（FIBO CI 标配；全量 DL 推理耗时长为已知挑战） | L3（owlready2 内置调用） |
| ROBOT | merge/reason/report——应用本体裁剪 | 可选增强（未装，MVP 不依赖） |
| pySHACL | 实例数据形状校验 | 可选增强（实例层数据校验时再装） |
