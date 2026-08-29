# Interactive Architecture Selector Guide

## How to Use This Guide

You can ask about architectures by specifying ONE attribute at a time. The system will re-rank and explain why certain architectures excel at that criterion.

**Ask questions like:**
- "Show me architectures that minimize MTTC"
- "Which architecture handles intent override best?"
- "Rank by token cost"
- "What about scenario-specific performance?"
- "Tell me about Browsing scenario success"

---

## AVAILABLE QUERY ATTRIBUTES

### 1. **Performance Metrics** (Re-rank by predicted scores)
   - `hit_rate`: Raw product recovery capability
   - `mrr`: Ranking quality (reciprocal rank)
   - `mttc`: Turns to find product
   - `efficiency`: (11 - MTTC) / 10 normalized efficiency
   - `technical_score`: 0.50×HitRate + 0.30×MRR + 0.20×Efficiency

### 2. **Cost Factors** (Re-rank by resource usage)
   - `token_cost_per_turn`: LLM token consumption
   - `latency`: Response time
   - `implementation_effort`: Days/weeks to implement
   - `computational_cost`: GPU/server resources needed
   - `api_dependency`: How many external APIs required

### 3. **Scenario Performance** (Re-rank by scenario type)
   - `buying_scenario`: Explicit constraint given early (40% of dataset)
   - `browsing_scenario`: Vague initial message (40%)
   - `intent_override_scenario`: Preference change on turn 3-4 (15%)
   - `boundary_scenario`: "No preference" handling (5%)

### 4. **Technical Capabilities** (Re-rank by feature set)
   - `semantic_understanding`: Captures paraphrasing & implicit intent
   - `determinism`: Predictable, auditable decisions
   - `personalization`: Uses user profile effectively
   - `fallback_robustness`: Handles edge cases gracefully
   - `reranking_quality`: Final ranking accuracy
   - `constraint_handling`: Explicit vs. implicit constraint matching

### 5. **Implementation Factors** (Re-rank by practical concerns)
   - `setup_time`: Days to productionize
   - `debugging_difficulty`: Hard to diagnose failures?
   - `team_expertise_required`: Skills needed (ML, NLP, SWE)
   - `data_requirements`: Training data needed
   - `production_readiness`: Ready to ship now?

### 6. **Intent Override Handling** (Re-rank by override success)
   - `override_detection_speed`: Turns to detect preference change
   - `override_adaptation_speed`: Turns to apply new constraints
   - `false_positive_rate`: Mistakes override for clarification?
   - `false_negative_rate`: Misses actual overrides?

---

## REAL-TIME RANKING SCENARIOS

### **Scenario A: You want to MAXIMIZE Hit Rate**

**Query:** "Rank architectures by hit_rate"

**Expected Ranking (Highest → Lowest Hit Rate):**
1. **Architecture #1** (Multi-Strategy Hybrid) - ~50-60% + semantic + LLM rewriting
2. **Architecture #3** (Multi-Route Classification) - ~45-55% + scenario routing
3. **Architecture #2** (Constraint-Driven) - ~40-50% + deterministic filtering
4. **Architecture #7** (Ensemble) - ~40-50% + multiple signals combined
5. **Architecture #6** (Two-Stage Ranking) - ~35-45% + coarse→fine
6. **Architecture #4** (Dense Retrieval) - ~30-45% + profile personalization
7. **Architecture #5** (Knowledge Graph) - ~25-40% + KG traversal
8. **Architecture #8** (RL Policy) - ~25-45% + learned policy (high variance)
9. **Architecture #9** (Few-Shot CoT) - ~20-40% + LLM generalization
10. **Architecture #10** (Active Learning) - ~15-30% + tuning iterations

**Explanation:**
Architectures #1, #3, #2 combine multiple retrieval signals (keyword + semantic + constraint-based). They capture both explicit requirements and implicit preferences. #7 ensemble also strong but requires tuning weights. Pure semantic (#4) works well for vague queries but less good for explicit constraints.

---

### **Scenario B: You want MINIMUM Token Cost**

**Query:** "Rank architectures by token_cost_per_turn"

