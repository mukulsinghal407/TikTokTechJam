# Multi-Turn Shopping Agent: Architecture Recommendations
## ⚠️ NO EXTERNAL APIs Constraint Edition

**Constraint:** No external LLM APIs, embedding APIs, vector databases, or cloud services. Local Python only.

---

## Competition Context
- **Hidden Target**: Find product by asking clarifying questions (max 10 turns)
- **Scoring**: 50% Hit Rate@10 + 30% MRR + 20% Efficiency (based on MTTC)
- **Baseline Performance**: 12.5% hit rate, 0.068 MRR, 9.81 MTTC, 0.107 Technical Score
- **Scenarios**: 40% Buying, 40% Browsing, 15% Intent Override, 5% Boundary

---

## REVISED TOP 5 VIABLE ARCHITECTURES (NO EXTERNAL APIs)

### 🥇 **Architecture #1: Constraint-Driven Filtering with Ranked Question Bank**
**Ranking: 1 (BEST FOR NO-API CONSTRAINT)**

**Components:**
- **Hard Constraint Parser**: Extract explicit constraints from each message (budget, material, size, color, etc.)
  - Regex-based material/color matching (pre-compiled patterns)
  - Budget range extraction ("$50-100", "under $200")
  - Structured output: `[("material", "cotton", 0.95), ("budget", "$50-100", 0.85)]`
  
- **Soft Preference Accumulator**: Track hints and preferences across turns
  - Maintain session state: `{session_id: {"constraints": [...], "asked_attrs": set(...)}}`
  
- **Constraint-Based Filtering** (pure BM25):
  - Build iterative SQL queries: `WHERE title MATCH "material:cotton" AND price < 100`
  - Score products by constraint satisfaction (exact match = highest score)
  - Use SQLite FTS5 for keyword matching (already in baseline)
  
- **Intelligent Question Generator** (information gain ranking):
  - Calculate attribute entropy: Which attributes would narrow results most?
  - Recommended order: Budget → Use Case → Material → Style → Color → Size
  - Pre-built question templates (no LLM needed)
  - Example: "What's your budget range?"
  
- **Profile-Aware Filtering** (optional fallback):
  - Use anonymized user_profile (purchase frequency, rating patterns)
  - When results ambiguous, bias toward user's historical preferences
  
- **Intent Override Manager**: State machine for constraint changes
  - Track old constraints vs new constraints
  - On turn 3-4, detect "Actually, ignore..." patterns
  - Swap constraint sets, re-filter candidates

**Why #1 for No-API:**
- ✅ Pure Python + SQLite (no external dependencies)
- ✅ Deterministic (auditable, no LLM randomness)
- ✅ Fast (BM25 on SQLite is extremely efficient)
- ✅ Excellent for Buying scenario (40% of dataset)
- ✅ Strong intent override handling
- ✅ Low latency (<100ms per turn)
- ✅ Zero API costs

**Expected Gains:** Hit Rate +35-50%, MRR +30-40%, MTTC -2 to -3 turns
**Technical Score:** 0.40-0.50 (3.7-4.7x better than baseline)
**Implementation:** 1-2 weeks
**Lines of Code:** ~800-1200 lines
**Memory Usage:** <50 MB

**Implementation Roadmap:**
```python
# Week 1: Core pipeline
- Constraint extraction (regex patterns)
- BM25 filtering
- Question generation
- Session state management

# Week 2: Refinements
- Override detection
- Profile personalization
- Fallback strategies
- Error handling
```

---

### 🥈 **Architecture #2: Two-Stage Ranking (Coarse→Fine Filtering)**
**Ranking: 2**

**Components:**
- **Stage 1 (Turns 1-3: Broad Filtering)**
  - Loose keyword matching on all 50K products
  - Filter to top 500-1000 candidates per query
  - Ask about highest-level attributes: Budget, Use Case, Category
  - Use BM25 with lower precision threshold
  
- **Stage 2 (Turns 4-10: Fine Ranking)**
  - Narrow candidate pool from Stage 1 to top 100-200
  - Apply specific constraints: Material, Color, Size, Style
  - Use stricter BM25 matching
  - Rerank by constraint satisfaction score
  
- **Adaptive Depth**:
  - Buying scenario: Skip Stage 1, jump to Stage 2 (hard constraint given)
  - Browsing: Spend 3-4 turns in Stage 1, gradually narrow
  - Intent Override: Reset to Stage 1 at turn 3-4 when constraint changes
  
- **Question Prioritization by Stage**:
  - Stage 1: High-cardinality attributes (Use Case, Category, Budget)
  - Stage 2: Low-cardinality distinguishers (Exact Color, Specific Size)
  - Each question → filter × 0.5 to 0.7 (good reduction rate)

