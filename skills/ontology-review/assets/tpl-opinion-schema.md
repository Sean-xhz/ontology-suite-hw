# 审阅意见单（opinion schema 与消费契约）

> 本文件是 ontology-review 意见回流的数据契约。页面导出的 `审阅意见.json` 机械消费，人读版本由 ingest_opinions.py 生成 `审阅意见单.md`（G1/S2 与入口 (c) 的消费格式）。

## 一、意见 JSON schema（页面导出，唯一数据源；schema_version 1.1）

```json
{
  "schema_version": "1.1",
  "export_date": "ISO8601 时间戳",
  "run_dir": "本体 run 目录（来源基线）",
  "baseline": {"ttl": {"path": "ontology.ttl", "sha": "提取时哈希（12 位）"}},
  "opinions": [
    {
      "target": "kind:id[:locate]",
      "kind": "class|object_property|data_property|axiom|rule|skos",
      "id": "构件标识（类/属性 localname，公理编号如 F3/L6，规则 ruleR1）",
      "label": "构件中文名",
      "locate": "定位补充（如「公理 F 族」「规则」）",
      "opinion": "意见原文（必填）",
      "suggest": "建议修改（选填）",
      "severity": "严重|重要|建议",
      "ts": "提交时间戳（ISO，机器消费）",
      "ts_local": "北京时间字符串（人读，Asia/Shanghai；⑦c）",
      "anchor": {"graph": "classes|props|axioms|rules|skos", "element": "图内元素 id（选填，⑦d）"}
    }
  ]
}
```

**子协议版本登记（独立不联动 skill 版本）**：`schema_version` 1.0→**1.1**（1.3.0 批次）——新增可选 `anchor`（图锚点，⑦d）+ `ts_local`（双时间戳，⑦c 早已在页面实现，本批补契约登记）。**兼容**：legacy 意见 JSON 无 `schema_version`→按 1.0 消费；无 `anchor`→jumpTo 回退 DOM `cls-`/`rule-`（renderOpinions 保留）；无 `ts_local`→前端 `fmtBJ(ts)` 现算。ingest_opinions 对新字段**自动随附录透传**（零改动，无接收位需求）。`anchor.element` 取图内命名空间 id（类节点 `c:<id>`/prop 边 `e-op-<id>`/atom `a:<atom_id>`/约束 `ax:…`/skos `s:<id>`/变量 `v:<name>`），与 D2 GRAPHS 注册表对齐（presentation-discipline ⑦d）。

## 二、severity 语义与回流通道

| 级别 | 语义 | 默认回流通道 |
|---|---|---|
| 严重 | 业务错误——结论/约束与业务事实相反 | **入口 (c)**（本轮重编译：generator 修订→机械校验→审计） |
| 重要 | 语义偏差——可运行但偏离业务意图 | 入口 (c) 或下轮 G1/S2（按修订成本裁量） |
| 建议 | 优化——不阻塞交付 | 下轮 G1/S2 消费（下次 run 修订） |

## 三、审阅意见单.md（人读消费格式）

ingest_opinions.py 产出，按 severity 分组倒序（严重→重要→建议），每条含：

- 构件定位（kind/id/label）
- 意见原文
- 建议修改（如有）
- 建议通道（上表映射）

## 四、纪律

1. 意见单是**专家意见的忠实转录**——ingest 不改写、不概括、不合并（忠实性优先于可读性）
2. 意见**不改本体文件**——一切形式化修改走入口 (c) 管线（专家做业务裁量、LLM 编译、闸门仲裁，与 ontology-model 哲学一致）。**D4 拖拽编辑同口径**：D4 patch（channel=d4）产 draft 非权威，晋升仍走入口 (c) S4 审计→G2/G3→人工，本纪律对 D4 并行产物**零改动**（见 §五）
3. 导出 JSON 与 md 双载体（JSON 机械消费+md 人读）——schema 先例同 tpl-golden-cases §5
4. 敏感纪律：意见原文若含真实人名/机构/参数，ingest 时如实登记并由用户裁定脱敏（不静默过滤）。**D4 patch JSON 含字面量值→真实载体 patch 不出本地**（同意见分级，R0 敏感判定延伸，tpl-d4-patch-schema §8）

## 五、D4 并行产物（拖拽编辑，1.3.0 新增）

D4 拖拽编辑（L1-L2 TBox）产 **patch JSON**（`source.channel="d4"`），与意见单是**并行的两类产物**：

| 产物 | 性质 | 消费通道 | 契约 |
|---|---|---|---|
| 审阅意见.json | 语义批注（专家业务裁量） | ingest_opinions → 意见单.md → G1/S2/入口 (c) | 本文件 §一-四 |
| D4 patch.json | 结构化编辑意图（label/comment/受控值/继承/域值域） | 编排器跑 R2 CLI（model patch）→ draft + report → 入口 (c) S4 晋升 | `tpl-d4-patch-schema.md` |

- **两类产物互不替代**：意见=「这里业务上不对」（语义层，须 LLM 编译/人工裁量）；D4 patch=「把这个 label 改成 X」（形式层轻量编辑，R2 机械执行）。专家可同页既批注又拖拽编辑。
- **ingest_opinions 零改动**：D4 patch 不经 ingest（无接收位需求）；意见新字段 anchor 自动随附录透传。
- **draft 非权威 + 零回写**：R2 产 draft TTL + patch-report.json，baseline/golden/patch 三文件 sha 断言，输出落工作区 cwd 不进 run 目录；晋升走入口 (c)（纪律 2 同口径）。
- **敏感分级同意见**：真实载体 D4 patch 不出本地（§四.4）；配例全虚构。
