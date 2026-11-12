# 审阅意见单（opinion schema 与消费契约）

> 本文件是 ontology-review 意见回流的数据契约。页面导出的 `审阅意见.json` 机械消费，人读版本由 ingest_opinions.py 生成 `审阅意见单.md`（G1/S2 与入口 (c) 的消费格式）。

## 一、意见 JSON schema（页面导出，唯一数据源）

```json
{
  "export_date": "ISO8601 时间戳",
  "run_dir": "本体 run 目录（来源基线）",
  "baseline": {"ttl": {"path": "ontology.ttl", "sha": "提取时哈希"}},
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
      "ts": "提交时间戳"
    }
  ]
}
```

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
2. 意见**不改本体文件**——一切形式化修改走入口 (c) 管线（专家做业务裁量、LLM 编译、闸门仲裁，与 ontology-model 哲学一致）
3. 导出 JSON 与 md 双载体（JSON 机械消费+md 人读）——schema 先例同 tpl-golden-cases §5
4. 敏感纪律：意见原文若含真实人名/机构/参数，ingest 时如实登记并由用户裁定脱敏（不静默过滤）
