# 审阅意见单

> 生成：ingest_opinions.py（忠实转录，无改写）
> 导出时间：2026-11-04 15:00:00 ｜ 本体基线：ontology.ttl sha=abc123def456
> 意见条数：2（严重 1 / 重要 0 / 建议 1）
> 消费契约：`assets/tpl-opinion-schema.md`（通道映射 §二）

## 严重（1 条）——建议通道：入口 (c)（本轮重编译：generator 修订→机械校验→审计）

### [推导规则] R3 A 级禁止贴现规则（ruleR3 · 规则）

**意见**：A 级票据在我行业务里允许贴现但需线下审批加签，不是一律禁止——规则结论过严。

**建议修改**：改为「A 级需人工加签后可贴现」，结论类换成 ConditionalDiscountable。

<small>提交：2026-11-04 14:50:00</small>

## 建议（1 条）——建议通道：下轮 G1/S2 消费（下次 run 修订）

### [类] 持票人（Holder · 类）

**意见**：持票人角色描述未提「委托代收」场景，术语表里应补同义词。

<small>提交：2026-11-04 14:52:00</small>

## 意见 JSON（机械消费源，防转录漂移）

```json
[
 {
  "target": "rule:ruleR3",
  "kind": "rule",
  "id": "ruleR3",
  "label": "R3 A 级禁止贴现规则",
  "locate": "规则",
  "opinion": "A 级票据在我行业务里允许贴现但需线下审批加签，不是一律禁止——规则结论过严。",
  "suggest": "改为「A 级需人工加签后可贴现」，结论类换成 ConditionalDiscountable。",
  "severity": "严重",
  "ts": "2026-11-04T14:50:00+08:00"
 },
 {
  "target": "class:Holder",
  "kind": "class",
  "id": "Holder",
  "label": "持票人",
  "locate": "类",
  "opinion": "持票人角色描述未提「委托代收」场景，术语表里应补同义词。",
  "suggest": "",
  "severity": "建议",
  "ts": "2026-11-04T14:52:00+08:00"
 }
]
```
