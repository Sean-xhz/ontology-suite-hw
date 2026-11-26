# ontology-model CHANGELOG

> semver（MAJOR.MINOR.PATCH）：MAJOR=执行契约不兼容变更（Stage/闸门/交付契约）；MINOR=新增能力或条款；PATCH=措辞与修正。当前版本登记于 SKILL.md frontmatter `metadata.version`。子协议版本（golden-cases / shapes / query-templates / patch schema、SWRL 规范）独立登记，不随 skill 版本联动。

## 1.14.2 (2026-11-26)
- 删除未接线的 expand_affected 死代码；新增 model 内共享工具模块 _common.py（file_sha256/base_namespace/rdf_list_items/local_name 收敛，消除重复定义分叉）。跨 skill 独立实现护栏不动。
- 子协议版本不变。

## 1.14.1 (2026-11-26)
- 黄金用例 prop_value/no_prop_value 字面量回退判定；run_one 早退预置 pass 键（防崩批）；--only 未知 id exit2；CQ 预检词汇补 rdfs:Class/skos:Concept/AnnotationProperty；版本 diff 排序全 IRI 决胜；closeout 敏感扫描补 .html；退出码契约修正。
- 子协议版本不变。

## 1.14.0 (2026-11-25)
- 新增 builtin × 引擎支持矩阵（`references/builtin-engine-matrix.md`）：Pellet builtin 支持（实测分级）/ HermiT 全不支持，结构化替代散文限制条目；validate 新增 L2-SWRL-BUILTIN builtin 使用清单（info 级）。
- 子协议版本不变；限制编号①-⑭稳定。

## 1.13.0 (2026-11-25)
- 新增 CQ 结构预检（`--precheck`）：推理执行前检查用例断言词汇∈本体词汇表（缺失硬失败）+ 类间 BFS 可达（depth≤3，advisory 告警），分流结构不可达用例省推理执行。
- 子协议版本不变（黄金集 schema 1.0）。

## 1.12.0 (2026-11-25)
- 新增版本机械 diff（`diff_ontology.py`）：两版本 TTL 三元组级 added/removed/changed 对照，按类/属性/规则/Concept 四面归类，产 JSON + md 修订对照表草稿（基线迭代人工只裁定不比对）。具名构件级准确，匿名 bnode 公理噪声单列计数。
- 子协议版本不变。

## 1.11.0 (2026-11-25)
- 新增 SWRL 静态反模式 lint（L2-SWRL-LINT）：恒假自比较（死规则，error）/ 恒真自比较（冗余恒真，warning）/ DL-safe（head 变量须 body 绑定，error），机械前置拦截 LLM 编译反模式。
- 子协议版本不变。

## 1.10.0 (2026-11-20)
- 接缝契约增补（`s1-handoff-contract.md`）：§六.2 图样联合消费条款（substrate-exact 图样内嵌原图仅含关系 glyphs 时，Read 原图给关系 + substrate bbox 给节点身份，联合重建拓扑）；§1.2 保图覆盖范围澄清（raster 载体无条件保图；PPTX 原生矢量 substrate-only 档无图片载体，内容经 substrate 位置结构承载）；§九 限制登记。

## 1.9.1 (2026-11-20)
- 接缝契约一致性修正：§5.1/§七 I3 机械组装口径对齐（`assemble_pack.py` 确定性拼接，非 LLM 合并）。

## 1.9.0 (2026-11-19)
- 新增接缝契约 `references/s1-handoff-contract.md`（ingest→S1 唯一接口权威）：五类 affordance（unit_type 形态维 / 图样保真 / verification_status 置信度 / personal_info_regions 个人信息精确位 / md_heading 溯源桥接）+ S1 消费协议 §六 + 溯源链 §五。
- S1 消费协议落地（形态分派 / 图样多模态 Read / context 预算 / 溯源携带 / 置信度消费 / 精确脱敏）；`tpl-29-sentences` 增「来源」列；`prompt-generator` 全构件 provenance annotation（rdfs:isDefinedBy/skos:note）；`tpl-ontology-doc` 溯源登记位。

