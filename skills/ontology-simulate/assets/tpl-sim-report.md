# what-if 模拟验证报告（模板）

> {{场景名}} ｜ 生成：{{日期}} ｜ ontology-simulate T5
> 本体基线：{{ontology.ttl 路径}} sha={{sha12}} ｜ 实例：{{instance.json}}

## 一、画像与诉求

> （compiler 的 scenario+query 忠实转录；画像轨道（受控真实/虚构）按 T0 登记注明，个人标识已去除）

## 二、推理结论（业务语言）

> （按诉求拆分的问题逐条作答——每条结论挂依据）

### 结论 1：{{问题}}

**{{结论表述}}**

依据链：
- 输入事实：{{instance.json 中的相关断言（业务语言）}}
- 推断事实：{{sim-result.inferred 相关三元组 → label_map 翻译}}
  - 归因：{{规则 ID+label}}（{{规则业务语义一句话}}）

## 三、推断事实清单（输入 vs 推断分层）

| # | 主体 | 推断 | 归因 | 层级 |
|---|------|------|------|------|
| 1 | indBill1 | 禁止贴现票据（NonDiscountable） | ruleR3 R3 A 级禁止贴现规则 | 推断 |
| 2 | indEnd1 → indEnd2 | 有效衔接（isUpstreamOf） | ruleR7 | 推断+闭包 |

> 输入事实（画像断言）N 条不列全表，见 instance.json。

## 四、处置档与开放世界登记

> （R3 拦截 / R5 仅登记等处置差异；AA 级未判定≠可贴现等开放世界语义——如适用）

## 五、存疑项

> （multi_rule_joint / schema_propagation / 未编译概念 / 归因降级 / label 缺口）

## 六、推理机原语数据（机械转录，防漂移）

```json
{{sim-result.json 的 inferred + attribution_summary + consistency 原文}}
```
