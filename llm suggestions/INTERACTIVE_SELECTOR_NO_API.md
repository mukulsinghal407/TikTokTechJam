# Interactive Architecture Selector Guide (NO EXTERNAL APIs)

## ⚠️ Constraint: Local Python Only
- ❌ No external LLM APIs (OpenAI, Claude, etc.)
- ❌ No external embedding APIs
- ❌ No vector databases (Pinecone, Weaviate)
- ✅ Local Python, SQLite, standard libraries only

---

## Viable Architectures (Only 5 Remain)

1. **#1 Constraint-Driven Filtering** ← RECOMMENDED
2. **#2 Two-Stage Ranking**
3. **#3 Knowledge Graph + Rules**
4. **#4 RL Policy (Offline-Trained)**
5. **#5 Ensemble of Rule Systems**

---

## How to Use This Guide

You can ask about architectures by specifying ONE attribute at a time. The system will re-rank and explain why certain architectures excel.

**Ask questions like:**
- "Show me architectures ranked by hit_rate"
- "Which one handles buying scenario best?"
- "Rank by implementation time"
- "Tell me about override handling"
- "What about Browsing scenarios?"

---

## AVAILABLE QUERY ATTRIBUTES

### 1. **Performance Metrics** (Re-rank by predicted scores)
   - `hit_rate`: Raw product recovery capability
   - `mrr`: Ranking quality (reciprocal rank)
   - `mttc`: Turns to find product
   - `efficiency`: (11 - MTTC) / 10 normalized efficiency
   - `technical_score`: 0.50×HitRate + 0.30×MRR + 0.20×Efficiency

### 2. **Cost Factors** (Re-rank by resource usage)
   - `implementation_time`: Days/weeks to implement
   - `code_complexity`: Lines of code + difficulty
   - `compute_cost`: CPU/RAM requirements
   - `memory_usage`: Peak RAM during operation
   - `latency_per_turn`: Response time

### 3. **Scenario Performance** (Re-rank by scenario type)
   - `buying_scenario`: Explicit constraint given early (40% of dataset)
   - `browsing_scenario`: Vague initial message (40%)
   - `intent_override_scenario`: Preference change on turn 3-4 (15%)
   - `boundary_scenario`: "No preference" handling (5%)

### 4. **Technical Capabilities** (Re-rank by feature set)
   - `determinism`: Predictable, auditable decisions
   - `personalization`: Uses user profile effectively
   - `constraint_handling`: Explicit constraint matching
   - `override_detection`: Catches preference changes
   - `fallback_robustness`: Handles edge cases gracefully

### 5. **Implementation Factors** (Re-rank by practical concerns)
   - `setup_time`: Days to productionize
   - `debugging_difficulty`: Easy to diagnose failures?
   - `team_expertise_required`: Skills needed (SWE vs ML)
   - `local_only`: Works without external APIs?
   - `production_readiness`: Ready to ship now?

### 6. **Scenario-Specific Excellence** (Re-rank by scenario mastery)
   - `buying_mastery`: Best for explicit constraints
   - `browsing_mastery`: Best for vague queries
   - `override_mastery`: Best at detecting intent changes
   - `balanced_performance`: Best all-around

---

## REAL-TIME RANKING SCENARIOS

### **Scenario A: Maximize Hit Rate (Winning the Competition)**

**Query:** "Rank by hit_rate"

**Expected Ranking:**
1. **#1 Constraint-Driven** - 35-50% (explicit constraints = high precision)
2. **#2 Two-Stage** - 30-45% (browsing fallback helps)
3. **#5 Ensemble** - 30-45% (multiple signals)
4. **#4 RL Policy** - 20-35% (learned strategy, high variance)
5. **#3 Knowledge Graph** - 25-40% (needs explicit attributes)

**Explanation:**
#1 dominates because Buying scenario (40% of data) has explicit constraints that #1 extracts perfectly. #2 helps balance with Browsing (40%). #5 ensemble adds robustness but adds complexity. #4 and #3 are riskier for pure hit rate.

---

### **Scenario B: Minimize Implementation Time (Quick MVP)**

**Query:** "Rank by implementation_time"

**Expected Ranking:**
1. **#1 Constraint-Driven** - 1-2 weeks (simple regex + BM25)
2. **#2 Two-Stage** - 1-2 weeks (filtering pipeline)
3. **#5 Ensemble** - 2-3 weeks (integrating 3 systems)
4. **#4 RL Policy** - 2-3 weeks (ML training component)
5. **#3 Knowledge Graph** - 2-3 weeks (data engineering)

