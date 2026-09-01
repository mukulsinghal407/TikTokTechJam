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

The 50,000-product catalog is not committed to this repo (large, read-only).
Download `catalog.jsonl.gz` from the challenge's participant kit release, verify
it, and unpack it into `data/`:

```bash
curl -L -O https://github.com/TechJam2026/techjam-conversational-search/releases/download/participant-kit/catalog.jsonl.gz
curl -L -O https://github.com/TechJam2026/techjam-conversational-search/releases/download/participant-kit/SHA256SUMS
shasum -a 256 -c SHA256SUMS --ignore-missing   # expect: catalog.jsonl.gz: OK

gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
wc -l data/catalog.jsonl                        # expect: 50000
```

`.gitignore` already excludes `data/catalog.jsonl`. `data/public_set.jsonl`
(200 labeled development sessions) is included and is all that is needed to
reproduce the numbers below; the held-out evaluation sessions are run by the
organizer.

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

Each limitation below is a deliberate scoping choice for this challenge, with the
rationale and the natural next step.

- **Lexical retrieval, no LLM semantic ranking.** Both routes are BM25 over
  SQLite FTS5. We deliberately kept the pipeline LLM-free so it is deterministic,
  free to run, and works with no network access at judging time. The clear next
  step is an in-memory dense route (a small sentence embedding, still no external
  vector DB) fused with the lexical routes.
- **Interpretable linear scorer.** `CandidateScorer` is a transparent, zero-
  dependency linear blend of retrieval relevance, explicit-evidence match, and a
  quality prior — easy to inspect and debug. A lightweight learned reranker on
  top is the natural way to push MRR further.
- **Small, deliberately constrained tuning surface.** The question policy is
  **parameter-free by design**: its attribute order follows a structural property
  of the frozen evaluator (`classify_constraint` is a fixed function) rather than
  a fitted value. Only the retrieval side carries a handful of tuned constants
  (route weights, coverage strength, uncertainty threshold). We kept the knob
  count low on purpose to limit overfit to the 200 public sessions;
  cross-validation across resampled splits is the next check.
- **Domain-specific evidence extraction.** Constraint extraction uses a
  clothing/shoes/jewelry lexicon and phrase markers, matched to this challenge's
  frozen single-category catalog. Extending to other categories would need
  additional lexicon work.
- **Template clarification questions.** The local evaluator does not read the
  natural-language `message` when scoring (verified), so question *wording* has
  no metric effect and we use fixed templates keyed by attribute. Generating
  questions from the actual candidate-pool split matters for real users and the
  demo, and is the next priority there.
- **Session-local memory.** Each session is evaluated in isolation, so there is
  no long-term profile across sessions. Cross-session profile distillation for
  returning shoppers is the extension toward Pillar III.

Given more time, our priority order would be: (1) add the dense-retrieval route
and a learned reranker, (2) cross-validate the retrieval constants across
resampled splits, (3) generate clarification questions from the live candidate
pool, then (4) cross-session profiles.

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