**Expected Ranking (Lowest → Highest Cost):**
1. **Architecture #4** (Dense Retrieval) - ~0 LLM tokens (embedding-only)
2. **Architecture #5** (Knowledge Graph) - ~0 LLM tokens (rule-based lookup)
3. **Architecture #2** (Constraint-Driven) - ~50-100 tokens/turn (only small LLM calls)
4. **Architecture #6** (Two-Stage Ranking) - ~50-150 tokens/turn
5. **Architecture #3** (Multi-Route) - ~100-200 tokens/turn (LLM routing)
6. **Architecture #8** (RL Policy) - ~50-150 tokens/turn (no live LLM if offline)
7. **Architecture #1** (Hybrid) - ~200-300 tokens/turn (query rewriting)
8. **Architecture #7** (Ensemble) - ~200-300 tokens/turn (4 models)
9. **Architecture #9** (Few-Shot CoT) - ~250-400 tokens/turn (full LLM reasoning)
10. **Architecture #10** (Active Learning) - ~100-500+ tokens/turn (high variance)

**Explanation:**
If you need to minimize API costs: go with #4 or #5 (pre-computed, no LLM). If you can afford some LLM: #2 or #6 (structured queries, not full reasoning). #1 and #9 are most expensive due to full LLM generations.

---

### **Scenario C: You want FASTEST Implementation**

**Query:** "Rank architectures by implementation_effort"

**Expected Ranking (Fastest → Slowest):**
1. **Architecture #9** (Few-Shot CoT) - ~3-5 days (just prompt engineering)
2. **Architecture #2** (Constraint-Driven) - ~1-2 weeks (rules engine)
3. **Architecture #6** (Two-Stage Ranking) - ~1-2 weeks (filtering pipeline)
4. **Architecture #1** (Hybrid Retrieval) - ~2-3 weeks (integration of 2 systems)
5. **Architecture #3** (Multi-Route) - ~2-3 weeks (routing logic + fallbacks)
6. **Architecture #10** (Active Learning) - ~3-4 weeks (experimentation + tuning)
7. **Architecture #7** (Ensemble) - ~3-4 weeks (tuning 4 models + weights)
8. **Architecture #8** (RL Policy) - ~4-6 weeks (data prep + training)
9. **Architecture #4** (Dense Retrieval) - ~2-4 weeks (vector DB setup)
10. **Architecture #5** (Knowledge Graph) - ~4-8 weeks (data engineering)

**Explanation:**
#9 is quickest if you have LLM API access. #2 is fastest for rule-based approach. #5 takes longest due to KG construction. If time is critical and you're a small team, pick #9 or #2.

---

### **Scenario D: Intent Override Scenarios (15% of dataset)**

**Query:** "Rank architectures by intent_override_success"

**Expected Ranking (Best → Worst):**
1. **Architecture #3** (Multi-Route) - Explicit override detection on turn 3-4
2. **Architecture #2** (Constraint-Driven) - Constraint state machine handles swaps
3. **Architecture #1** (Hybrid) - LLM recognizes "Actually..." patterns
4. **Architecture #7** (Ensemble) - Multiple signals catch override
5. **Architecture #6** (Two-Stage) - Can pivot filters at stage boundary
6. **Architecture #8** (RL Policy) - Learned to handle override (if trained well)
7. **Architecture #5** (Knowledge Graph) - KG can swap constraint sets
8. **Architecture #4** (Dense Retrieval) - Struggles with explicit preference changes
9. **Architecture #10** (Active Learning) - Depends on tuning; variable
10. **Architecture #9** (Few-Shot CoT) - LLM hallucination risk on override

**Explanation:**
#3 and #2 have explicit intent override detection logic. #1 can recognize language patterns. #4 struggles because it relies on embedding continuity. #9 might confuse override signals or fail to reset correctly.

---

### **Scenario E: Browsing Scenarios (40% of dataset - HARDEST)**

**Query:** "Rank architectures by browsing_scenario_success"

**Expected Ranking (Best for vague queries):**
1. **Architecture #1** (Hybrid) - LLM extracts implicit features from vague text
2. **Architecture #4** (Dense Retrieval) - Semantic embeddings capture vague intent
3. **Architecture #3** (Multi-Route) - Aggressive questioning strategy for browsing
4. **Architecture #6** (Two-Stage) - Broad stage-1 filtering then refinement
5. **Architecture #2** (Constraint-Driven) - Can work but depends on extracted constraints
6. **Architecture #7** (Ensemble) - Profile + semantic signals help
7. **Architecture #8** (RL Policy) - Learns good question sequences
8. **Architecture #5** (Knowledge Graph) - Good if customer hints at attributes
9. **Architecture #9** (Few-Shot CoT) - Depends on prompt quality
10. **Architecture #10** (Active Learning) - Depends on team's ability to iterate