**Explanation:**
#1 is fastest: just regex patterns + BM25 filtering (already in baseline). #2 similar but adds Stage 1 vs Stage 2 logic. #5 requires tuning 3 systems. #4 needs RL expertise. #3 requires building materialized attribute tables.

---

### **Scenario C: Best for Buying Scenarios (40% of dataset - EASIEST)**

**Query:** "Rank by buying_scenario"

**Expected Ranking:**
1. **#1 Constraint-Driven** - 70% hit rate (perfect for explicit constraints)
2. **#3 Knowledge Graph** - 50% hit rate (KG traversal for constraints)
3. **#5 Ensemble** - 55% hit rate (constraint module strong)
4. **#2 Two-Stage** - 50% hit rate (can work, less optimized)
5. **#4 RL Policy** - 45% hit rate (learned but less certain)

**Explanation:**
Buying scenario = customer says "I want cotton, size M, budget $50-100" on turn 1. #1 extracts these constraints perfectly via regex → BM25 filter → boom, right products. #3 can do it via KG but overkill. #2 doesn't optimize for Buying. #4 depends on training quality.

---

### **Scenario D: Best for Browsing Scenarios (40% of dataset - HARDEST)**

**Query:** "Rank by browsing_scenario"

**Expected Ranking:**
1. **#2 Two-Stage** - 40% hit rate (coarse→fine exploration)
2. **#5 Ensemble** - 35% hit rate (profile similarity helps)
3. **#4 RL Policy** - 30% hit rate (learned strategy)
4. **#1 Constraint-Driven** - 25% hit rate (vague queries = no constraints)
5. **#3 Knowledge Graph** - 15% hit rate (needs attribute hints)

**Explanation:**
Browsing scenario = "I'm looking for something comfy but trendy" (no explicit constraints). #1 gets stuck because regex finds nothing. #2 shines: broadly filter → ask targeted questions → narrow down. #5 can fallback to profile. #4 learned to question systematically. #3 completely lost without attributes.

---

### **Scenario E: Intent Override Handling (15% of dataset - CRITICAL)**

**Query:** "Rank by intent_override_scenario"

**Expected Ranking:**
1. **#1 Constraint-Driven** - 40% hit rate (state machine tracks constraint swaps)
2. **#5 Ensemble** - 35% hit rate (multiple systems adapt)
3. **#4 RL Policy** - 35% hit rate (trained to handle override)
4. **#2 Two-Stage** - 30% hit rate (less explicit override handling)
5. **#3 Knowledge Graph** - 25% hit rate (KG swap complex)

**Explanation:**
Override on turn 3-4: "Actually, forget material. I really need machine-washable." 
#1 detects this → swaps constraint set → re-filters. Perfect.
#5 multiple systems adapt together.
#4 learned to recognize override signals (maybe).
#2 has to restart its stages.
#3 has to rebuild KG query.

---

### **Scenario F: Balanced Across All Scenarios (Highest Composite Score)**

**Query:** "Rank by technical_score"

**Expected Ranking:**
1. **#1 Constraint-Driven** - 0.40-0.50 (40-50% hit, strong on Buying)
2. **#2 Two-Stage** - 0.30-0.45 (30-45% hit, strong on Browsing)
3. **#5 Ensemble** - 0.30-0.45 (balanced across all)
4. **#4 RL Policy** - 0.20-0.40 (high variance, risky)
5. **#3 Knowledge Graph** - 0.25-0.40 (specialized, less flexible)

**Explanation:**
#1 wins because Buying is 40% of dataset and #1 crushes it. The technical score weights heavily on hit rate. #2 catches overflow from Browsing (40%). Ensemble balanced but doesn't specialize. RL risky due to limited training data.

---

## HOW THE SYSTEM HANDLES YOUR ATTRIBUTE CHANGE (MID-SESSION OVERRIDE)

When you switch from one attribute to another mid-conversation:

**Example flow:**

**Turn 1:** "Rank by hit_rate"
→ System returns: #1, #2, #5, #4, #3

**Turn 2:** "Actually, we only have 1 week"
→ System re-ranks by implementation_time: #1, #2, #5, #4, #3 (same order, actually!)
→ "Good news: fastest approaches also score high!"

**Turn 3:** "But Browsing scenarios are failing. What do I do?"
→ System re-ranks by browsing_scenario: #2, #5, #4, #1, #3
→ "For Browsing: #2 Two-Stage is best, but keep #1 as Buying fallback"
→ Recommendation: Implement #1 week 1, add #2 week 2

