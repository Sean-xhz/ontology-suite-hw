# Ontology Capability Suite

> Automated business ontology modeling → visual expert review → simulation & A/B empirical validation.
> A three-skill suite, carrier-neutral (applicable to any industry domain).
> 中文文档：[README.md](README.md) ｜ Frozen snapshot v8 (2026-11-12).

## What this is

A reproducible, auditable pipeline that turns natural-language business knowledge into a
W3C-compliant ontology (RDF/OWL/SKOS/SWRL, Turtle output), makes it reviewable by business
experts with zero engineering background, and empirically validates what the formalization
actually buys you — instead of trusting LLM improvisation.

| Skill | What it does | Pipeline |
|---|---|---|
| **ontology-model** | "7+1" 29-sentence description set → W3C-compliant TTL ontology | S0-S6 stages + G1-G3 human gates + heterogeneous dual-model QA (generator/auditor on different models) + L1-L3 mechanical validation + golden-case business acceptance; 8-piece delivery |
| **ontology-review** | Modeling output → single-file HTML review page for business experts | Dual-source extraction (TTL authoritative + scheme md expert-language layer) → offline cytoscape page (class graph + dual-channel rules + annotation UI) → expert opinions JSON → mechanical feedback into modeling |
| **ontology-simulate** | Expert-reviewed ontology → what-if materialization + three-arm A/B experiment | Profile + request → compliant instance compilation (zero-fabrication gate) → Pellet materialization (inferred-layer isolation + per-rule attribution) → business-language interpretation; A/B: ontology arm / description-set arm / bare arm + mechanical scoring + expert blind review |

Five agents (`agents/`) ship as a **Claude Code reference implementation**; the script layer is
platform-agnostic. The generator/auditor heterogeneity discipline (two different models, no
self-review) is platform-neutral — see [agents/README.md](agents/README.md) for adaptation.

## Quickstart

```bash
# 1. Bootstrap: check python3/pip/Java/node, install dependencies, run full acceptance
bash scripts/bootstrap.sh --run-tests

# 2. Or run the acceptance battery alone (examples/ fictional carrier as fixture)
python3 scripts/run_suite_tests.py            # T0-T10, exit 0 = all pass
python3 scripts/run_suite_tests.py --skip-java  # no-Java environment (T8 registered SKIP)

# 3. Open the example review page in any browser (offline, zero dependencies)
#    examples/票据贴现/建模run/审阅页.html
```

Each skill is driven by its `SKILL.md` execution contract (LLM orchestration entry) with
`README.md` as the human manual. Iterable domain specifications live in each skill's
`references/` (stable clause numbering — iteration happens there, not by accreting clauses in
SKILL.md); `CHANGELOG.md` is the build archive. Trigger in Claude Code: `/ontology-model`, `/ontology-review`,
`/ontology-simulate`. Standalone deployment: keep the three skills sibling-level (cross-skill
relative imports) and point `ONTOLOGY_RUNS_ROOT` at your run directory.

## Environment

- **python3 ≥3.9** + `rdflib` + `owlready2` (see `requirements.txt`; owlready2 pinned to 0.51 —
  engine behavior is registered against that version)
- **Java**: Pellet requires **≥25**; HermiT requires ≥17 (L3 consistency & SWRL materialization;
  jars ship inside the owlready2 pip package). Without Java, scripts degrade to L2 and register
  the downgrade — L1/L2 and most acceptance items still run.
- **node** (optional): only the review `self_test.py` E9 template-JS syntax check; degrades to skip.
- Engine limitations, the three-level reasoner downgrade chain, and the SWRL writing spec:
  `skills/ontology-model/references/reasoner-limits.md`.

## Repository layout

```text
.
├── skills/            # three skills (SKILL.md contract + README manual + CHANGELOG archive
│                      #   + assets/references/scripts)
├── agents/            # five agent definitions (Claude Code reference implementation) + adaptation guide
├── examples/票据贴现/  # fully fictional bill-discounting carrier: modeling run + review + simulation demos
├── scripts/           # bootstrap.sh (environment) + run_suite_tests.py (unified acceptance, N5)
├── requirements.txt   # Python dependencies (pinned/verified)
├── docs/              # GitHub Pages site (landing page + live review-page demo)
├── .github/workflows/ # CI matrix (tests.yml) + Pages deploy (pages.yml) — activates on release
├── LICENSE            # MIT
└── THIRD-PARTY-LICENSES.md  # bundled JS libraries (MIT) + pip dependency license notes
```

## Testing

`scripts/run_suite_tests.py` orchestrates the full acceptance battery (T0-T10) against the
fictional example carrier: py_compile, review self-test (E1-E10), golden-case schema, L1/L2
validation, signature full-equality + double-run determinism, instance gate positive/negative,
cross-skill imports, Pellet
materialization (inferred triples + rule attribution + zero-writeback hash assertion), closeout
sensitive scan, and the brand-name contract. All outputs land in a temporary directory —
`examples/` is read-only. CI (`.github/workflows/tests.yml`) consumes the same entry.

## Sensitive-data discipline (red lines)

1. `examples/` contains only a **fully fictional** carrier. Artifacts from real business runs
   never enter this suite and are never distributed.
2. Skill/agent assets never contain real business data or personal names; template examples are
   fictional and neutral.
3. The suite ships no API credentials. Run `closeout_check.py` sensitive scan before any
   external distribution.

## License & acknowledgments

- Suite code: **MIT** ([LICENSE](LICENSE)).
- Bundled JS libraries (cytoscape.js / dagre / cytoscape-dagre): MIT, with license headers
  embedded in every generated review page — see [THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md)
  and `skills/ontology-review/assets/vendor-LICENSES.md` (version locks & hashes).
- Methodology source: the modeling methodology kernel
  (`skills/ontology-model/references/methodology-core.md`) is derived from the public methodology
  of 《本体驱动的AI数据管理》 (*Ontology-Driven AI Data Management*, by its editorial group),
  distilled and recompiled into self-contained execution criteria with per-item source annotations.
  No book text is reproduced in this suite.
