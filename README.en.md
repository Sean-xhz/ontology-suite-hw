# Ontology Capability Suite

> Heterogeneous document ingestion → automated business ontology modeling → visual expert review → simulation & A/B empirical validation. A four-skill suite.
> Carrier-neutral, applicable to any industry domain (finance, insurance, supply chain, manufacturing, etc.). 中文：[README.md](README.md)

## What this is

A **reproducible, verifiable, auditable** pipeline that turns natural-language business knowledge into a W3C-compliant ontology (RDF/OWL/SKOS/SWRL, Turtle output), makes it directly reviewable by business experts with zero engineering background, and empirically answers "how much increment does formalization actually buy" — rather than relying on LLM improvisation.

| skill | Role | Pipeline |
|---|---|---|
| **ontology-ingest** | Heterogeneous documents (PDF/image/Excel/Word/PPT) → extraction feed pack (clean faithful MD + canonical manifest + attachments), the structured front-end intake for model S1 | I0-I3: admission & sensitivity classification → I1 mechanical parsing (render/inventory/substrate, pure-pip deterministic CLI) → I2 whole-page layout-aware transcription (primary, read-only vision agent) → I3 mechanical assembly + cross-check + IG1 light human gate; the parsing layer transcribes verbatim without de-identification (de-identification stays in model S1→S2) |
| **ontology-model** | "7+1" 29-sentence description set → W3C-compliant TTL ontology | S0-S6 + G1-G3 human gates + heterogeneous dual-model QA (generator/auditor must be different models) + L1-L3 mechanical validation + golden-case business acceptance, 8-piece delivery |
| **ontology-review** | Modeling output → single-file review page readable by business experts (six graph panels + dual-channel rules + annotation + L1-L2 drag-edit) | Dual-source extraction (TTL authoritative + scheme expert-language layer + supply layer) → offline cytoscape single-file HTML → expert annotation / D4 edit exports patch → mechanical opinion-sheet feedback / patch handed to model R2 engine |
| **ontology-simulate** | Expert-reviewed ontology → what-if materialization + three-arm A/B empirics | Profile + request → compliant instance compilation (zero-fabrication gate) → Pellet materialization (inferred-layer isolation + rule attribution) → business-language interpretation; A/B: ontology arm / description-set arm / bare arm + mechanical scoring + expert blind review (AG2 final gate) |

Companion agents (`agents/`): ontology-vision-extractor (ingest I2 whole-page transcription, read-only), ontology-generator / ontology-auditor (heterogeneous dual-model QA), ontology-whatif-compiler / ontology-whatif-interpreter (simulation compilation & interpretation), ab-responder (A/B three-arm responder, arm-agnostic). The script layer is platform-agnostic; the agent layer is a Claude Code reference implementation and the heterogeneity discipline is platform-neutral — see `agents/README.md` for adaptation to other platforms.

## Quickstart

```bash
# 1. Environment bootstrap: check python3/pip/Java/node, install dependencies, run full acceptance
bash scripts/bootstrap.sh --run-tests

# 2. Or run the acceptance battery alone (examples/ fictional carrier as fixture, zero side-effects)
python3 scripts/run_suite_tests.py             # T0-T15, exit 0 = all pass
python3 scripts/run_suite_tests.py --skip-java # no-Java environment (degraded tier)

# 3. Unified CLI facade (mechanical backbone; LLM orchestration stays external)
python3 scripts/ontology_cli.py --help         # capability map: ingest / model / review / simulate / suite
python3 scripts/ontology_cli.py suite doctor   # read-only environment self-check
python3 scripts/ontology_cli.py ingest parse doc.pdf sheet.xlsx --output-dir ./pack
python3 scripts/ontology_cli.py model validate examples/票据贴现/建模run/ontology.ttl
python3 scripts/ontology_cli.py model shapes ontology.ttl --output-shapes shapes.ttl   # R4 TTL→SHACL derivation
python3 scripts/ontology_cli.py model shacl data.ttl shapes.ttl --strict               # R4 instance data-integrity
python3 scripts/ontology_cli.py model queries ontology.ttl --output-json q.json        # D3c TTL→SPARQL query-template library

# 4. Open the example review page in any browser (offline, zero dependencies)
#    examples/票据贴现/建模run/审阅页.html
```

Each skill is driven by its `SKILL.md` execution contract (LLM orchestration entry), with `README.md` as the human manual; iterable domain specifications live in each skill's `references/` (stable clause numbering — iteration happens inside the reference); `CHANGELOG.md` is the version history. Trigger in Claude Code: `/ontology-ingest`, `/ontology-model`, `/ontology-review`, `/ontology-simulate`. Standalone deployment: keep the four skills sibling-level (cross-skill relative imports) and point `ONTOLOGY_RUNS_ROOT` at your run directory.

## Unified CLI entry

`scripts/ontology_cli.py` aggregates the four skills' **deterministic mechanical scripts** into a unified command surface. The LLM orchestration layer (I0-I3 / S0-S6 pipeline, IG1 / G1-G3 / SG1-SG2 / AG1-AG2 human gates, dual-model generate-audit, vision transcription) is **not** in the CLI — it is driven by an external orchestrator; the CLI only exposes independently runnable mechanical capabilities.

