# Architecture Comparison Matrix

## Quick Visual Reference

| Rank | Architecture | Hit Rate | MRR | MTTC | Token/Turn | Setup (weeks) | Buying | Browsing | Override | Boundary | Best For |
|------|---|---|---|---|---|---|---|---|---|---|---|
| **1** | 🟡 Hybrid Retrieval | 50-60% | 0.06-0.08 | 4-5 | 200-300 | 2-3 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | **Max score** |
| **2** | 🟢 Constraint-Driven | 40-50% | 0.03-0.04 | 6-7 | 50-100 | 1-2 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **Speed + cost** |
| **3** | 🟠 Multi-Route | 45-55% | 0.04-0.05 | 5-6 | 100-200 | 2-3 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **Robustness** |
| **4** | 🔵 Dense Vectors | 30-45% | 0.02-0.04 | 7-8 | ~0 | 2-4 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | **Min cost** |
| **5** | 🔴 Knowledge Graph | 25-40% | 0.02-0.03 | 8-9 | ~0 | 4-8 | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐ | **Transparency** |
| **6** | 🟣 Two-Stage | 35-45% | 0.025-0.035 | 6-7 | 50-150 | 1-2 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | **Natural flow** |
| **7** | 🟡 Ensemble | 40-50% | 0.03-0.04 | 6-7 | 200-300 | 3-4 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | **Fallbacks** |
| **8** | 🟠 RL Policy | 25-45% | 0.02-0.035 | 6-8 | 50-150 | 4-6 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | **Learning** |
| **9** | 🟢 Few-Shot CoT | 20-40% | 0.015-0.03 | 7-8 | 250-400 | 0.5-1 | ⭐ | ⭐⭐ | ⭐⭐ | ⭐ | **Fastest MVP** |
| **10** | 🔵 Active Learn | 15-30% | 0.01-0.02 | 9+ | Varies | 3-4 | ⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ | **Post-launch** |

---

## Performance Predictions (Estimated Technical Score)

```
Technical Score = 0.50 × Hit Rate@10 + 0.30 × MRR + 0.20 × Efficiency
                  (where Efficiency = clip((11 - MTTC) / 10, 0, 1))

Baseline (BM25):     0.107 (12.5% hit, 0.068 MRR, 9.81 MTTC)

#1  Hybrid:          0.55-0.70  (50-60% hit, 0.06-0.08 MRR, 4-5 MTTC)  ← 5-6x better
#2  Constraint:      0.40-0.50  (40-50% hit, 0.03-0.04 MRR, 6-7 MTTC)  ← 3.7-4.7x better
#3  Multi-Route:     0.45-0.55  (45-55% hit, 0.04-0.05 MRR, 5-6 MTTC)  ← 4.2-5.1x better
#4  Dense:           0.30-0.45  (30-45% hit, 0.02-0.04 MRR, 7-8 MTTC)  ← 2.8-4.2x better
#5  Knowledge Graph: 0.25-0.40  (25-40% hit, 0.02-0.03 MRR, 8-9 MTTC)  ← 2.3-3.7x better
#6  Two-Stage:       0.30-0.45  (35-45% hit, 0.025-0.035 MRR, 6-7 MTTC)← 2.8-4.2x better
#7  Ensemble:        0.35-0.50  (40-50% hit, 0.03-0.04 MRR, 6-7 MTTC)  ← 3.3-4.7x better
#8  RL Policy:       0.25-0.45  (25-45% hit, 0.02-0.035 MRR, 6-8 MTTC) ← 2.3-4.2x better
#9  Few-Shot CoT:    0.20-0.40  (20-40% hit, 0.015-0.03 MRR, 7-8 MTTC) ← 1.9-3.7x better
#10 Active Learn:    0.15-0.30  (15-30% hit, 0.01-0.02 MRR, 9+ MTTC)   ← 1.4-2.8x better
```

---

## Cost Breakdown (Approximate)

