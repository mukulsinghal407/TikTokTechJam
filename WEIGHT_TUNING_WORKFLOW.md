# Complete Workflow: Architecture → Weight Tuning → Deployment
## End-to-End Guide for Rule-Based Ranking with Local LLM

---

## 📋 Complete Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. SELECT ARCHITECTURE (You did this!)                          │
│    → Chose #1: Constraint-Driven + Light LLM                    │
├─────────────────────────────────────────────────────────────────┤
│ 2. IMPLEMENT PHASE 1: Regex Baseline (Week 1)                  │
│    → Constraint extraction patterns                              │
│    → BM25 filtering                                              │
│    → Question generation                                         │
│    → Expected: 35-40% hit rate                                   │
├─────────────────────────────────────────────────────────────────┤
│ 3. TUNE RANKING WEIGHTS (This guide!)                          │
│    → Run weight_tuner.py                                         │
│    → Grid search + random search                                 │
│    → Generate optimal_ranking_weights.json                       │
├─────────────────────────────────────────────────────────────────┤
│ 4. INTEGRATE WEIGHTS (Days 3-5)                                │
│    → Add feature computation to agent                            │
│    → Load tuned weights                                          │
│    → Test locally                                                │
│    → Expected: 40-50% hit rate ← SUBMIT POINT!                 │
├─────────────────────────────────────────────────────────────────┤
│ 5. OPTIONAL: Add LLM & Reranking (Week 2)                      │
│    → Ollama integration                                          │
│    → LLM reranking for final top-10                             │
│    → Expected: 45-55% hit rate                                   │
├─────────────────────────────────────────────────────────────────┤
│ 6. OPTIONAL: Multi-Route Orchestration (Week 3-4)              │
│    → Scenario classification                                     │
│    → Route-specific strategies                                   │
│    → Expected: 50-65% hit rate                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Quick Timeline

| Phase | Task | Time | Expected Score |
|---|---|---|---|
| **1** | Regex + BM25 baseline | 3-5 days | 35-40% hit |
| **2** | Weight tuning | 1-2 hours | 38-42% hit |
| **3** | Integration | 1-2 days | **40-50% hit** ✅ |
| **4** | Optional: LLM | 2-3 days | 45-55% hit |
| **5** | Optional: Routing | 2-3 days | 50-65% hit |

**Week 1 Complete:** You'll have a competitive agent at 40-50% hit rate!

---

## 🚀 Today's Focus: Weight Tuning (Phase 3)

You're at: "I have regex + BM25, now how do I tune ranking weights?"

### Here's Exactly What To Do

#### Step 1: Understand the Problem (5 minutes)

You have products to rank:
```
Product A: constraint_match=0.8, bm25=0.6, profile_sim=0.3, popularity=0.7
Product B: constraint_match=0.5, bm25=0.9, profile_sim=0.8, popularity=0.2
```

Which should rank higher? Depends on weights!

```
Weights A (constraint-focused):
  score_A = 0.8*0.6 + 0.6*0.2 + 0.3*0.1 + 0.7*0.05 = 0.635
  score_B = 0.5*0.6 + 0.9*0.2 + 0.8*0.1 + 0.2*0.05 = 0.445
  → A ranks higher ✓

Weights B (bm25-focused):
  score_A = 0.8*0.3 + 0.6*0.5 + 0.3*0.1 + 0.7*0.05 = 0.585
  score_B = 0.5*0.3 + 0.9*0.5 + 0.8*0.1 + 0.2*0.05 = 0.615
  → B ranks higher ✓
```

Which weights are better? That's what tuning finds out!

#### Step 2: Run Weight Tuning (10 minutes to 2 hours, depending on iterations)

```bash
# Copy weight_tuner.py to your project directory
cp /path/to/weight_tuner.py .

# Run tuning (will evaluate many weight combinations)
python3 weight_tuner.py

# Output: optimal_ranking_weights.json
# Example:
# {
#   "optimal_weights": {
#     "constraint_match": 0.55,
#     "bm25_normalized": 0.25,
#     "profile_similarity": 0.12,
#     "popularity": 0.05,
#     "category_match": 0.03
#   },
#   "score": 0.452
# }
```

**What the script does:**
1. Loads 200 public sessions
2. Samples 50 sessions for speed
3. Tries 50 random weight combinations (Phase 1)
4. Finds best one
5. Does fine grid search around best (Phase 2)
6. Saves optimal weights to JSON

**How long?** ~15-30 minutes with 50 random + grid search

#### Step 3: Integrate Weights into Agent (30 minutes)

See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for full code.