**Explanation:**
#1 and #4 are best because they handle vague/semantic understanding. #2 struggles in pure browsing because no explicit constraints to extract. #5 needs attribute hints to work well.

---

### **Scenario F: Buying Scenarios (40% of dataset - EASIEST)**

**Query:** "Rank architectures by buying_scenario_success"

**Expected Ranking (Best for explicit constraints):**
1. **Architecture #2** (Constraint-Driven) - Perfect for "hard constraint disclosed early"
2. **Architecture #3** (Multi-Route) - Buying route optimized for this
3. **Architecture #5** (Knowledge Graph) - KG traversal for constraints
4. **Architecture #6** (Two-Stage) - Constraint filtering in stage 1
5. **Architecture #1** (Hybrid) - Query rewriting + constraint matching
6. **Architecture #7** (Ensemble) - Multiple signals catch constraint
7. **Architecture #4** (Dense Retrieval) - Can work if constraint embeds well
8. **Architecture #8** (RL Policy) - Learned policy should excel here
9. **Architecture #10** (Active Learning) - Should improve with tuning
10. **Architecture #9** (Few-Shot CoT) - Less reliable than structured extraction

**Explanation:**
#2 dominates because Buying = explicit constraints = rule-based extraction is ideal. #3 has dedicated Buying route. #5 can traverse KG for constraints. Pure semantic approaches (#4, #9) less ideal because constraint might not embed perfectly.

---

## HOW THE SYSTEM HANDLES YOUR ATTRIBUTE CHANGE (MID-SESSION OVERRIDE)

When you switch from one attribute to another mid-conversation:

**Example flow:**

**Turn 1:** "Rank by hit_rate"
→ System returns: #1, #3, #2, #7, #6, #4, #5, #8, #9, #10

**Turn 2:** "Actually, minimize token cost instead"
→ System re-ranks: #4, #5, #2, #6, #3, #8, #1, #7, #9, #10
→ Note: #4 and #5 now top (0 LLM tokens)

**Turn 3:** "But we need to handle intent override perfectly"
→ System re-ranks: #3, #2, #1, #7, #6, #8, #5, #4, #10, #9
→ Note: #3 and #2 now top (explicit override detection)

**Turn 4:** "And our team only has 1 week to implement"
→ System re-ranks: #9, #2, #6, #1, #3, #10, #7, #8, #4, #5
→ Note: #9 fastest (few-shot CoT, 3-5 days)

**Key insight:** The system handles these overrides by:
- Tracking which attribute you care about now
- Clearing previous rankings
- Re-sorting all 10 architectures by new criterion
- Explaining why the top choice changed
- Offering "hybrid approaches" that balance multiple criteria

---

## MULTI-ATTRIBUTE QUERIES (Beyond One Attribute)

If you provide 2+ attributes, the system uses weighted scoring:

**Example: "I want high hit rate AND low token cost, but our team is small"**
→ Interpreted as: 40% Hit Rate + 30% Token Cost + 30% Implementation Speed
→ Re-ranked by weighted composite

**Expected composite ranking:**
1. **Architecture #2** - Great hit rate (40-50%), cheap (50-100 tokens), fast (1-2 weeks)
2. **Architecture #6** - Good hit rate (35-45%), cheap-ish (50-150 tokens), fast (1-2 weeks)
3. **Architecture #1** - Best hit rate (50-60%), expensive (200-300), slower (2-3 weeks)
4. **Architecture #3** - Good all-around (45-55%, 100-200 tokens, 2-3 weeks)
5. ...rest

**Explanation:** #2 wins composite because it's well-balanced. #1 has best hit rate but fails on token cost and speed.

---

## EXPECTED OUTPUT FORMAT (After You Ask an Attribute Question)

When you ask: "Show me architectures ranked by [ATTRIBUTE]"

**System response will be:**

