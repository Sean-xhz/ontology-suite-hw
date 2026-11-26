# ontology-ingest CHANGELOG

> semver（MAJOR.MINOR.PATCH）：MAJOR=执行契约不兼容变更（I 阶段/闸门/喂入契约）；MINOR=新增能力或条款；PATCH=措辞与修正。当前版本登记于 SKILL.md frontmatter `metadata.version`。子协议版本（pack schema / page-transcribe schema）独立登记，不随 skill 版本联动。

## 2.2.2 (2026-11-26)
- --doc-id 路径净化（统一过 sanitize + strip 防 .. + 包目录 realpath 包含守卫，防目录逃逸）。
- pack schema 不变。

## 2.2.1 (2026-11-20)
- 登记 PPTX 原生矢量图样保图边界（parsing-limits ⑱）；零解析行为变更。

## 2.2.0 (2026-11-20)
- 新增 I3 机械组装（`scripts/assemble_pack.py`）：每源件单一合并 md，机械保证按 manifest 序拼接 / 不丢弃 / 图嵌守恒 / 清洁无机器锚 / source.sha 零回写。

## 2.1.0 (2026-11-19)
- 接缝契约（model 侧 `s1-handoff-contract.md` 接口权威）：五类 affordance——unit_type 形态维 / 图样保真（嵌原图 + 图内文字照录）/ verification_status 置信度 / personal_info_regions 个人信息精确位 / md_heading 溯源桥接，萃取就绪保真。
- 子协议：pack schema 2.1 / page-transcribe 1.1。

## 2.0.0 (2026-11-19)
- LLM 整页布局感知转录为主路径 + 机械护栏（渲染 / inventory / substrate / 完整性交叉校验）；清洁 markdown（机器元数据全入 manifest）；任何视觉单元必过 LLM，无静默 mechanical-only 跳过。
- 渲染层 pypdfium2（PDF→页图）+ LibreOffice 可选（office→PDF）；DOCX/XLSX 原生结构化 substrate 优先（直抽比 OCR 更准）。
- 子协议：pack schema 2.0 / page-transcribe 1.0。

## 1.0.0 (2026-11-18)
- 首版：五格式机械解析（PDF/DOCX/XLSX/PPTX/图片）+ vision agent 识图 + 萃取原料包（保真 MD + canonical manifest + attachments）；I0-I3 管线 + IG1 轻停等闸门；解析层照录不脱敏（脱敏在 model S1→S2）。
- 子协议：pack schema 1.0 / vision-extract 1.0。
