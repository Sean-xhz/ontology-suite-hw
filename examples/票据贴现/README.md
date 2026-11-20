# 发行示例：票据贴现（全虚构载体）

> 三件套端到端示例：建模 8 件套 → 审阅页与意见单 → what-if 模拟 demo。
> 本体规模：10 类 / 9 对象属性 / 13 数据属性 / 5 SWRL 规则 / 15 SKOS Concept；黄金用例 16 条（100% 基线，1 条 exempt 登记）。
> **全虚构声明**：机构名/企业名/人名/数值均为虚构，与任何真实主体无关。

## 目录

| 子目录 | 内容 | 来自 |
|---|---|---|
| `建模run/` | 8 件套（ontology.ttl / 建模方案 / 29句话描述集 / 术语词典 / 缺陷报告 / 黄金用例集 / 测试报告 / run-manifest）+ 校验产物（validate/consistency/golden-cases-result/review.json）+ G1 初审 checklist + S5 拓扑报告 + 审阅页.html | ontology-model 端到端 run（2026-10-26/27，G3 通过） |
| `审阅与意见/` | 票据贴现_review.json（提取产物）/ 票据贴现_审阅页.html（专家审阅入口，浏览器直开）/ test-审阅意见.json + test-审阅意见单.md（批注→意见单回流格式示例） | ontology-review Phase 1 |
| `模拟demo/` | demo1-4 instance+sim-result（物化推理，demo1 含解读报告 sim-report.md）/ demo1-bad-instance.json（check_instance 闸门拦截反例）/ 票据_signature.json（编译约束签名） | ontology-simulate Phase 2 |

## 快速复现

```bash
SUITE=<本套件根目录>；EX=$SUITE/examples/票据贴现
# 审阅页：浏览器直开
open "$EX/审阅与意见/票据贴现_审阅页.html"
# 校验 + 签名 + 实例闸门
python3 $SUITE/skills/ontology-model/scripts/validate_ontology.py "$EX/建模run/ontology.ttl"
python3 $SUITE/skills/ontology-model/scripts/run_golden_cases.py "$EX/建模run/ontology.ttl" "$EX/建模run/golden-cases.json" --check
python3 $SUITE/skills/ontology-simulate/scripts/check_instance.py "$EX/模拟demo/demo1-instance.json" "$EX/模拟demo/票据_signature.json"   # exit 0
python3 $SUITE/skills/ontology-simulate/scripts/check_instance.py "$EX/模拟demo/demo1-bad-instance.json" "$EX/模拟demo/票据_signature.json" # exit 1（拦截）
# 物化推演（需 Java + Pellet）
python3 $SUITE/skills/ontology-simulate/scripts/simulate_reason.py --instance "$EX/模拟demo/demo1-instance.json" --ttl "$EX/建模run/ontology.ttl" --json-output /tmp/demo1.json
```

## A/B 实验协议

A/B 三臂实验协议（本体臂/描述集臂/裸臂 + 机械判据 + 专家盲评）见 `skills/ontology-simulate/references/ab-protocol.md`。本示例聚焦建模 → 审阅 → 模拟三件套端到端；A/B 实验材料按敏感纪律另行管理（真实业务载体盲评数字不可外发）。