```
RANKING BY: [Your Attribute]
==================================================

🥇 #[Number] - [Architecture Name]
   Performance: [Score/Range]
   Why best: [2-3 sentences explaining why this excels at your attribute]
   Tradeoff: [What this architecture sacrifices]
   
🥈 #[Number] - [Architecture Name]
   ...

🥉 #[Number] - [Architecture Name]
   ...

---

[5] #[Number] - [Architecture Name]
   ...

[Remaining architectures 6-10, more concisely]

==================================================
INSIGHT: [Why this ranking makes sense / Common pattern]

NEXT STEPS:
- If you want [related attribute], consider instead: #X
- If you want to balance multiple goals, try combining #X + #Y
- To implement fastest, start with #Z then improve to #Y
```

---

## COMMON MULTI-TURN CONVERSATIONS

### **Conversation #1: Pragmatic Team (You have 2 weeks, 1 LLM API, need results)**

```
Turn 1 (User): "Rank by implementation time"
System: #9 (few-shot), #2 (constraint), #6 (two-stage), ...
User: "OK, but we need to actually win the competition. Rank by hit rate now."

Turn 2 (User): "Rank by hit rate"
System: #1 (hybrid), #3 (multi-route), #2 (constraint), ...
User: "Can I do #1 in 2 weeks?"

Turn 3 (User): "Can you find me an architecture that scores high on both hit_rate AND has <2 week implementation?"
System: "Best composite option: #2 (constraint-driven) 
         - Hit rate: 40-50% (good, not best)
         - Implementation: 1-2 weeks (fast)
         - Token cost: cheap
         OR try #6 (two-stage) with same profile
         OR implement #2 week 1, then add #1 features week 2 for hybrid approach"
```

### **Conversation #2: Perfectionist Team (You want best score, time flexible)**

```
Turn 1 (User): "Rank by hit rate AND mrr"
System: #1 (hybrid), #3 (multi-route), #2 (constraint), ...
User: "How long to implement #1?"

Turn 2 (User): "Rank by technical_score (composite)"
System: #1 (hybrid) - 55-70% hit, 0.06-0.08 MRR, 4-5 MTTC, score: ~0.65
User: "What if we need to handle intent_override perfectly?"

Turn 3 (User): "Rank architectures that handle intent_override + high technical_score"
System: #3 (multi-route) - explicit override handling + 45-55% hit rate + score: ~0.55
        #1 (hybrid) - semantic override detection + 50-60% hit rate + score: ~0.65
        Recommendation: Implement #1 with explicit override detection from #3
```

### **Conversation #3: Cost-Conscious Team (Minimal API spend)**

```
Turn 1 (User): "Rank by token_cost_per_turn"
System: #4 (dense, 0 tokens), #5 (knowledge graph, 0 tokens), #2 (50-100 tokens), ...
User: "But dense retrieval hit rate might not be competitive. Can I get good hit rate with <100 tokens/turn?"

Turn 2 (User): "Find me architectures with <100 tokens/turn AND hit_rate >40%"
System: "Best options:
         - #2 (constraint-driven): 40-50% hit rate, 50-100 tokens
         - #6 (two-stage): 35-45% hit rate, 50-150 tokens
         Other low-cost options: #4 (dense), #5 (KG)
         Consider: #2 baseline + #4 dense retrieval combo = low cost, higher hit rate"
User: "OK, let's do #2 + #4. How should I implement?"

Turn 3: [System would explain hybrid #2+#4 implementation]
```

---

## TIPS FOR ASKING EFFECTIVE QUESTIONS

1. **Be specific about your constraint:**
   - ✅ Good: "Rank by token_cost_per_turn"
   - ❌ Bad: "Which is cheapest?"
   
2. **You can ask about multiple attributes, but system re-ranks each time:**
   - ✅ Good: "Show me architectures ranked by [attr1], then by [attr2]"
   - ❌ Bad: "Which is best?" (ambiguous)

3. **Mention your team context for better recommendations:**
   - "We have 1 person, 2 weeks" → system prioritizes fast + simple
   - "We have ML experts, 1 month" → system considers complex approaches
   - "We need <$1000 in API costs" → system ranks by cost

4. **If you change your mind mid-session:**
   - Just say: "Actually, let me optimize for [NEW ATTRIBUTE] instead"
   - System will re-rank and explain the shift

5. **Ask for hybrid approaches:**
   - "Can I combine #2 and #1 for both speed and hit rate?"
   - System will explain how to implement multi-architecture approach

---