Quick summary:
```python
# In starter/agent.py

def __init__(self, catalog_path):
    # Load optimal weights
    with open('optimal_ranking_weights.json') as f:
        config = json.load(f)
        self.ranking_weights = config['optimal_weights']

def respond(self, session_id, user_message, turn, top_k):
    # ... existing code ...
    
    # Get top 100 candidates
    candidates = bm25_search(user_message, k=100)
    
    # Score each candidate
    scored = []
    for product in candidates:
        features = compute_ranking_features(product, user_message, constraints, user_profile)
        score = sum(features[f] * self.ranking_weights[f] for f in features)
        scored.append((product['asin'], score))
    
    # Return top-10
    top_10 = sorted(scored, key=lambda x: -x[1])[:top_k]
    return {
        'recommendations': [{'parent_asin': asin} for asin, _ in top_10],
        'message': question,
        'ask_attribute': attr
    }
```

#### Step 4: Test and Verify (30 minutes)

```bash
# Run evaluator
python3 -m evaluator.local_evaluator

# Check results
echo "Target metrics:"
echo "  Hit Rate: > 40%"
echo "  MRR: > 0.035"
echo "  MTTC: < 6 turns"
echo "  Technical Score: > 0.40"
```

**If metrics improved:** ✅ Phase 3 complete! Proceed to Phase 4 if time permits.
**If metrics didn't improve:** See troubleshooting section.

---

## 🔍 Understanding Your Tuned Weights

After running tuning, you'll get weights like:

```json
{
  "constraint_match": 0.550,      ← 55% importance
  "bm25_normalized": 0.250,       ← 25% importance
  "profile_similarity": 0.120,    ← 12% importance
  "popularity": 0.050,            ← 5% importance
  "category_match": 0.030         ← 3% importance
}
```

**What this means:**
- **constraint_match = 55%**: Your #1 success factor is matching explicit constraints
  - This makes sense: Buying scenarios (40%) need explicit constraints
  - If tuned value < 0.4: Your constraint extraction is broken
  - If tuned value > 0.7: You might be ignoring other signals too much

- **bm25_normalized = 25%**: Keyword relevance matters but isn't dominant
  - This makes sense: Browsing scenarios need semantic understanding
  - If tuned value < 0.15: You're not using keywords enough
  - If tuned value > 0.4: Over-indexing on keywords (might ignore preferences)

- **profile_similarity = 12%**: User preferences help but aren't critical
  - This makes sense: 40% Buying (explicit constraints override preferences)
  - If tuned value < 0.05: User profile not useful (maybe all zeros?)
  - If tuned value > 0.3: Great user profiles (tuner finds them valuable)

- **popularity = 5%**: Overall popularity is a small tiebreaker
- **category_match = 3%**: Category matching is least important

**Red flags in tuned weights:**
- All weights equal (0.2 each) → Tuner couldn't differentiate
- One weight = 0.99, rest = 0 → Severe overfitting
- Weights opposite of intuition → Bug in feature computation

---

## 🛠️ Customizing Tuning for Your Setup

### If You Want Faster Tuning (5-10 minutes):

```python
# In weight_tuner.py, modify main():

tuner = SimpleWeightTuner(
    public_set_path='data/public_set.jsonl',
    sample_size=20  # Use only 20 sessions (was 50)
)

random_results = tuner.random_search(
    n_iterations=30,  # Fewer iterations
    ...
)

# Trade-off: Slightly less stable results, but much faster
```

### If You Want More Accurate Tuning (1-2 hours):

```python
tuner = SimpleWeightTuner(
    sample_size=100  # Use all 200 sessions
)

random_results = tuner.random_search(
    n_iterations=200,  # More comprehensive search
    ...
)

grid_results = tuner.grid_search(
    step_size=0.03  # Finer-grained search
)

# Trade-off: More stable weights, but longer tuning time
```

### If You Want to Add New Features:

```python
# In weight_tuner.py, compute_ranking_features():

def compute_ranking_features(...):
    # ... existing features ...
    
    # NEW feature: Brand trust
    brand_trust = user_profile.get('brand_trust_scores', {}).get(product['brand'], 0.5)
    features['brand_trust'] = brand_trust
    
    return features

# Then in main(), add to weight_ranges:
weight_ranges = {
    'constraint_match': (0.2, 0.7),
    'bm25_normalized': (0.1, 0.4),
    'profile_similarity': (0.05, 0.25),
    'popularity': (0.0, 0.15),
    'category_match': (0.0, 0.15),
    'brand_trust': (0.0, 0.1),  # NEW
}
```

---

## ❌ Avoiding Common Mistakes

### Mistake 1: Not Normalizing Features
❌ WRONG:
```python
features['bm25'] = bm25_score  # Could be 0-100
features['constraint'] = matches  # Could be 0-5
score = 0.5 * features['bm25'] + 0.5 * features['constraint']
# Result: bm25 dominates (0-50 range) vs constraint (0-2.5 range)
```

✅ CORRECT:
```python
features['bm25'] = min(bm25_score / 100, 1.0)  # Normalized to [0, 1]
features['constraint'] = matches / 5  # Normalized to [0, 1]
score = 0.5 * features['bm25'] + 0.5 * features['constraint']
# Result: Both contributions are comparable
```