### LLM Token Cost (per turn, averaged)
```
#4, #5: 0 tokens (embedding-only)
#2, #6, #8: 50-150 tokens
#3: 100-200 tokens
#1, #7: 200-300 tokens
#9: 250-400 tokens (highest)
#10: Highly variable
```

### Implementation Effort (days)
```
#9: 3-5 days (few-shot prompting)
#2, #6: 7-14 days (rule-based)
#1, #3: 14-21 days (integration)
#4: 14-28 days (vector DB setup)
#10: 21-28 days (experimentation)
#7, #8: 28-42 days (complex tuning)
#5: 28-56 days (data engineering)
```

### Team Size Recommendations
```
#9: 1 person (just prompt engineering)
#2, #6: 1-2 people (engineering + tuning)
#1, #3, #4: 2-3 people (systems integration)
#8, #7: 3-4 people (ML expertise required)
#5: 3-5 people (data engineering + implementation)
```

---

## Scenario Performance (% hit rate by scenario type)

| Architecture | Buying (40%) | Browsing (40%) | Override (15%) | Boundary (5%) | Weighted Avg |
|---|---|---|---|---|---|
| #1 Hybrid | 65% | 50% | 45% | 40% | 55% |
| #2 Constraint | 70% | 30% | 40% | 35% | 45% |
| #3 Multi-Route | 70% | 40% | 50% | 45% | 50% |
| #4 Dense | 30% | 50% | 20% | 45% | 37% |
| #5 Knowledge Graph | 50% | 20% | 25% | 20% | 32% |
| #6 Two-Stage | 50% | 35% | 30% | 35% | 40% |
| #7 Ensemble | 55% | 40% | 40% | 40% | 45% |
| #8 RL Policy | 50% | 40% | 35% | 30% | 41% |
| #9 Few-Shot CoT | 35% | 30% | 25% | 20% | 30% |
| #10 Active Learn | 30% | 25% | 20% | 20% | 25% |

**Key Insights:**
- **Buying dominance**: #2 and #3 (constraint-focused) destroy in Buying scenarios
- **Browsing challenge**: #1 (semantic) and #4 (dense) best for vague queries
- **Override handling**: #3 > #2 > #1 (explicit override detection matters)
- **Boundary scenarios**: #1 and #4 (personalization helps when "no preference")

---

## Component Checklist: What Each Architecture Includes

### Core Components
```
Retrieval:
  [x] BM25 Keyword Search
  [x] Dense Embeddings
  [x] Knowledge Graph
  [x] Constraint Filtering
  [x] User Profile Matching

Question Strategy:
  [x] Information Gain Ranking
  [x] Attribute Sequencing
  [x] Fallback Questions
  [x] Scenario Routing

Intent Handling:
  [x] Constraint Tracking
  [x] Override Detection
  [x] Preference Swapping
  [x] History Management

Ranking:
  [x] BM25 Scoring
  [x] Cross-Encoder Reranking
  [x] Profile Personalization
  [x] LLM Reranking
```

### Architecture Component Matrices
```
                    BM25  Dense  KG  Constraint  Reranker  Profile  LLM  StateMgmt  Override
#1 Hybrid           [x]   [x]   [ ]    [x]        [x]       [x]     [x]    [x]      [x]
#2 Constraint       [x]   [ ]   [ ]    [x]        [ ]       [ ]     [ ]    [x]      [x]
#3 Multi-Route      [x]   [ ]   [ ]    [x]        [ ]       [x]     [x]    [x]      [x]
#4 Dense            [ ]   [x]   [ ]    [ ]        [ ]       [x]     [ ]    [x]      [ ]
#5 Knowledge Graph  [ ]   [ ]   [x]    [x]        [ ]       [ ]     [ ]    [x]      [x]
#6 Two-Stage        [x]   [ ]   [ ]    [x]        [x]       [ ]     [ ]    [x]      [ ]
#7 Ensemble         [x]   [x]   [ ]    [x]        [x]       [x]     [x]    [x]      [x]
#8 RL Policy        [x]   [ ]   [ ]    [ ]        [x]       [x]     [ ]    [x]      [x]
#9 Few-Shot CoT     [ ]   [ ]   [ ]    [ ]        [ ]       [ ]     [x]    [x]      [ ]
#10 Active Learn    [*]   [*]   [*]    [*]        [*]       [*]     [*]    [x]      [*]
                        (depends on implementation iteration)
```

