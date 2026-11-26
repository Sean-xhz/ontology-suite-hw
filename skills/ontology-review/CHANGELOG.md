# ontology-review CHANGELOG

> semver（MAJOR.MINOR.PATCH）：MAJOR=执行契约不兼容变更（R 阶段/闸门/回流契约）；MINOR=新增能力或条款；PATCH=措辞与修正。当前版本登记于 SKILL.md frontmatter `metadata.version`。子协议版本（review.json / 意见 JSON / 页 PAGE_SCHEMA / patch schema）独立登记，不随 skill 版本联动。

## 1.3.5 (2026-11-26)
- E13 批注锚点测试补格式有效性+负例判别（消除自证恒真）；E14 D4 导出契约动态选靶（去 fixture 硬编码，carrier-neutral）。
- 子协议版本不变。

## 1.3.4 (2026-11-26)
- E12 bnode 正则补 N+32hex/cb 格式；plain_swrl 角色消歧 >5 同角色降级数字后缀防越界；base_ns 回退去 example 魔数（通用载体 base 推断）。
- 子协议版本不变。

## 1.3.3 (2026-11-26)
- merge 函数拆分（抽 _collect_derived_mentions/_axiom_md_overlay 纯子块，210→151 行）+ 入参突变契约 docstring 明示。review.json 输出字节不变。
- 子协议版本不变。

## 1.3.2 (2026-11-26)
- 修复专家审阅页存储型 XSS（SWRL 原子 predicate/arguments + 实体表列头转义）；冻结审阅页维护批次再生（3 页字节全等，signature 零影响）；退出码契约修正。
- 子协议版本不变。

## 1.3.1 (2026-11-20)
- engine 修正：`review_extract` 提取的 `meta.run_dir` 取 basename 归一化，杜绝绝对本地路径进入意见单导出与浏览器 localStorage key；消费端全兼容，提取 DATA 零变更。
- 子协议版本不变（review.json 1.1 / 意见 JSON 1.1 / PAGE_SCHEMA 1.1 / patch schema 1.0）。

## 1.3.0 (2026-11-18)
- D2 六板块图示：类继承树 / 属性域值域图（union 枢纽）/ 公理约束图 / 规则流图 / SKOS 层级图 / 批注跨图锚点；每图配 print 回退边表。
- D4 编辑模式（L1-L2 TBox）：label/comment/oneOf 受控值编辑 + subClassOf 拖拽重父 + domain/range 双下拉；导出 `d4-patch.json`（内容哈希 patch_id）交 model R2 引擎执行；patch-report 回读（文件类型守卫）。
- R1 supply 供给层（review.json schema 1.1）：iri_map/literal_meta/enum_literals/axiom_graph 等确定性供给字段（signature 白名单投影零漂移）。
- self_test E11-E14（规则流 atom_meta / 公理 SKOS union / 批注锚点 / D4 导出契约）。
- 子协议：review.json 1.1 / 意见 JSON 1.1（anchor）/ PAGE_SCHEMA 1.1 / patch schema 1.0。

## 1.2.4 (2026-11-12)
- 受控目录表述泛化（不暴露本地目录结构）。

## 1.2.3 (2026-11-11)
- 新增 `references/presentation-discipline.md`（R2 呈现纪律五组条款独立成文，编号稳定）。

## 1.2.2 (2026-11-11)
- `parse_ttl` 确定性修复：具名字段只承载具名 IRI，匿名表达式→空串 + 结构化成员字段（domain_union/range_union）；rules.variables 改真实变量名（? 前缀）；输出禁含 bnode 随机标签，双跑字节一致。

## 1.2.1 (2026-11-11)
- vendor 合规：dagre/cytoscape-dagre 补注 MIT 许可头（原始字节未改）+ `assets/vendor-LICENSES.md` 版本锁定；许可头随单文件 HTML 分发。README English Summary。

## 1.2.0 (2026-11-11)
- 三受众拆分（SKILL 执行契约 / README 人类手册 / CHANGELOG 版本历史）；R1 选型硬门禁四条凝练；R2 呈现纪律规范化（编号稳定）；路径参数化（self_test `--runs`/`ONTOLOGY_SELFTEST_RUNS` 显式传入，无隐式默认）；frontmatter `metadata.version`。

## 1.1.0 (2026-11-10)
- 交付通道中立；载体中立化清理。

## 1.0.0 (2026-11-10)
- 首版：R0-R5 管线（`review_extract` 双源解析〔TTL 结构权威 + md 专家语言层〕→ `build_review_page` 七区单文件审阅页〔cytoscape 图示 + 规则双通道 + 批注 UI，浏览器直开零依赖〕→ AG1 专家审阅停等 → `ingest_opinions` 意见单 → 双通道回流）；self_test E1-E10。