## 1.8.0 (2026-11-18)
- D3c SPARQL Read 查询模板库：新增 `scripts/derive_sparql.py`（TTL-direct 机械派生 7 类 SELECT 模板，纯 rdflib 内置 SPARQL 1.1，零新增依赖）+ `assets/tpl-query-templates.md`。子类闭包 property path / derived 类分流 / 参数化 + IRI 守卫。
- 子协议：query-templates schema 1.0 / derivation-report 1.0。CLI +`model queries`。

## 1.7.1 (2026-11-18)
- 上游进料指针：S0 入口 (a) + 资产索引增 ontology-ingest（异构文档→萃取原料包→S1）。

## 1.7.0 (2026-11-17)
- R4 SHACL 约束校验层：新增 `scripts/derive_shacl.py`（TTL→SHACL shapes 派生，纯 rdflib）+ `scripts/validate_shacl.py`（pyshacl 实例级数据完整性）+ `assets/tpl-shacl-shapes.md`。封闭世界数据完整性补 OWL 开放世界盲区（facet/基数/枚举/hasKey）。
- 子协议：shapes schema 1.0 / derivation-report 1.0 / violations-report 1.0。pyshacl==0.29.1 核心依赖。CLI +`model shapes`/`shacl`。

## 1.6.0 (2026-11-17)
- R2 增量 patch 引擎：新增 `scripts/incremental_patch.py`（结构化编辑操作 JSON→draft TTL + patch-report，纯 rdflib 核心）+ `assets/tpl-patch-schema.md`。8 操作目录 / L1-L2 零新增 error 闸门 / 黄金用例回归守护 / 语义版本 diff（PATCH/MINOR/MAJOR）。
- 子协议：patch JSON schema 1.0 / report 1.0。CLI +`model patch`。

## 1.5.0 (2026-11-12)
- 新增盲测还原率对照报告模板 `assets/tpl-restoration-report.md`；`reasoner-limits` §七 引擎限制归因三分类（绑定/序列化层 / 引擎实现缺陷 / 引擎能力边界）+ 升级纪律；交付分级纪律浓缩入 manifest 收卷清单。

## 1.4.2 (2026-11-11)
- S6 实例级推理执行纪律浓缩为单一执行块（机制自包含于 `reasoner-limits` 限制⑩⑭）。

## 1.4.1 (2026-11-11)
- 双模型异构纪律平台中立化（生成/审计须不同模型，禁同模型自审；模型别名降参考实现注记）；README English Summary。

## 1.4.0 (2026-11-11)
- 新增 `references/reasoner-limits.md`（引擎限制①-⑭ + 削减实验矩阵 + 三级降级链 + L2/L3 分工，自包含）；run 根三级路径解析（调用传入 > `ONTOLOGY_RUNS_ROOT` > 部署默认）；7 类语义覆盖矩阵（编译进 TTL / md 扩展位 / 不承接）；frontmatter `metadata.version`。

## 1.3.0 (2026-11-10)
- 新增 `references/methodology-core.md`（方法论判据自包含内核，源自《本体驱动的AI数据管理》公开方法论）；`structured-input-mapping` 通用四步法；盲测重定位为辅助验证模式（非默认路径）；交付通道中立。

## 1.2.0 (2026-11-10)
- 载体中立化（description 泛化为业务场景；敏感纪律措辞泛化，纪律本体保留；模板配例虚构中性）。

## 1.1.0 (2026-11-03)
- SWRL 编译形态约束（head 单原子化 + 双通道标准形态）；canonical 确定性档（`canonicalize_base` 内置）；基线迭代入口 (b) 变体；run 目录三区结构 + 呈报件规范 `tpl-gate-submission`；收卷三步 + `closeout_check.py`（齐套 + 敏感扫描 + 计数一致）；`tpl-production-handoff`；`structured-input-mapping`。

## 1.0.0 (2026-10-27)
- 首版：S0-S6 管线 + G1-G3 人工闸门 + 双模型异构质检（generator/auditor，四元组缺陷报告，博弈 ≤3 轮）+ L1-L3 机械校验 + 黄金用例业务验收（80%→90%）；8 件套交付；`scripts/run_golden_cases.py`（用例外置 golden-cases.json schema 1.0）。