```bash
python3 scripts/ontology_cli.py <group> <action> [args...]
```

| group | action | Underlying capability |
|---|---|---|
| **ingest** | `parse` | I1 heterogeneous-document mechanical parsing → extraction feed pack (pure pip; vision transcription external via vision agent) |
| **model** | `validate` / `consistency` / `topology` / `golden` / `patch` / `shapes` / `shacl` / `queries` | L1+L2 validation / L3 consistency / S5 text topology / S6 golden cases / R2 incremental patch / R4 TTL→SHACL derivation / R4 instance data-integrity / D3c TTL→SPARQL Read query-template library |
| **review** | `extract` / `page` / `ingest` / `selftest` | dual-source extraction + supply / single-file review page / opinion-sheet feedback / E1-E14 self-test |
| **simulate** | `signature` / `check` / `reason` / `ab-score` | compilation signature / instance zero-fabrication check / what-if materialization / A/B mechanical scoring |
| **suite** | `test` / `doctor` | unified acceptance battery T0-T15 / read-only environment self-check |

**Thin-dispatch discipline**: each subcommand forwards remaining args verbatim to the underlying script (subprocess) and passes exit codes through — zero behavior change, scripts still run standalone, the CLI is just a convenience facade. Script paths are relative to the suite root (`__file__` auto-locates, cwd-independent); cross-skill imports are handled by each script's own relative `sys.path` shim. Unknown group/action or missing script = exit 2.

## Repository layout

```text
.
├── skills/            # four skills (SKILL.md contract + README manual + CHANGELOG version history + assets/references/scripts)
├── agents/            # six agent definitions + README (role overview / heterogeneity discipline / platform adaptation, bilingual)
├── examples/票据贴现/  # fully fictional example carrier (distributable): modeling run + review & opinions + simulation demos
├── scripts/           # ontology_cli.py (unified CLI) + bootstrap.sh (environment bootstrap) + run_suite_tests.py (unified acceptance entry)
├── requirements.txt   # Python dependencies (exactly pinned, verified versions)
├── docs/              # GitHub Pages site (index.html landing + demo.html live review-page preview)
├── .github/workflows/ # CI matrix (tests.yml) + Pages deploy (pages.yml)
├── LICENSE            # MIT (primary license)
├── THIRD-PARTY-LICENSES.md  # third-party license summary (bundled JS libs + pip dependency notes + methodology acknowledgment)
├── README.md          # Chinese
└── README.en.md       # this file (English)
```

## Environment

- **python3 (≥3.9)** + `rdflib` + `owlready2` + `pyshacl` + the six parsing libraries `pypdf`/`pypdfium2`/`python-docx`/`openpyxl`/`python-pptx`/`Pillow` (see `requirements.txt`, exactly pinned — output byte-stability is version-sensitive, upgrades require re-running double-run determinism). One-click bootstrap = `bash scripts/bootstrap.sh`.
  - **owlready2==0.51** (engine behavior registered against that version); **pyshacl==0.29.1** (R4 SHACL layer, pure Python no Java, two orthogonal environment axes vs the Java reasoner).
  - **pypdfium2 install requires `--only-binary=:all:`** (the wheel bundles the pdfium binary, avoiding old pip selecting the sdist and triggering a download timeout).
  - **LibreOffice optional** (office→PDF full visual render enhancement, MPL-2.0 independent subprocess does not infect MIT; without it office degrades to the substrate-only pure-pip main path, which still works).
  - **Parsing-lib optionality**: if a library is missing, `ingest parse` degrades to exit 2 + a pip hint and does not block model/review/simulate (doctor optional-WARN tier). fitz/PyMuPDF is a zero-code path (AGPL, not introduced); pypdf[crypto] (AES) is an optional extra not installed by default.
- **Java** + Pellet/HermiT reasoner jars (L3 consistency & SWRL materialization; **Pellet requires Java ≥25**, HermiT ≥17; jars ship inside the owlready2 pip package). Without Java, scripts degrade to L2 and register the downgrade — delivery is not blocked; R4 SHACL and D3c SPARQL are pure Python and run without Java too. Engine versions/limits/downgrade chain: `skills/ontology-model/references/reasoner-limits.md`.
- **node** (optional, only the review `self_test.py` template-JS syntax check; missing degrades to skip).
- **CI**: `.github/workflows/tests.yml` (python 3.9/3.12 matrix × temurin Java 25 × node 20, consumes the unified acceptance entry).

## Acceptance battery

`python3 scripts/run_suite_tests.py` (T0-T15 orchestration, examples fictional carrier as fixture, all outputs land in a temporary directory zero side-effects, `--skip-java` degraded tier; exit 0/1/2). CI consumes the same entry.