**Turn 4:** "Wait, intent override is critical for us. Can we handle it?"
→ System re-ranks by intent_override_scenario: #1, #5, #4, #2, #3
→ "#1 and #5 both handle override well"
→ Recommendation: Start with #1, add #5 (Ensemble) for override robustness

**Key insight:** The system handles these overrides by:
- Tracking which attribute you care about now
- Re-sorting all 5 architectures by new criterion
- Explaining why the ranking changed
- Offering combo approaches when multiple attributes matter

---

## MULTI-ATTRIBUTE QUERIES

If you provide 2+ attributes, the system uses weighted scoring:

**Example: "I want high hit rate AND low implementation time"**
→ Interpreted as: 50% Hit Rate + 50% Implementation Speed
→ Re-ranked by composite score

**Expected composite ranking:**
1. **#1 Constraint-Driven** - Best hit rate (35-50%) + Fast (1-2 weeks)
2. **#2 Two-Stage** - Good hit rate (30-45%) + Fast (1-2 weeks)
3. **#5 Ensemble** - Good hit rate (30-45%) + Medium (2-3 weeks)
4. **#4 RL Policy** - Risky hit rate (20-35%) + Medium (2-3 weeks)
5. **#3 Knowledge Graph** - Lower hit rate (25-40%) + Slower (2-3 weeks)

**Explanation:** #1 wins both criteria. #2 trades slightly lower hit for browsing fallback (still fast).

---

## MULTI-TURN CONVERSATION EXAMPLES

### **Conversation #1: Pragmatic SWE Team (1 week, no ML)**

```
Turn 1 (You): "Rank by implementation_time"
System: #1 (1-2 weeks), #2 (1-2 weeks), #5 (2-3 weeks), #4 (2-3 weeks), #3 (2-3 weeks)
Response: "You can implement #1 in 1-2 weeks!"

Turn 2 (You): "OK, but what's the hit rate?"
System: Re-ranks by hit_rate: #1 (35-50%), #2 (30-45%), #5 (30-45%), #3 (25-40%), #4 (20-35%)
Response: "#1 is both fastest AND has highest hit rate. Win-win!"

Turn 3 (You): "Is 35-50% competitive enough?"
System: "Compared to baseline (12.5%), you're 2.8-4x better. Could be competitive."
"Want to add #2 (Two-Stage) week 2? Could push to 40-55%."

Turn 4 (You): "Yes, let's do #1 week 1, #2 week 2. What should I implement first?"
System: [Provides implementation roadmap and code structure for #1 + #2]
```

### **Conversation #2: Research Team (Time flexible, want to try ML)**

```
Turn 1 (You): "Rank by hit_rate"
System: #1 (35-50%), #2 (30-45%), #5 (30-45%), #3 (25-40%), #4 (20-35%)

Turn 2 (You): "Can we use RL to learn better?"
System: "#4 RL Policy could work but risky: only 200 training sessions.
        Better: Start #1, then try #4 week 3 as experiment."

Turn 3 (You): "What about knowledge graph? Seems transparent."
System: Re-ranks by determinism: #3 (100% rule-based), #1 (95% rule-based), #5, #4, #2
"#3 is most transparent but weaker on hit rate (25-40% vs #1's 35-50%)."
"Tradeoff: hit rate vs auditability. #1 is best of both worlds."

Turn 4 (You): "OK, implement #1 as baseline, add #3 as explainability fallback?"
System: [Provides joint implementation strategy: #1 primary + #3 for audit trail]
```

### **Conversation #3: Competitive Team (Want to maximize score)**

```
Turn 1 (You): "Rank by technical_score"
System: #1 (0.40-0.50), #2 (0.30-0.45), #5 (0.30-0.45), #3 (0.25-0.40), #4 (0.20-0.40)

Turn 2 (You): "Can we beat 0.50?"
System: "#1 top end is 0.50. To go higher (0.55-0.65), need hybrid approach."
"But no external APIs... Option: #1 + #2 + #5 (ensemble local-only)"

Turn 3 (You): "How long for #1 + #2 + #5 combo?"
System: "#1 week 1-2, #2 week 2, #5 week 3 = 3 weeks total"
"Expected: 0.45-0.55 technical score (50-65% hit rate)"

Turn 4 (You): "Let's try it. What's the implementation order?"
System: [Provides 3-phase implementation plan: Phase 1 (#1), Phase 2 (#2), Phase 3 (#5 ensemble)]
```

---

## EXPECTED OUTPUT FORMAT (After You Ask an Attribute Question)

When you ask: "Show me architectures ranked by [ATTRIBUTE]"

**System response will be:**

