# Architecture Comparison Matrix (NO EXTERNAL APIs)

## Quick Visual Reference - VIABLE ONLY

| Rank | Architecture | Hit Rate | MRR | MTTC | API Cost | Setup (weeks) | Buying | Browsing | Override | Boundary | Best For |
|------|---|---|---|---|---|---|---|---|---|---|---|
| **1** | 🟢 Constraint-Driven | 35-50% | 0.03-0.04 | 6-7 | $0 | 1-2 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **Fast + Buying** |
| **2** | 🔵 Two-Stage Ranking | 30-45% | 0.025-0.035 | 6-7 | $0 | 1-2 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | **Browsing + Natural** |
| **3** | 🟡 Knowledge Graph | 25-40% | 0.02-0.03 | 8-9 | $0 | 2-3 | ⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐ | **Transparency** |
| **4** | 🟠 RL Policy | 20-35% | 0.015-0.025 | 7-8 | $0 | 2-3 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | **Learning** |
| **5** | 🟣 Ensemble Rules | 30-45% | 0.025-0.035 | 7-8 | $0 | 2-3 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | **Robustness** |

---

## Performance Predictions (Technical Score - NO API)

```
Technical Score = 0.50 × Hit Rate@10 + 0.30 × MRR + 0.20 × Efficiency
                  (where Efficiency = clip((11 - MTTC) / 10, 0, 1))

Baseline (BM25):          0.107  (12.5% hit, 0.068 MRR, 9.81 MTTC)

#1  Constraint-Driven:    0.40-0.50   (35-50% hit, 0.03-0.04 MRR, 6-7 MTTC)   ⭐ 3.7-4.7x better
#2  Two-Stage:            0.30-0.45   (30-45% hit, 0.025-0.035 MRR, 6-7 MTTC) ⭐ 2.8-4.2x better
#3  Knowledge Graph:      0.25-0.40   (25-40% hit, 0.02-0.03 MRR, 8-9 MTTC)   ⭐ 2.3-3.7x better
#4  RL Policy:            0.20-0.40   (20-35% hit, 0.015-0.025 MRR, 7-8 MTTC) ⭐ 1.9-3.7x better
#5  Ensemble:             0.30-0.45   (30-45% hit, 0.025-0.035 MRR, 7-8 MTTC) ⭐ 2.8-4.2x better
```

---

## Cost Breakdown

### LLM/API Cost
```
#1-5: $0 per turn (all local Python)
```

### Compute Requirements
```
#1 Constraint-Driven: ~50 MB RAM, <100ms per turn (minimal)
#2 Two-Stage:         ~75 MB RAM, <150ms per turn
#3 Knowledge Graph:   ~200 MB RAM (materialized relations), <50ms per turn
#4 RL Policy:         ~100 MB RAM, <50ms per turn (pre-computed policy)
#5 Ensemble:          ~150 MB RAM, <200ms per turn (three systems)
```

### Implementation Effort
```
#1 Constraint-Driven: 7-14 days (regex + BM25)
#2 Two-Stage:         7-14 days (filtering pipeline)
#3 Knowledge Graph:   14-21 days (data engineering)
#4 RL Policy:         14-21 days (ML + offline training)
#5 Ensemble:          14-21 days (system integration)
```

### Team Size
```
#1: 1-2 people (SWE + data skills)
#2: 1-2 people (SWE + product sense)
#3: 2-3 people (SWE + data engineer)
#4: 2-3 people (SWE + ML expertise)
#5: 2-3 people (SWE + systems design)
```

---

## Scenario Performance (% hit rate by scenario type)

| Architecture | Buying (40%) | Browsing (40%) | Override (15%) | Boundary (5%) | Weighted Avg |
|---|---|---|---|---|---|
| #1 Constraint-Driven | 70% | 25% | 40% | 35% | 48% |
| #2 Two-Stage | 50% | 40% | 30% | 35% | 42% |
| #3 Knowledge Graph | 50% | 15% | 25% | 20% | 35% |
| #4 RL Policy | 45% | 30% | 35% | 30% | 36% |
| #5 Ensemble Rules | 55% | 35% | 35% | 35% | 43% |

**Analysis:**
- **#1 dominates Buying** (70%): explicit constraints are its strength
- **#2 shines in Browsing** (40%): gradual refinement works for vague queries
- **#1 best for Override** (40%): constraint state machine handles swaps
- **#5 most balanced** (43%): ensemble approach covers all scenarios
- **#3 weakest in Browsing** (15%): needs explicit attribute hints

---

## Component Checklist: What Each Architecture Includes

```
                    BM25  Constraint  Rules  Profile  Override  Question_Gen
#1 Constraint       [x]      [x]      [x]     [x]      [x]         [x]
#2 Two-Stage        [x]      [x]      [x]     [ ]      [ ]         [x]
#3 Knowledge Graph  [ ]      [x]      [x]     [ ]      [x]         [ ]
#4 RL Policy        [x]      [ ]      [x]     [x]      [x]         [x]
#5 Ensemble         [x]      [x]      [x]     [x]      [x]         [x]
```

