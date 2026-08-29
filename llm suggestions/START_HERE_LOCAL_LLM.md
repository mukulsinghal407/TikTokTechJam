# Your Recommended Path: Local LLM Edition
## Ollama + Mistral + 8GB Laptop = Competitive Agent

---

## THE GOOD NEWS

You CAN use locally-hosted LLMs (Ollama + Mistral). This opens up much better architectures:

**Baseline (no updates):** 12.5% hit rate, 0.107 technical score
**Your target (with #1):** 40-50% hit rate, 0.40-0.55 technical score
**Improvement:** 3.2-4.7x better! 🎯

---

## START HERE: Architecture #1 (Constraint-Driven + Light LLM)

### Why This Architecture?
✅ Fast to implement (2 weeks)
✅ Works on 8GB laptop
✅ Mostly regex-based (fast)
✅ LLM only as fallback (efficient)
✅ High hit rate (40-50%)
✅ Competitive technical score (0.40-0.55)

### What You'll Build

**Week 1: Regex + BM25 (No LLM)**
- Extract constraints via regex patterns (material, color, budget, size)
- Filter catalog using BM25 + constraints
- Generate questions by information gain
- Expected: 35-40% hit rate

**Week 2: Add Ollama + Mistral Fallback**
- Install Ollama locally
- Call LLM only when regex extraction fails
- Expected: 40-50% hit rate (+10% boost!)
- Latency: <500ms per turn
- LLM calls: ~1-2 per session (efficient!)

---

## QUICK START INSTRUCTIONS

### Step 1: Install Ollama (10 minutes)
```bash
# macOS: Download from https://ollama.ai
# Or: brew install ollama
ollama pull mistral   # 4GB download
ollama serve &        # Start server in background
```

### Step 2: Update Agent Code (Minimal Changes)
```python
# In starter/agent.py, add:

import requests
import re

class Agent:
    def __init__(self, ...):
        # ... existing code ...
        self.ollama_model = "mistral"
    
    def respond(self, session_id, user_message, turn, top_k):
        # Step 1: Extract constraints (regex, no LLM)
        constraints = {
            'material': re.search(r'cotton|polyester|nylon|...', message.lower()),
            'color': re.search(r'black|white|blue|...', message.lower()),
            'budget': re.search(r'\$(\d+)', message),
            # ... more patterns
        }
        
        # Step 2: If regex found nothing, use LLM fallback
        if not constraints:
            constraints = self._extract_via_llm(user_message)
        
        # Step 3: BM25 + constraint filtering (existing code)
        # ... rest of respond() method
```

### Step 3: Test Locally
```bash
# Make sure Ollama running
curl http://localhost:11434/api/tags

# Run evaluator
python3 -m evaluator.local_evaluator

# Check results
cat results.json | jq '.recommended_technical_score'
```

---

## THE 4-WEEK ROADMAP

| Week | Phase | Implementation | Expected Score |
|---|---|---|---|
| **1** | Regex Baseline | Constraint patterns + BM25 filtering | 35-40% hit rate, 0.30 score |
| **2** | + Light LLM | Ollama fallback for failed extractions | 40-50% hit rate, 0.40-0.50 score ✅ |
| **3** | + Routing | LLM scenario classification (turn 1) | 42-55% hit rate, 0.42-0.55 score |
| **4** | + Ensemble | BM25 + Constraint + LLM voting | 45-60% hit rate, 0.48-0.62 score |

**Minimum viable (Week 2):** 40-50% hit rate = COMPETITIVE
**Ambitious (Week 4):** 45-60% hit rate = STRONG

---

## WHAT FILES WERE CREATED FOR YOU

1. **[ARCHITECTURE_LOCAL_LLM.md](ARCHITECTURE_LOCAL_LLM.md)** ← START HERE
   - Detailed guide for all 7 viable architectures
   - Setup instructions for Ollama
   - Full code templates
   - Risk assessment

2. **[LOCAL_LLM_QUICK_REFERENCE.md](LOCAL_LLM_QUICK_REFERENCE.md)**
   - Quick reference matrix
   - Phase-by-phase implementation
   - Code structure template
   - Testing checklist

3. **[ARCHITECTURE_RECOMMENDATIONS_NO_API.md](ARCHITECTURE_RECOMMENDATIONS_NO_API.md)**
   - Original 5 no-API architectures (still valid backup)

4. **[ARCHITECTURE_COMPARISON_NO_API.md](ARCHITECTURE_COMPARISON_NO_API.md)**
   - Comparison matrix for no-API options

5. **[INTERACTIVE_SELECTOR_NO_API.md](INTERACTIVE_SELECTOR_NO_API.md)**
   - Interactive guide for exploring architectures

---

## CRITICAL SUCCESS FACTORS

### 1. Regex Pattern Coverage
Make sure your regex patterns catch most constraints:
```python
MATERIALS = ("cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon")
COLORS = ("black", "white", "blue", "red", "pink", "green", "brown", "gray", "purple", "yellow", "orange")
SIZES = ("XS", "S", "M", "L", "XL", "XXL", "32", "34", "36", "6", "8", "10", "12")
```

### 2. Question Sequencing
Ask in order of discriminative power:
1. Budget (high value filter)
2. Use case
3. Material
4. Style
5. Color
6. Size

### 3. Intent Override Detection
Watch for patterns like "Actually", "Wait", "Changed my mind" on turn 3-4

### 4. Keep LLM Calls Minimal
- Phase 1: 0 LLM calls per turn
- Phase 2: 0-2 LLM calls per session (only fallback)
- Phase 3: 0.14 LLM calls per turn (1 per session)
- Phase 4: 1 LLM call per turn (reranking)

---

## EXPECTED PERFORMANCE

### Week 1 (Regex Only)
- Hit Rate: 30-35%
- MRR: 0.025-0.030
- MTTC: 7-8 turns
- Latency: <100ms/turn
- Status: ✅ Foundation working

### Week 2 (+ Light LLM) ← COMPETITIVE
- Hit Rate: 40-50%
- MRR: 0.035-0.048
- MTTC: 5-6 turns
- Latency: <500ms/turn
- LLM calls: ~1-2 per session
- Status: ✅ Ready to submit!

### Week 3 (+ Routing)
- Hit Rate: 42-55%
- MRR: 0.040-0.050
- MTTC: 5-6 turns
- LLM calls: ~0.14 per turn (very efficient!)
- Status: ✅ Optimized

### Week 4 (+ Ensemble)
- Hit Rate: 45-60%
- MRR: 0.045-0.065
- MTTC: 4-5 turns
- Status: ✅ High performance

---

## FAQ

**Q: Will 8GB be enough with Ollama running?**
A: Yes! Ollama runs separately (~4GB), your Python runs in separate process (~500MB).

**Q: How fast is Mistral on CPU?**
A: 500-800ms per LLM call. For Phase 2 (1-2 calls per session), totally acceptable.

**Q: Should I use Phase 2 or Phase 4?**
A: Phase 2 is minimum viable + competitive. Phase 4 if you have full 4 weeks.

**Q: Can I use different LLM models?**
A: Yes! Try Phi (faster) or Neural Chat (better quality). Just `ollama pull [model]`.

**Q: What if LLM call fails?**
A: Agent falls back to regex-only mode + profile-based recommendations. Never crashes.

**Q: Does this require GPU?**
A: No! CPU works fine. GPU would speed up 10-50x, but not required.

**Q: How many LLM tokens per session?**
A: Phase 2: ~100-500 tokens. Phase 4: ~2000-3000 tokens. All free locally!

---

## RISK ASSESSMENT

**Low Risk (Safe to proceed):**
- Phase 1: Pure Python, no LLM, no dependencies ✅
- Phase 2: Lightweight LLM usage, fails gracefully ✅
- Phase 3: Single LLM call per session ✅

**Medium Risk:**
- Phase 4: Depends on LLM reranking quality (tunable)

**Avoid:**
- Architecture #7 (Few-Shot CoT): Too slow on CPU, not recommended

---

## NEXT STEPS

### Immediate (Next 30 minutes)
1. Read [ARCHITECTURE_LOCAL_LLM.md](ARCHITECTURE_LOCAL_LLM.md)
2. Install Ollama: https://ollama.ai
3. Download Mistral: `ollama pull mistral`

### This Week (Days 1-5)
1. Implement Phase 1 (regex + BM25)
2. Run local evaluator: `python3 -m evaluator.local_evaluator`
3. Verify: Hit rate >30%

### Next Week (Days 6-10)
1. Add Ollama integration
2. Implement LLM fallback for constraint extraction
3. Verify: Hit rate >40%
4. **Submit if competitive!**

### Weeks 3-4 (If time permits)
1. Try Phase 3 (scenario routing) or Phase 4 (ensemble)
2. Fine-tune weights on public set

---

## KEY METRICS TO TRACK

Track these numbers to know you're on track:

```
Week 1 Target:
  hit_rate_at_10: >30%
  mrr: >0.025
  mttc: <8
  latency_per_turn: <100ms

Week 2 Target (SUBMIT POINT):
  hit_rate_at_10: >40%
  mrr: >0.035
  mttc: <6
  latency_per_turn: <500ms
  llm_calls_per_session: <3

Week 3-4 Target (If ambitious):
  hit_rate_at_10: >50%
  mrr: >0.045
  mttc: <5
  technical_score: >0.45
```

---

## FINAL RECOMMENDATION

**Start with Architecture #1 (Constraint-Driven + Light LLM)**

This is:
- ✅ Easiest to implement (2 weeks)
- ✅ Lowest risk (mostly rules-based)
- ✅ Most efficient on 8GB (minimal LLM calls)
- ✅ Competitive hit rate (40-50%)
- ✅ Clear path to improve (Phase 2 → 3 → 4)

**You should be able to achieve:**
- Week 2: **40-50% hit rate** (competitive)
- Week 3: **42-55% hit rate** (strong)
- Week 4: **45-60% hit rate** (very strong)

This is **3-5x better than baseline** and should be competitive in the competition.

---

## GET STARTED NOW

1. Install Ollama (5 mins): https://ollama.ai
2. Read full guide: [ARCHITECTURE_LOCAL_LLM.md](ARCHITECTURE_LOCAL_LLM.md)
3. Start Week 1 implementation (regex baseline)
4. Come back after Phase 1 if you have questions

Good luck! 🚀