**Why #2:**
- ✅ Pure Python + SQLite
- ✅ Mimics real shopping behavior (browse → refine)
- ✅ Good MTTC (fewer wasted turns due to staged approach)
- ✅ Robust to noisy input (Stage 1 is forgiving)
- ✅ Natural question progression
- ✅ Works well for Browsing scenario (vague initial queries)

**Expected Gains:** Hit Rate +30-45%, MRR +25-35%, MTTC -2 to -3 turns
**Technical Score:** 0.30-0.45 (2.8-4.2x better than baseline)
**Implementation:** 1-2 weeks
**Lines of Code:** ~1000-1500 lines

---

### 🥉 **Architecture #3: Knowledge Graph + Attribute Extraction**
**Ranking: 3**

**Components:**
- **Attribute Materialization** (pre-computed):
  - Extract and normalize all product attributes during init
  - Build relationship tables: {product_id → material → "cotton"}, etc.
  - Materialize in SQLite: `CREATE TABLE product_materials AS SELECT ...`
  - Enables O(1) constraint checking
  
- **Structured Extraction** (regex + pattern matching):
  - Parse user message → `{constraint_type: value, confidence}`
  - Material: regex on known materials list
  - Color: regex on color words
  - Size: regex on size patterns
  - Budget: regex on price patterns
  - Output: `[("material", "cotton", 0.95), ("color", "blue", 0.8)]`
  
- **Graph Traversal Search**:
  - Start from materialized constraints
  - SQL query: `SELECT products WHERE material="cotton" AND color="blue" AND price < 100`
  - Join relationship tables
  - Score by constraint match count (more matches = higher rank)
  
- **Attribute Question Sequencing**:
  - Track which attributes mentioned so far
  - Ask about unmentioned, high-discriminative-power attributes
  - Use attribute frequency stats: Material > Budget > Style > Color > Size
  
- **Profile-Aware Reranking**:
  - After retrieving candidates, rerank by user profile affinity
  - "Does this user typically buy silk or cotton? Boost silk."

**Why #3:**
- ✅ Highly deterministic (rules-based)
- ✅ Zero LLM/API dependency
- ✅ Transparent (can explain why product recommended)
- ✅ Fast (materialized relationships)
- ✅ Scales well to 50K products
- ✅ Traceability + auditability

**Expected Gains:** Hit Rate +25-40%, MRR +20-30%, MTTC -1.5 to -2.5 turns
**Technical Score:** 0.25-0.40 (2.3-3.7x better than baseline)
**Implementation:** 2-3 weeks (data engineering component)
**Lines of Code:** ~1500-2200 lines
**Tradeoff:** Slower for Browsing scenarios (needs explicit attributes)

---

### **Architecture #4: RL Policy (Offline-Trained, No Live APIs)**
**Ranking: 4**

**Components:**
- **State Representation** (no live API needed):
  ```python
  state = {
      "turn": int (1-10),
      "conversation_history": list of messages,
      "top_k_candidates": list of 100 products,
      "user_profile_vector": [freq, rating, ...],
      "constraints_so_far": dict,
      "attributes_asked": set,
      "scenario_type": "buying|browsing|override"
  }
  ```
  
- **Offline RL Training** (on public 200-session dataset):
  - Precompute policy π(state → action) offline
  - Actions: {question to ask, attribute to ask about}
  - Reward: +1 for hit, scaled by (11 - turn)
  - Use policy gradient or Q-learning (scikit-learn or simple numpy)
  - No live APIs during inference
  
- **Policy Execution** (at test time):
  - Given state, lookup policy: action = π(state)
  - Execute action (ask question, return recommendations)
  - No training at test time
  - Completely deterministic after training
  