---

## Core Building Blocks (Shared Code)

All NO-API architectures use these foundations:

### 1. Constraint Extraction (Regex Patterns)
```python
MATERIALS = ("cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon")
COLORS = ("black", "white", "blue", "red", "pink", "green", "brown", "gray", "purple", "yellow", "orange")
SIZES = ("XS", "S", "M", "L", "XL", "XXL", "32", "34", "6", "8", "10")

def extract_constraints(message: str) -> dict:
    """Extract (attribute, value, confidence) tuples from message"""
    constraints = {}
    
    # Material
    for mat in MATERIALS:
        if re.search(rf'\b{mat}\b', message.lower()):
            constraints['material'] = (mat, 0.95)
    
    # Color
    for color in COLORS:
        if re.search(rf'\b{color}\b', message.lower()):
            constraints['color'] = (color, 0.95)
    
    # Budget
    budget_match = re.search(r'\$(\d+)-?(\d*)', message)
    if budget_match:
        constraints['budget'] = (budget_match.group(0), 0.90)
    
    return constraints
```

### 2. BM25 Filtering (SQLite FTS5)
```python
# Already in baseline code, extend with:
def apply_constraint_filter(expression: str, constraint_field: str, constraint_value: str) -> list:
    """Filter products by constraint"""
    rows = self.connection.execute(
        f"SELECT parent_asin FROM products "
        f"WHERE products MATCH ? AND {constraint_field} LIKE ?",
        (expression, f"%{constraint_value}%")
    ).fetchall()
    return [row[0] for row in rows]
```

### 3. Session State (Conversation Memory)
```python
class Session:
    def __init__(self, session_id: str, user_profile: dict):
        self.session_id = session_id
        self.user_profile = user_profile
        self.constraints = {}  # {attribute: (value, confidence)}
        self.asked_attributes = set()  # Which attributes already mentioned
        self.conversation_history = []  # [(turn, message)]
        self.top_candidates = []  # Current best 100 products
        self.override_detected = False
```

### 4. Question Generation
```python
def generate_question(self, session: Session) -> str:
    """Generate best next question based on information gain"""
    
    # Attributes not yet asked about
    unanswered = {
        'budget', 'use_case', 'material', 'style', 'color', 'size'
    } - session.asked_attributes
    
    # Information gain per attribute (simplified)
    gains = {
        'budget': 0.8,      # High discriminative power
        'use_case': 0.7,
        'material': 0.6,
        'style': 0.5,
        'color': 0.3,
        'size': 0.2
    }
    
    # Ask about highest-gain unanswered attribute
    best_attr = max(unanswered, key=lambda x: gains.get(x, 0))
    session.asked_attributes.add(best_attr)
    
    templates = {
        'budget': "What's your budget range?",
        'use_case': "What will you use this for?",
        'material': "Do you prefer a specific material like cotton or silk?",
        'style': "What style are you looking for?",
        'color': "Do you have a color preference?",
        'size': "What size do you need?"
    }
    
    return templates[best_attr]
```

### 5. Intent Override Detection
```python
def detect_override(message: str) -> bool:
    """Detect if user changed their mind (turn 3-4)"""
    override_signals = {
        'actually', 'wait', 'ignore', 'changed my mind', 
        'different', 'different preference', 'scratch that',
        'not what i meant', 'let me rephrase'
    }
    return any(signal in message.lower() for signal in override_signals)
```

---

## Decision Tree: NO-API Only

```
START
│
├─ How much time do you have?
│  ├─ <1 week → #1 (Constraint-Driven)
│  ├─ 1-2 weeks → #1 + #2 (Two-Stage fallback)
│  ├─ 2-3 weeks → #1 + #2 + #5 (Ensemble)
│  └─ 3+ weeks → #4 (RL Policy) for potential gains
│
├─ What's your team's strength?
│  ├─ Strong ML → #4 (RL Policy)
│  ├─ Strong SWE → #1 (Constraint) or #5 (Ensemble)
│  └─ Mixed → #2 (Two-Stage, balanced approach)
│
├─ What scenario matters most?
│  ├─ Buying (40%) → #1 (Constraint-Driven) - 70% hit
│  ├─ Browsing (40%) → #2 (Two-Stage) - 40% hit
│  ├─ Override (15%) → #1 (Constraint) - 40% hit
│  └─ All balanced → #5 (Ensemble) - ~43% average
│
└─ Do you need transparency?
   ├─ YES → #3 (Knowledge Graph) - auditable
   └─ NO → #1 (Constraint) - best score

RECOMMENDED STARTING POINT:
→ Week 1: Implement #1 (Constraint-Driven)
→ Week 2: Add #2 (Two-Stage) as fallback for Browsing
→ Week 3-4: Tune + optimize + ensemble if time permits
```

---

## Implementation Path (Week by Week)