| # | Item | Coverage |
|---|---|---|
| T0 | py_compile | all scripts syntax |
| T1 | review `self_test.py` | E1-E14 (E11-E14 = D2/D4 supply & export contract); `--runs` explicit, no-arg/bad-dir exit 2 |
| T2 | `run_golden_cases.py --check` | golden-case schema |
| T3 | `validate_ontology.py` | L1+L2 structural validation |
| T4 | `extract_signature.py` vs frozen signature | full JSON equality + double-run byte determinism |
| T5/T6 | `check_instance.py` positive/negative | exit 0 / exit 1 interception |
| T7 | cross-skill import | suite-internal relative import resolution |
| T8 | `simulate_reason.py` materialization (Pellet) | inferred triples + rule attribution + zero-writeback assertion |
| T9 | `closeout_check.py` | closeout completeness + sensitive scan |
| T10 | brand-name grep contract | fictional carrier 0 hits |
| T11 | `incremental_patch.py` (R2) | annotation/structural positives, L2 negative, regression flip, MAJOR-guard policy, sha mismatch, double-run determinism |
| T12 | `derive_shacl.py`+`validate_shacl.py` (R4) | derivation determinism + count anchors, conform positives, facet/cardinality/enum/hasKey negatives, check_instance complementarity dual, contract errors |
| T13 | D2/D4 review-page end-to-end | supply→page tokens, five patch classes→R2 engine, sha12/bare-literal negatives, regression-flip G1, content-hash patch_id double-run, merge+supply isolation |
| T14 | `parse_documents.py` (ingest I1) | four text formats schema + substrate/rendered, image direct-supply, contract errors, scanned-page whole-page render, double-run byte-equality, zero-writeback, boundary matrix, clean md, inventory ground truth, seam affordance prepared state |
| T15 | `derive_sparql.py` (D3c) | derivation double-run byte-equality + count anchor, prepareQuery syntax valid, graph.query execution positives, derived routing, parameterization zero leakage + IRI guard, contract errors, zero-writeback (pure rdflib built-in SPARQL 1.1, no Java) |

## License & acknowledgments

- **Primary license = MIT** (`LICENSE`).
- **Third-party licenses**: `THIRD-PARTY-LICENSES.md` (bundled JS libs cytoscape/dagre/cytoscape-dagre MIT full text, license headers travel with every single-file HTML distribution + pip dependency license notes + methodology source acknowledgment); skill-level version-lock registry = `skills/ontology-review/assets/vendor-LICENSES.md`.
- **Methodology source**: the modeling methodology kernel (`skills/ontology-model/references/methodology-core.md`) is derived from the public methodology of 《本体驱动的AI数据管理》 (*Ontology-Driven AI Data Management*, by its editorial group), distilled and recompiled into self-contained execution criteria. No book text is reproduced in this suite.

## Sensitive-data discipline (red lines)

1. `examples/` contains only a **fully fictional** carrier (bill discounting). Artifacts from real business runs **never enter this suite** and are never distributed.
2. Skill/agent assets never contain real business data or personal names; template examples are fictional and neutral.
3. The suite ships no API credentials. Run the `closeout_check.py` sensitive scan before any external distribution.
4. **D4 patches carry literal values** — a `d4-patch.json` exported from a real-carrier edit stays local (same classification as opinion JSON); distributed artifacts are always fictional.

## Known issues & follow-ups

- **ab_score enum_values key mismatch (registered, not fixed)**: `ontology-simulate/scripts/ab_score.py` reads the `enum_values` key while `extract_signature` emits `oneOf_enum` → the A/B mechanical-scoring controlled-value vocabulary is always empty. Correct fix = change one line in ab_score (a separate simulate PATCH); **do not change `oneOf_enum` to accommodate it** — that would break the frozen signature (T4) + check_instance E07 consumption.
- **D4 handle-node drag-reconnect (post-MVP)**: cytoscape 3.30 core has no edge-endpoint reconnect API; the current path is an accessible fallback dual-dropdown (click a property edge → side-panel domain/range dual-dropdowns, same semantics same ops); handle-block drag-reconnect is left to a later iteration.
- **D4 edit-level boundary**: currently L1-L2 TBox only (label/comment/oneOf controlled values/subClassOf re-parenting/domain/range); ABox instance-value editing + L3 rule editing deferred.
- **D4 offline-loop interaction gap (to be scheduled)**: under the current path, producing `patch-report.json` requires leaving the review page to run an R2 CLI command — in a real scenario the expert has only the page, no command-running environment. A later iteration moves CLI execution **inside the browser** (pyodide/WASM embedding the pure-rdflib R2 core, producing draft+report in-page so the expert never leaves; L3/golden regression still needs Java, external or degraded), weighing the tension with the single-file zero-dependency iron rule at that time. The reader already has a file-type guard: mistakenly selecting an exported `d4-patch.json` no longer renders silent `?` — it shows a "this is a patch, not a report" notice + operation preview + the CLI command to produce a report.
- **Large-graph performance (post-MVP)**: six cytoscape instances are stress-free on the fictional fixture; for real large ontologies, lazy nav initialization is optional, registered non-blocking.
- **ingest full four channels**: talk ASR / code SQL DDL / diagram / proprietary DB connectors are later extension slots (see `skills/ontology-ingest/references/parsing-limits.md`, no schedule commitment); SPARQL C/U/D (UPDATE) left to a later instantiation pipeline.