- **Fallback Heuristics**:
  - If confidence < 0.5, fall back to rule-based (Architecture #1)
  - Protects against policy overfitting to public set
  
- **Intent Override Handling**:
  - Policy trained to detect override signals
  - State includes "detected_override" flag
  - Different policy branch for post-override

**Why #4:**
- ✅ No external APIs at inference time
- ✅ Learns from public dataset (improves over hand-crafted rules)
- ✅ Potential to beat rule-based approaches
- ✅ Adapts automatically to different scenario types
- ⚠️ Risk: Overfitting to 200 public sessions
- ⚠️ Complex: Requires ML expertise

**Expected Gains:** Hit Rate +20-35%, MRR +15-25%, MTTC -0.5 to -2 turns
**Technical Score:** 0.20-0.40 (1.9-3.7x better than baseline)
**Implementation:** 2-3 weeks (requires ML experience)
**Lines of Code:** ~800-1200 lines
**Training Time:** <5 minutes offline

---

### **Architecture #5: Ensemble of Rules-Based Systems**
**Ranking: 5 (Fallback/Robustness)**

**Components:**
- **System A: BM25 Pure Keyword Matching**
  - Baseline from starter code
  - Fast, reliable baseline
  
- **System B: Constraint-Based Filtering** (#1 above)
  - Explicit constraint matching
  - High precision for explicit requirements
  
- **System C: Product Similarity** (pre-computed)
  - For each product, pre-compute 5-10 similar products
  - Use Jaccard similarity on (categories, features)
  - When user likes a product, recommend similar ones
  
- **Ensemble Strategy**:
  - Normalize scores from each system to [0, 1]
  - Weights: 0.30×BM25 + 0.50×Constraint + 0.20×Similarity
  - Rerank top-100 by ensemble score
  - Return top-10
  
- **Adaptive Weighting by Scenario**:
  - Buying: increase Constraint weight to 0.70 (explicit is key)
  - Browsing: increase Similarity weight to 0.40 (profile-based fallback)
  - Override: pivot weights to new constraints

**Why #5:**
- ✅ Combines strengths of multiple approaches
- ✅ Robustness: if one system fails, others compensate
- ✅ No external dependencies
- ✅ Deterministic and auditable
- ⚠️ Requires tuning 3 weights

**Expected Gains:** Hit Rate +30-45%, MRR +25-35%, MTTC -1.5 to -2.5 turns
**Technical Score:** 0.30-0.45 (2.8-4.2x better than baseline)
**Implementation:** 2-3 weeks
**Lines of Code:** ~1200-1800 lines

---

## COMPARISON: Viable No-API Architectures

| Architecture | Hit Rate | MTTC | Token Cost | Implementation | Best For |
|---|---|---|---|---|---|
| #1 Constraint | 35-50% | 6-7 | 0 | 1-2 weeks | **Speed + Buying** |
| #2 Two-Stage | 30-45% | 6-7 | 0 | 1-2 weeks | Browsing + natural flow |
| #3 Knowledge Graph | 25-40% | 8-9 | 0 | 2-3 weeks | Transparency + audit |
| #4 RL Policy | 20-35% | 7-8 | 0 | 2-3 weeks | Learning + adaption |
| #5 Ensemble | 30-45% | 7-8 | 0 | 2-3 weeks | Robustness |

---

## RECOMMENDED IMPLEMENTATION PATH (NO-API)

### **Phase 1 (Week 1): Build Architecture #1 Baseline**
```
1. Constraint extraction (regex patterns for material, color, budget, size, style)
2. BM25 filtering using SQLite FTS5 (extend baseline)
3. Question bank (pre-written templates for each attribute)
4. Session state management
5. Basic override detection
```
**Expected Result:** 35-50% hit rate, 0.03-0.04 MRR, 6-7 MTTC

### **Phase 2 (Week 2): Refine #1 + Add Two-Stage Fallback**
```
1. Improve constraint parser (handle more edge cases)
2. Add profile-aware filtering (optional boost based on user_profile)
3. Implement Stage 1 vs Stage 2 routing for Browsing scenarios
4. Enhance override detection (more patterns)
5. Optimize question sequencing (information gain)
```
**Expected Result:** 40-55% hit rate, 0.04-0.05 MRR, 5-6 MTTC

### **Phase 3 (Week 3): Add Ensemble Components**
```
1. Implement product similarity index (Jaccard distance)
2. Add ensemble weighting (0.30×BM25 + 0.50×Constraint + 0.20×Similarity)
3. Scenario-adaptive weighting (Buying vs Browsing)
4. Fine-tune weights on public dataset (5-fold CV)
```
**Expected Result:** 45-60% hit rate, 0.05-0.06 MRR, 4-5 MTTC

### **Phase 4 (Week 4): Polish + Fallbacks**
```
1. Implement robust error handling
2. Add fallback strategies (if all systems fail)
3. Scenario-specific optimizations
4. Performance monitoring + logging
5. Final tuning pass
```
**Expected Final Result:** 50-65% hit rate, 0.05-0.07 MRR, 3.5-4.5 MTTC

---

## DECISION TREE: Choose Your Architecture (NO-API)

```
START
│
├─ Do you have <1 week?
│  ├─ YES → #1 (Constraint-Driven) - quick & effective
│  └─ NO ↓
│
├─ Do you want maximum simplicity?
│  ├─ YES → #1 (Constraint-Driven) - just regex + BM25
│  ├─ NO ↓
│
├─ Is robustness critical?
│  ├─ YES → #5 (Ensemble) - multiple fallbacks
│  ├─ NO ↓
│
├─ Do you understand ML/RL?
│  ├─ YES → #4 (RL Policy) - potential to beat rules
│  ├─ NO → #1 (Constraint) or #2 (Two-Stage)
│  └─ (MAYBE) ↓
│
├─ Does your team need transparency/audit trail?
│  ├─ YES → #3 (Knowledge Graph)
│  └─ NO → #1 (Constraint)

RECOMMENDED PATHS:
- Fastest/Best: #1 (Week 1) + #2 (Week 2) combo
- High Robustness: #1 + #5 (Ensemble)
- Maximum Score: #1 + #2 + #5 (3-way ensemble)
- ML Approach: #4 (RL Policy)
```

---

## CRITICAL SUCCESS FACTORS (NO-API Edition)

1. **Constraint Extraction**: Regex patterns must be comprehensive
   - Materials: "cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon"
   - Colors: full spectrum
   - Budget: flexible ranges ("$50-100", "under $200", "around $75")
   - Size: various formats ("M", "medium", "size 8", "32-inch")

2. **Question Quality**: One attribute per turn, max 10 turns
   - Sequencing matters: high-discriminative attributes first
   - Recommended order: Budget → Use Case → Material → Style → Color → Size

3. **Constraint Satisfaction**: Ensure top-10 match user's explicit requirements
   - Don't return products that violate stated constraints
   - Better to have 3 accurate results than 10 mediocre ones

4. **Intent Override Handling**: Detect & adapt on turn 3-4
   - Watch for: "Actually", "Wait", "Ignore", "Changed my mind"
   - Swap constraint sets, re-filter candidates
   - Test this extensively

5. **Profile Personalization**: Use anonymized user_profile signals
   - user_profile contains: purchase_frequency, rating_patterns
   - Bias results toward products aligned with user's preferences
   - This helps in Browsing + Boundary scenarios

6. **Early Filtering**: Reduce candidate pool quickly
   - After turn 2-3: go from 50K → 500-1000 candidates
   - After turn 5-6: go from 1000 → 50-100 candidates
   - This enables good ranking by turn 10

7. **Fallback Strategies**: What if constraint extraction fails?
   - Fall back to pure BM25 keyword matching
   - Or use profile-based recommendations
   - Never return empty list

---

## FAQ: NO-API Edition

**Q: Can I use Sentence-Transformers or other local libraries?**
A: Yes! Sentence-Transformers runs locally (no API). But it's not required for competitive performance. #1 Constraint-Driven can achieve 40-50% without embeddings.

**Q: Should I pre-embed all 50K products?**
A: Only if you're doing #4 (RL Policy) or hybrid approach. For pure #1 or #2, not necessary. Adds ~2-3 weeks to implementation.

**Q: Can I use the local evaluator to test my implementation?**
A: Yes! The evaluator is completely local. Run: `python3 -m evaluator.local_evaluator`

**Q: What if my hit rate is stuck at 30%?**
A: Likely issues:
- Poor constraint extraction → improve regex patterns
- Wrong question sequencing → reorder attributes
- Ranking problem → better rerank by constraint match count
- Solution: Move to #5 (Ensemble) or add product similarity

**Q: How do I handle the "I don't have a preference" boundary scenario?**
A: Fall back to user profile + popular products. If user says "I don't prefer material", recommend products that match other constraints + high-rating products for that category.

**Q: Can I use scikit-learn or other Python libraries?**
A: Yes! Scikit-learn, numpy, scipy all run locally. No internet needed.

---

## SUCCESS CRITERIA

**Minimum Viable Agent:**
- Hit Rate: 25-35%
- MRR: 0.015-0.025
- MTTC: 8-9
- Technical Score: 0.17-0.25 (1.6-2.3x baseline)
- Implementation: 1-2 weeks
- Architecture: #1 (Constraint-Driven)

**Competitive Agent:**
- Hit Rate: 40-50%
- MRR: 0.03-0.04
- MTTC: 6-7
- Technical Score: 0.35-0.50 (3.3-4.7x baseline)
- Implementation: 2-3 weeks
- Architecture: #1 + #2 (Two-Stage fallback)

**High-Performance Agent:**
- Hit Rate: 50-65%
- MRR: 0.05-0.07
- MTTC: 3.5-4.5
- Technical Score: 0.55-0.70 (5.1-6.5x baseline)
- Implementation: 3-4 weeks
- Architecture: #1 + #2 + #5 (Ensemble)

---

## WHAT'S BEEN REMOVED (Due to No-API Constraint)

❌ **Architecture #1 (Hybrid with LLM)** - Requires external LLM API
❌ **Architecture #9 (Few-Shot CoT)** - Requires external LLM API
❌ **Architecture #4 (Dense Vectors)** - Requires external embedding API (unless self-hosted)
❌ **Architecture #7 (Ensemble with LLM)** - Requires external LLM

**These are now ranked 1-5 among NO-API architectures instead.**

---