### Mistake 2: Overfitting to Public Set
❌ WRONG: Tune until you get 95% hit rate on public set
```python
# This will overfit! Private set will be 30-40% due to different distribution
random_results = tuner.random_search(n_iterations=500)  # Too many!
```

✅ CORRECT: Use moderate tuning
```python
# This finds generalizable patterns
random_results = tuner.random_search(n_iterations=50-100)
# Followed by grid search on top 10
```

### Mistake 3: Weights Not Summing to 1.0
❌ WRONG:
```python
weights = {'a': 0.5, 'b': 0.4, 'c': 0.3}  # Sum = 1.2!
score = sum(features[k] * weights[k] for k in weights)  # Score can exceed 1.0
```

✅ CORRECT:
```python
weights = {'a': 0.5, 'b': 0.4, 'c': 0.3}
total = sum(weights.values())  # = 1.2
weights = {k: v/total for k, v in weights.items()}  # Normalize to sum = 1.0
score = sum(features[k] * weights[k] for k in weights)  # Score in [0, 1]
```

The tuning script already does this! But good to understand.

### Mistake 4: Features Don't Match Reality
❌ WRONG: Feature "constraint_match" always 0.5 (dummy value)
```python
# This wastes tuning effort - feature has no signal
features['constraint_match'] = 0.5  # No variation!
# Tuner: "This feature doesn't help, ignore it"
weights['constraint_match'] = 0.0
```

✅ CORRECT: Features should have real variation
```python
# Compute ACTUAL constraint satisfaction
if product_matches_constraint:
    features['constraint_match'] = 1.0
else:
    features['constraint_match'] = 0.0
# Now tuner can see this feature's impact
```

---

## 📊 Monitoring Tuning Progress

While tuning runs, you'll see output like:

```
Starting random search: 50 iterations
============================================================
[1/50] New best: 0.3421
  constraint_match: 0.551
  bm25_normalized: 0.251
[2/50] Score: 0.3412 (no improvement)
[3/50] Score: 0.3405 (no improvement)
[4/50] New best: 0.3445
  constraint_match: 0.548
  bm25_normalized: 0.268
...
[50/50] Final best: 0.3487
```

**What to look for:**
- "New best" appearing every 5-10 iterations: Good, finding improvements
- "New best" appearing every 1-2 iterations: Great, very productive search
- "New best" only in first 10 iterations: Okay, found optimum quickly
- No "New best" after iteration 30: Normal, hitting diminishing returns

**Expected progress:**
- Random search: 0.30 → 0.35 (improving)
- Grid search: 0.35 → 0.40+ (fine-tuning)
- Total improvement: 0.30 → 0.40 (33% boost from tuning)

---

## ✅ Success Criteria

After weight tuning, you should see:

```
BEFORE tuning (just regex + BM25):
  Hit Rate: 30-35%
  MRR: 0.025-0.030
  MTTC: 7-8

AFTER tuning:
  Hit Rate: 38-42% ← Expected gain: +8%
  MRR: 0.033-0.038 ← Expected gain: +30%
  MTTC: 6-7 ← Expected gain: -1 turn
  
  Technical Score: 0.35-0.40 ← Expected gain: +33%
```

**If you're NOT seeing improvement:**
1. Check feature computation (print sample features)
2. Verify constraints are extracting correctly
3. Verify weights file loaded correctly
4. Try more tuning iterations
5. Check if feature_match always same value (broken feature)

---

## 🚀 Next Steps After Weight Tuning

### If Hit Rate >= 40% (Good!)
✅ You're competitive! Consider:
1. Submitting as-is (40-50% hit rate is strong)
2. Optional: Add Phase 4 (LLM reranking) for +5% boost

### If Hit Rate 35-39% (Moderate)
⚠️ Close but not quite there:
1. Try re-tuning with more iterations
2. Check constraint extraction patterns
3. Add more features to ranking
4. Proceed to Phase 4 (LLM reranking) for boost

### If Hit Rate < 35% (Problem)
❌ Something's wrong:
1. Debug constraint extraction (what gets extracted?)
2. Check BM25 retrieval (are right products in top 100?)
3. Verify feature computation (print sample values)
4. Check for bugs in ranking code

---

## 📝 Checklist

- [ ] Ran `python3 weight_tuner.py` successfully
- [ ] `optimal_ranking_weights.json` was created
- [ ] Inspected tuned weights (do they make sense?)
- [ ] Updated `starter/agent.py` with new methods
- [ ] Called `_load_ranking_weights()` in `__init__()`
- [ ] Updated `respond()` to score products with weights
- [ ] Ran `python3 -m evaluator.local_evaluator`
- [ ] Metrics improved (hit rate > 38%)?
- [ ] Saved `optimal_ranking_weights.json` to git
- [ ] Ready to move to Phase 4 (optional) or submit

---