```
RANKING BY: [Your Attribute]
==================================================

🥇 #[Number] - [Architecture Name]
   Score: [Value/Range]
   Why best: [2-3 sentences explaining why this excels at your attribute]
   Tradeoff: [What this architecture sacrifices]
   Implementation: [Timeline]
   
🥈 #[Number] - [Architecture Name]
   ...

🥉 #[Number] - [Architecture Name]
   ...

[4] #[Number] - [Architecture Name]
   ...

[5] #[Number] - [Architecture Name]
   ...

==================================================
KEY INSIGHT: [Why this ranking makes sense / Common pattern]

NEXT STEPS:
- If you want [related attribute], consider instead: #X
- If you want to balance multiple goals, try combining #X + #Y
- To implement fastest, start with #Z
- Estimated composite score: Y (based on multiple attributes)
```

---

## QUICK DECISION MATRIX

**Choose by Your Priority:**

| **Your Priority** | **Best Architecture** | **Hit Rate** | **Time** | **Why** |
|---|---|---|---|---|
| **Win the competition** | #1 (Constraint) | 35-50% | 1-2w | Beats Buying (40%) |
| **Fastest MVP** | #1 (Constraint) | 35-50% | 1-2w | Same! |
| **Handle Browsing best** | #2 (Two-Stage) | 30-45% | 1-2w | Coarse→fine for vague |
| **Most robust** | #5 (Ensemble) | 30-45% | 2-3w | 3 fallbacks |
| **Most transparent** | #3 (Knowledge Graph) | 25-40% | 2-3w | 100% auditable rules |
| **Try ML approach** | #4 (RL Policy) | 20-35% | 2-3w | High variance, risky |
| **Everything matters equally** | #1 + #2 combo | 40-55% | 2-3w | Best balanced |

---

## TIPS FOR ASKING EFFECTIVE QUESTIONS

1. **Be specific about your constraint:**
   - ✅ Good: "Rank by hit_rate"
   - ❌ Bad: "Which is best?"
   
2. **You can ask about multiple attributes, but system re-ranks each time:**
   - ✅ Good: "First, show me [attr1], then [attr2]"
   - ❌ Bad: Asking 5 questions at once

3. **Mention your team context for better recommendations:**
   - "I'm alone" → prioritize #1 (simplest)
   - "I have 2 SWEs" → prioritize #1 + #2
   - "I have ML person" → consider #4 (RL)
   - "We have 1 week" → prioritize #1 or #2

4. **If you change your mind mid-session:**
   - Just say: "Actually, let me optimize for [NEW ATTRIBUTE] instead"
   - System will re-rank and explain the shift

5. **Ask about combinations:**
   - "Can I combine #1 and #2?" → Yes! Recommended.
   - "Should I try #4 after #1?" → Yes! Week 3 experiment.

---

## ATTRIBUTE INTERACTIONS (Bonus Insights)

**If you ask about Hit Rate (#1 ranks first):**
- Then ask about Override → #1 still ranks first (handles override well)
- Then ask about Browsing → #2 suddenly important (balancing act)
- Then ask about Time → #1 still wins (both fast + high hit rate)

**If you ask about Browsing (A #2 ranks first):**
- Then ask about Buying → #1 jumps to top (dominates Buying)
- Then ask about Time → both #1 and #2 equally fast (both viable)
- Then ask about Override → #1 slightly better

**If you ask about Override (A #1 ranks first):**
- Then ask about Hit Rate → #1 still first (good across board)
- Then ask about Browsing → #2 catches up (both needed)
- Recommendation: Implement both #1 + #2

---

## ARCHITECTURE SPECIALIZATIONS (Quick Lookup)

```
When to use #1 (Constraint-Driven):
- Buying scenarios dominant in your test set
- You want fast implementation
- Your team is SWE-only (no ML)
- You need deterministic results
- Hit rate is your top metric

When to use #2 (Two-Stage):
- Browsing scenarios matter
- You want natural user experience
- Early stage (coarse) vs late stage (fine) differentiation helps
- You have time for 1-2 weeks

When to use #3 (Knowledge Graph):
- Transparency/audit trail critical
- You have data engineer on team
- You want to explain "why" for each recommendation
- 2-3 weeks implementation acceptable

When to use #4 (RL Policy):
- You have ML expertise
- You want to learn from public dataset (risky!)
- Experimentation is fun
- You have 2-3 weeks
- Hit rate variance acceptable

When to use #5 (Ensemble):
- You want robustness (fallbacks matter)
- You have time for 2-3 weeks
- You want to combine strengths (#1 for Buying + #2 for Browsing)
- "Better safe than sorry" mentality
```

---