---

## Decision Tree: Choose Your Architecture

```
START
│
├─ Do you have <1 week?
│  ├─ YES → #9 (Few-Shot CoT) - quick MVP
│  └─ NO ↓
│
├─ Is minimizing API cost critical?
│  ├─ YES → #4 (Dense) or #5 (Knowledge Graph)
│  └─ NO ↓
│
├─ Do you have ML/LLM expertise?
│  ├─ YES (strong ML team) → #1 (Hybrid) or #7 (Ensemble)
│  ├─ NO (SWE team only) → #2 (Constraint) or #6 (Two-Stage)
│  └─ MAYBE (1-2 people) ↓
│
├─ Can you use external LLM APIs?
│  ├─ YES → #1 (Hybrid) for best score
│  ├─ NO → #4 (Dense) or #5 (Knowledge Graph)
│  └─ MAYBE (limited budget) → #2 (Constraint)
│
└─ What matters most?
   ├─ Hit Rate → #1 (Hybrid)
   ├─ Speed to implement → #9 or #2
   ├─ Cost → #4, #5, or #2
   ├─ Intent Override → #3 (Multi-Route)
   ├─ Browsing Scenarios → #1 or #4
   ├─ Buying Scenarios → #2 or #3
   └─ Robustness → #3 or #7

RECOMMENDED PATHS:
- Fast winner: #9 (day 1-2) → #2 (day 3-5) → #1 (day 6-10) for hybrid
- High score: Start #1 (Hybrid), parallel #3 (Multi-Route) route fallback
- Low cost: #2 (Constraint) + #4 (Dense) ensemble
- Balanced: #3 (Multi-Route) - good at everything, master of none
```

---

## A/B Testing Roadmap (If you implement multiple)

### Week 1-2: Baseline
- Implement #2 (Constraint-Driven) as baseline
- Metrics: 40-50% hit rate, 0.03-0.04 MRR, 6-7 MTTC

### Week 2-3: Experiment
- A/B test #2 vs #6 (Two-Stage) on buying scenarios
- Expected: #6 slightly better on browsing, #2 still better on buying
- Decision: Combine into multi-route?

### Week 3-4: Upgrade
- Implement #1 (Hybrid) as primary
- Metrics: 50-60% hit rate, 0.06-0.08 MRR, 4-5 MTTC
- Fallback to #2 if LLM quality issues

### Week 4+: Polish
- Integrate #4 (Dense) for browsing scenarios
- Fine-tune ensemble weights
- Expected final: 55-70% hit rate, 0.06-0.08 MRR, 3.5-4.5 MTTC

---

## FAQ: Which architecture should I choose?

**Q: I only have 1 person and 2 weeks**
A: Start with #9 (Few-Shot CoT, 3-5 days), then pivot to #2 (Constraint, 7-10 days)

**Q: We want to win, cost is not an issue**
A: Implement #1 (Hybrid) as primary + #3 (Multi-Route) for override handling

**Q: We want minimum infrastructure complexity**
A: #2 (Constraint-Driven) - pure Python, no embeddings, no LLM APIs needed

**Q: We have budget for one LLM API call source**
A: #1 (Hybrid) - LLM for query rewriting only, rest is BM25

**Q: Our main weakness is browsing scenarios**
A: #1 (Hybrid) or #4 (Dense) - both handle semantic intent well

**Q: We keep failing on intent override**
A: Implement #3 (Multi-Route) - explicit override detection and strategy pivot

**Q: We have 3 smart people and 4 weeks**
A: Implement #1 (Hybrid) + ensemble with #4 (Dense) for combined coverage

---

