# ontology-simulate CHANGELOG

> semver（MAJOR.MINOR.PATCH）：MAJOR=执行契约不兼容变更（T 阶段/闸门/A-B 协议）；MINOR=新增能力或条款；PATCH=措辞与修正。当前版本登记于 SKILL.md frontmatter `metadata.version`。子协议版本（应答契约 / 题库 schema）独立登记，不随 skill 版本联动。

## 1.2.4 (2026-11-17)
- facet 实例校验承接方注释口径修正（→ model SHACL 层 R4）；T3 三闸正交组合薄指针（check_instance JSON 零臆造 → validate_shacl TTL 数据完整性 → simulate_reason 物化）。校验/物化/归因逻辑零改动。

## 1.2.3 (2026-11-11)
- 新增 `references/ab-protocol.md`（A/B 三臂实验协议独立成文：三臂定义 / 应答契约 / 题库编制契约 / 执行纪律 / 机械判据 / 专家盲评）。

## 1.2.2 (2026-11-11)
- `extract_signature` 输出确定性（共享解析层 bnode 修复联动）：匿名 union domain/range→空串 + 结构化成员字段；signature 双跑字节一致。本 skill 脚本零改动。

## 1.2.1 (2026-11-11)
- 配套 agents 平台中立指针（`agents/README.md`）；README English Summary。

## 1.2.0 (2026-11-11)
- 三受众拆分；路径参数化（`<skill根>/scripts` 约定）；题库编制契约成文（素材白名单 / 编制分工 / gold 冲突裁定 / 冻结双哈希）；实验参数建议化（题量 10-15 / 盲评 ≥2 人）；编译双路径（自然语言→compiler agent / 结构化→主会话直构，check_instance 统一硬闸门）；frontmatter `metadata.version`。

## 1.1.0 (2026-11-10)
- 画像受控双轨（受控前提三条满足即真实案例可入模拟；个人标识去除为通用红线；对外分发产物一律虚构）；应答契约 v1.1（`simulate_reason --render-md` 业务语言确定性渲染 + 本体臂材料双轨注入 + 三臂统一表述纪律）；交付通道中立；载体中立化。

## 1.0.0 (2026-11-10)
- 首版：what-if 协议 T0-T6（签名提取→实例编译→check_instance 机械闸门→Pellet 物化〔双快照 diff 推断层 + 逐规则归因 + canonical 缓存〕→业务解读）+ SG1/SG2 停等 + 沙箱零回写；A/B 三臂实验协议（本体臂/描述集臂/裸臂 + ab_score 机械判据 + 专家盲评聚合 + AG2 终审）。
