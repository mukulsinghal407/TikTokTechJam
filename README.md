# 4. Shopping Copilot "TikTalk": AI Conversational Search and Recommendations

TikTok TechJam 2026 · Track 4: Shopping Copilot

A conversational shopping agent that recovers a customer's hidden target product
within at most 10 turns by asking useful clarification questions and re-ranking a
frozen Amazon catalog after every message.

## Project Overview

Traditional e-commerce search matches keywords and ignores how buying intent
shifts mid-conversation. This agent treats each session as an evolving belief
about one shopper: it extracts typed constraints from every message, retrieves
candidates on multiple lexical routes, scores them against the accumulated
evidence, and — only when the candidate pool is still too broad — asks one
targeted question instead of returning a noisy list.

The agent runs entirely in-memory on the Python standard library (SQLite FTS5 for
retrieval). It uses **no LLM API and reports zero tokens**, so it is fully
reproducible and free to run.

### Results (200 public sessions, official evaluator)

| System | TechnicalScore | Hit Rate@10 | MRR | MTTC |
|---|---|---|---|---|
| Weak BM25 baseline (`docs/baseline_results.json`) | 0.1067 | 0.125 | 0.068 | 9.81 |
| **This agent** (`starter/agent.py`) | **0.8658** | **1.000** | **0.666** | **2.70** |

`TechnicalScore = 0.50 · HitRate@10 + 0.30 · MRR + 0.20 · Efficiency`,
`Efficiency = clip((11 − MTTC) / 10, 0, 1)`.

### How it works

`starter/agent.py` is a thin facade that orchestrates five modules, mapping onto
the four challenge pillars:

| Pillar | Module | Role |
|---|---|---|
| I. Intent routing & hybrid pipeline | `starter/intent/evidence_extractor.py` | Regex + ontology extraction of typed constraints (category, material, color, size, style, brand, budget, feature, use_case) and no-preference / replacement markers |
| | `starter/retrieval/candidate_retriever.py` | Two-route BM25 over SQLite FTS5 (active-term route + category route), turn-to-turn carry-over, and exposure suppression of already-shown items |
| | `starter/ranking/scorer.py` | Linear blend of retrieval relevance, explicit-evidence match, and a quality prior |
| II. Multi-turn dialog strategy | `starter/intent/state_manager.py` | Incremental slot accumulation; on intent override, erases superseded evidence and rewrites the goal |
| | `starter/dialogue/question_policy.py` | Open-first then depth-gated clarification; sticky follow-up; catalog-guarded so it only asks when a question actually splits the candidate pool |
| III. Self-evolution / dynamic context | `starter/intent/belief.py` | Active-evidence belief state and an intent-uncertainty signal derived from dialog history |
| | `starter/ranking/selector.py` | Risk-aware coverage portfolio: widens the Top-K to hedge when intent uncertainty is high, tightens it when the belief is sharp |
| IV. Evaluation | `evaluator/local_evaluator.py` | Unmodified official simulator and scorer |

## Setup and Installation

Python 3.10 or later (tested on 3.14). No third-party packages — the agent and
evaluator use only the standard library.

```bash
git clone <this-repo-url>
cd TikTokTechJam
git checkout semifinal
```

### Download the catalog

The frozen 50,000-product catalog is **not** committed to this repo (it is large
and read-only). Download it from the official **Participant Kit** release:

> https://github.com/TechJam2026/techjam-conversational-search/releases/tag/participant-kit

That release is the single source of the final, frozen competition data. It
contains three assets:

| Asset | What it is |
|---|---|
| `catalog.jsonl.gz` | The 50,000-product frozen catalog (Amazon Reviews 2023, `Clothing_Shoes_and_Jewelry`), gzip-compressed (~19 MB; ~58 MB unpacked) |
| `SHA256SUMS` | SHA-256 checksums for `catalog.jsonl.gz` and `techjam-participant-kit.zip` |
| `techjam-participant-kit.zip` | The full kit (catalog + starter package + checksums) as one archive |

You only need `catalog.jsonl.gz`. From the repo root:

```bash
# 1. Download the catalog and the checksum file
curl -L -O https://github.com/TechJam2026/techjam-conversational-search/releases/download/participant-kit/catalog.jsonl.gz
curl -L -O https://github.com/TechJam2026/techjam-conversational-search/releases/download/participant-kit/SHA256SUMS

# 2. Verify the download BEFORE unpacking (checksum is on the .gz, not the .jsonl)
shasum -a 256 -c SHA256SUMS --ignore-missing
#   expected: catalog.jsonl.gz: OK
#   (07fd142631fd6b03e2b4d09988c3eb7d53720e9d57010c79db48eeaada50a8f8)

# 3. Unpack into data/
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl

# 4. Sanity check: 50000 lines
wc -l data/catalog.jsonl
```

`.gitignore` already excludes `data/catalog.jsonl`, so it will not be committed.
`data/public_set.jsonl` (200 labeled development sessions) is the only session
data used here and **is** included in this repo. The 800 private evaluation
sessions are held by the organizer and are not needed to reproduce the numbers
below.

## Steps to Reproduce Our Results

Run the official evaluator against `starter/agent.py`:

```bash
python3 -m evaluator.local_evaluator
```

This prints the aggregate and per-scenario metrics and writes `results.json`.
Expected headline numbers:

```
sample_count                 200
hit_rate_at_10               1.0
mrr                          0.666004
mttc                         2.7
efficiency                   0.83
recommended_technical_score  0.865801
```

To score an alternative implementation without touching `starter/agent.py`:

```bash
python3 -m evaluator.run_agent starter.agent --output results.json
```

The run is deterministic; the evaluator and the public labels are unmodified from
the participant kit (`docs/competition_specification.md`,
`docs/evaluation_config.json`, `docs/agent_api_contract.json`).

## Limitations and Future Work

**Limitations**

- **Lexical retrieval only.** Both routes are BM25 / FTS5. A shopper who
  describes a product with vocabulary that never appears in its catalog text can
  be missed at the retrieval stage; Hit Rate@10 is 1.0 on the public set but this
  is the most likely place private sessions degrade.
- **Hand-tuned linear ranker.** `CandidateScorer` is a fixed linear blend. A
  learned or LLM-based reranker would likely lift MRR further.
- **Public-split tuning.** Hyperparameters (route weights, coverage strength,
  uncertainty threshold, question-policy gates) were tuned on the 200 public
  sessions. Some overfit to that split is possible.
- **Regex/ontology evidence extraction.** Constraint extraction depends on a
  clothing-domain lexicon and phrase markers; it is brittle to out-of-domain
  wording and would not transfer to another catalog without lexicon work.
- **Fixed question templates.** Clarification questions are canned strings keyed
  by attribute, not generated for the specific candidate pool.
- **Session-local memory.** There is no long-term profile that persists across
  sessions.

**What we would do with more time**

- Add an in-memory dense-retrieval route (small sentence embedding, no external
  vector DB) and fuse it with the BM25 routes.
- Replace the linear scorer with a lightweight learned reranker trained on the
  public sessions.
- Cross-validate hyperparameters instead of tuning once on the public split.
- Add cross-session profile distillation for returning shoppers.
- Generate clarification questions from the actual candidate-pool split rather
  than from templates.

## Team Contributions

Five members (anonymized).

| Members | Contribution |
|---|---|
| 3 members | Theory and statistical-model research; model review and validation |
| 1 member | Modeling |
| 1 member | Coding and implementation |

## Data Attribution

The catalog and sessions derive from the Amazon Reviews 2023 dataset (McAuley
Lab, UCSD). See `DATA_ATTRIBUTION.md` before using or redistributing the data.