### Week 1: Foundation (#1 Constraint-Driven)
```
Day 1-2: Regex patterns for constraint extraction
Day 3: BM25 filtering on extracted constraints
Day 4: Question generation (info gain ranking)
Day 5: Session state management
Day 6-7: Override detection + basic testing
```
**Result: 35-40% hit rate, 0.025-0.030 MRR, 7 MTTC**

### Week 2: Refinement (#1 Tuning + #2 Fallback)
```
Day 1-2: Improve constraint parser (edge cases)
Day 3: Add profile-aware filtering
Day 4: Implement Two-Stage routing for Browsing
Day 5: Enhance override handling
Day 6-7: Tune question sequencing + test
```
**Result: 40-48% hit rate, 0.030-0.038 MRR, 6-7 MTTC**

### Week 3: Scale (#5 Ensemble - If time permits)
```
Day 1-2: Implement product similarity (Jaccard)
Day 3: Build ensemble weighting
Day 4: Scenario-adaptive weights
Day 5: Fine-tune on public dataset
Day 6-7: Performance optimization
```
**Result: 45-55% hit rate, 0.038-0.048 MRR, 5-6 MTTC**

### Week 4: Polish
```
Day 1-2: Error handling + edge cases
Day 3: Fallback strategies
Day 4: Logging + monitoring
Day 5-7: Final tuning + optimization
```
**Result: 50-65% hit rate, 0.048-0.065 MRR, 4-5 MTTC**

---

## Common Issues & Fixes

### Issue: Hit rate stuck at 25-30%
**Cause:** Constraint extraction too strict
**Fix:** 
- Loosen regex patterns
- Add fuzzy matching for typos (e.g., "cotten" → "cotton")
- Fall back to BM25-only if no constraints matched

### Issue: MTTC too high (>8 turns)
**Cause:** Questions not discriminative enough
**Fix:**
- Prioritize high-discriminative attributes first (budget, use_case)
- Filter candidate pool more aggressively after each question
- Implement Two-Stage approach (#2) for early broad filtering

### Issue: Intent override failing
**Cause:** Not detecting or applying override correctly
**Fix:**
- Add more override trigger patterns ("actually", "wait", etc.)
- Maintain old + new constraint sets separately
- Swap weights when override detected
- Test this extensively on public override scenarios

### Issue: Browsing scenarios failing (vague initial queries)
**Cause:** Constraint extraction gets nothing from vague message
**Fix:**
- Fall back to #2 Two-Stage approach
- Use profile-based recommendations
- Ask broad questions first (budget, use_case) before specific ones

### Issue: Memory/performance slow
**Cause:** Processing inefficiency
**Fix:**
- Pre-compile regex patterns (done in regex_compile)
- Cache constraint extraction results
- Use SQLite indices on frequently-queried fields
- Materialize product attributes during init

---

## Success Checklist

- [ ] Regex patterns for material, color, budget, size, style, use_case
- [ ] BM25 filtering on constraints
- [ ] Session state management (constraint tracking)
- [ ] Question generation (info gain ordering)
- [ ] Override detection (pattern matching)
- [ ] Profile-aware fallback
- [ ] Error handling (empty results, invalid input)
- [ ] Local evaluator running successfully
- [ ] Public set hit rate >35%
- [ ] Intent override scenarios working (>30% hit)
- [ ] Browsing scenarios not collapsing (<30% hit)

---

## FAQ: NO-API Edition

**Q: Can I use numpy/scipy/scikit-learn?**
A: Yes! All run locally, no internet needed.

**Q: Should I pre-embed products with Sentence-Transformers?**
A: Only if you want to try hybrid approach later. For pure #1, not needed.

**Q: How do I test locally?**
A: `python3 -m evaluator.local_evaluator` runs 200 public sessions.

**Q: Can I see per-scenario results?**
A: Yes, evaluator breaks down by Buying/Browsing/Override/Boundary.

**Q: What if MTTC is 9+?**
A: Questions are ineffective. Use Two-Stage approach or smarter sequencing.

**Q: Should I tune on the public set?**
A: 5-fold CV to avoid overfitting. Or implement ensemble (robust to overfit).

---

## Comparison: #1 vs #2 vs #5

| Metric | #1 Constraint | #2 Two-Stage | #5 Ensemble |
|---|---|---|---|
| **Hit Rate** | 35-50% | 30-45% | 30-45% |
| **Buying** | 70% | 50% | 55% |
| **Browsing** | 25% | 40% | 35% |
| **Override** | 40% | 30% | 35% |
| **Implementation** | 1-2 weeks | 1-2 weeks | 2-3 weeks |
| **Code Complexity** | Low | Medium | High |
| **Best For** | Fast + Winning | Browsing + Natural | Robustness + Balance |

**Recommendation:**
- **Minimum:** Implement #1 only (fast, high impact)
- **Target:** Implement #1 + #2 (covers all scenarios)
- **Ambitious:** Implement #1 + #2 + #5 (ensemble for robustness)

---

