# Multi-Turn Shopping Agent: Architecture Recommendations

## Competition Context
- **Hidden Target**: Find product by asking clarifying questions (max 10 turns)
- **Scoring**: 50% Hit Rate@10 + 30% MRR + 20% Efficiency (based on MTTC)
- **Baseline Performance**: 12.5% hit rate, 0.068 MRR, 9.81 MTTC, 0.107 Technical Score
- **Scenarios**: 40% Buying, 40% Browsing, 15% Intent Override, 5% Boundary

## Architecture Scoring Framework

**Ranking Criteria (1 = highest priority):**
1. Hit Rate@10 potential (raw recovery capability)
2. MRR potential (rank quality of recovered product)
3. MTTC efficiency (turns to conversion)
4. Intent override handling
5. Boundary scenario robustness
6. Implementation complexity vs. benefit
7. Token/latency cost

---

## TOP 10 RANKED ARCHITECTURES

### 🥇 **Architecture #1: Multi-Strategy Hybrid Retrieval with LLM Query Rewriting**
**Ranking: 1 (Best)**

**Components:**
- **Query Rewriter** (LLM-based): Interprets user intent → structured queries + implicit features
- **Dual Retrieval**: 
  - Dense (embedding-based) for semantic understanding
  - Sparse (BM25) for keyword matching
  - Hybrid fusion with learnable weights
- **Adaptive Attribute Sequencing**: LLM determines next best question based on:
  - Product cluster entropy in current results
  - User profile signals
  - Conversation history
- **Intent Override Detector**: Track constraint changes and reset retrieval strategy
- **Semantic Reranker**: Cross-encoder to reorder results by user intent alignment

**Why #1:**
- Combines keyword + semantic understanding
- LLM query rewriting captures implicit intent (e.g., "dressy" → "occasion:formal, material:silk")
- Adaptive questioning minimizes turns for Browsing scenarios
- Natural intent override handling via constraint tracking
- Can leverage user profile for personalization

**Expected Gains:** Hit Rate +45-60%, MRR +40-50%, MTTC -3 to -4 turns
**Token Cost:** ~200-300 tokens/turn (manageable)
**Implementation Difficulty:** Medium-High

---

### 🥈 **Architecture #2: Constraint-Driven Filtering with Ranked Question Bank**
**Ranking: 2**

**Components:**
- **Hard Constraint Parser**: Extract explicit constraints from each message (budget, material, size, etc.)
- **Soft Preference Accumulator**: Track hints and preferences
- **Constraint-Based Filtering**: 
  - Build catalog filters iteratively based on accumulated constraints
  - Score products by how well they satisfy constraints
- **Intelligent Question Generator**: 
  - Calculate information gain per attribute (entropy reduction)
  - Ask about highest-entropy attributes first
  - Pre-built question templates by attribute type
- **Profile-Aware Filtering**: Bias results toward products aligned with user's historical preferences
- **Override Context Manager**: On override, remove old constraint, apply new one

**Why #2:**
- More deterministic than #1 (no dependency on LLM quality)
- Excellent for Buying scenario (hard constraints disclosed early)
- Simple, auditable pipeline
- Lightweight token cost (~50-100/turn)
- Strong intent override handling via constraint state machine

**Expected Gains:** Hit Rate +35-50%, MRR +30-40%, MTTC -2 to -3 turns
**Token Cost:** ~50-100 tokens/turn
**Implementation Difficulty:** Medium

---

### 🥉 **Architecture #3: Multi-Route Classification + Route-Specific Retrieval**
**Ranking: 3**

**Components:**
- **Scenario Classifier** (lightweight LLM or rule-based):
  - Classify incoming message as: Buying, Browsing, or Intent Override
  - Confidence threshold routing
- **Route 1 (Buying - 40%)**:
  - Extract hard constraint from first message
  - Direct BM25 search on constraint field
  - Follow-up with semantic similarity to top candidates
  - Ask confirming questions
  
- **Route 2 (Browsing - 40%)**:
  - Aggressive attribute questioning strategy
  - Information-gain based question ordering
  - Expand search radius gradually as constraints accumulate
  - Use clustering to identify product families
  
- **Route 3 (Intent Override - 15%)**:
  - Maintain two constraint sets: {old_constraints} and {new_constraints}
  - On turn 3-4, detect override trigger phrase
  - Pivot: apply new constraints, deprioritize old ones
  
- **Route 4 (Boundary - 5%)**:
  - Handle "I don't have a preference" gracefully
  - Fall back to user profile-based recommendations

**Why #3:**
- Each scenario has different optimal strategy
- Buying: constraint-based filtering (fast)
- Browsing: question-driven exploration (systematic)
- Intent Override: constraint management (robust)
- Boundary: personalization fallback (handles edge case)

**Expected Gains:** Hit Rate +40-55%, MRR +35-45%, MTTC -2 to -4 turns
**Token Cost:** ~100-200 tokens/turn
**Implementation Difficulty:** Medium

---

### **Architecture #4: Dense Vector Retrieval with User Profile Personalization**
**Ranking: 4**

**Components:**
- **Embedding-Based Catalog Index**: 
  - Embed all 50K products using product title + key features
  - Use off-the-shelf embeddings (e.g., BGE-base or CLIP for clothing)
  - Build FAISS or ANN index for fast retrieval
  
- **User Profile Encoding**:
  - Convert anonymized user profile into embedding space
  - Blend purchase frequency + rating preferences into product affinity
  
- **Conversation-Aware Query Embedding**:
  - Embed user message + conversation history as combined context
  - Dynamically reweight embedding space toward profile-aligned products
  - Multi-turn context accumulation
  
- **Attribute-Specific Sub-Indices**:
  - Separate embeddings for: {color, material, size, brand, style, use_case}
  - Allow filtering before top-k retrieval
  
- **Semantic Query Expansion**:
  - Generate related terms (e.g., "waterproof" → "weather-resistant", "durable")
  - Expand user queries before embedding lookup

**Why #4:**
- Pure semantic understanding without LLM (faster, cheaper)
- Natural multi-turn context accumulation
- User profile integration improves Browsing & Boundary scenarios
- Excellent for customers with vague descriptions ("something comfy")
- Requires no live API calls if self-hosted embeddings

**Expected Gains:** Hit Rate +30-45%, MRR +25-35%, MTTC -2 to -3 turns
**Token Cost:** Minimal (embedding model cost only, ~0 LLM tokens)
**Implementation Difficulty:** Medium (requires vector DB setup)

---

### **Architecture #5: Knowledge Graph + Structured Attribute Extraction**
**Ranking: 5**

**Components:**
- **Catalog Knowledge Graph**:
  - Build KG: Products → (has_material) → Materials, (in_category) → Categories, etc.
  - Materialized relationship tables: {product → attribute → value}
  - Enables constraint satisfaction checking in O(1)
  
- **Structured Extraction Module**:
  - Parse user message → {constraint_type: value, confidence}
  - Use regex + lightweight NER for material, color, size, budget
  - Structured output: [("material", "cotton", 0.95), ("budget", "$50-100", 0.8)]
  
- **Attribute Question Sequencing**:
  - Track which attributes have been mentioned
  - Identify high-cardinality attributes with best discriminative power
  - Ask about unasked attributes likely to narrow results most
  
- **Graph Traversal Search**:
  - Start from matched constraints
  - Traverse edges to find products satisfying multiple constraints
  - Return products ranked by constraint satisfaction score
  
- **Profile-Aware Ranking**:
  - Rerank results by user's historical affinity for brands, price ranges, styles

**Why #5:**
- Highly deterministic (rules-based constraint matching)
- Fast (knowledge graph lookup is ~O(1) after preprocessing)
- Excellent traceability (can explain why product was recommended)
- Scales well to 50K products (preprocessed relations)
- Handles intent override by swapping constraint sets

**Expected Gains:** Hit Rate +25-40%, MRR +20-30%, MTTC -1.5 to -2.5 turns
**Token Cost:** Minimal
**Implementation Difficulty:** High (KG construction requires data engineering)

---

### **Architecture #6: Two-Stage Ranking with Coarse→Fine Filtering**
**Ranking: 6**

**Components:**
- **Stage 1 (Coarse Filtering - Turns 1-3)**:
  - Broad BM25 search on all products
  - Filter to top 200-500 candidates per query
  - Ask about highest-level attributes (category, use_case, budget)
  
- **Stage 2 (Fine Ranking - Turns 4-10)**:
  - Narrow candidate set further with specific constraints (material, color, size, style)
  - Apply cross-encoder reranking on narrowed set
  - Ask targeted follow-ups about distinguishing features
  
- **Adaptive Depth**:
  - Buying scenario: Jump directly to Stage 2 (hard constraint given)
  - Browsing: Spend 3-4 turns in Stage 1, then refine
  - Intent Override: Reset filters on turn 3-4, restart from narrowed Stage 1 set
  
- **Question Prioritization**:
  - Stage 1: Prioritize high-cardinality filters (use_case, category)
  - Stage 2: Prioritize low-cardinality distinguishers (specific color, exact size)

**Why #6:**
- Matches human shopping behavior (browse broadly, then narrow)
- Reduces MTTC by early filtering (fewer candidates to rank by turn 5+)
- Separate strategies for early & late turns
- Works well when embedding space not available

**Expected Gains:** Hit Rate +30-45%, MRR +25-35%, MTTC -2 to -3 turns
**Token Cost:** ~50-150 tokens/turn
**Implementation Difficulty:** Medium

---

### **Architecture #7: Multi-Model Ensemble with Weighted Voting**
**Ranking: 7**

**Components:**
- **Model 1: BM25 Retriever** (75th percentile weight)
  - Baseline keyword matching
  - Fast, reliable, no API dependency
  
- **Model 2: LLM Semantic Retrieval** (60th percentile weight)
  - Query rewriting + dense search
  - Slower but captures paraphrasing
  
- **Model 3: User Profile Similarity** (50th percentile weight)
  - Recommend products similar to user's past purchases
  - Effective for Browsing & Boundary scenarios
  
- **Model 4: Constraint Solver** (80th percentile weight)
  - Rule-based constraint matching
  - Deterministic, high precision for explicit constraints
  
- **Ensemble Strategy**:
  - Normalize scores from each model to [0, 1]
  - Weighted combination: 0.35×BM25 + 0.25×LLM + 0.20×Profile + 0.35×Constraint
  - Rerank top-100 by ensemble score
  - Return top-10
  
- **Adaptive Weighting by Scenario**:
  - Buying: increase Constraint weight (0.50) → more rule-based
  - Browsing: increase Profile weight (0.35) → more personalization
  - Intent Override: reset Constraint model, apply new weights

**Why #7:**
- Combines strengths of multiple approaches
- Robustness: multiple retrieval sources reduce single-point failures
- Each model handles different aspects of the problem well
- Can fall back if any model fails
- High implementation complexity but predictable performance

**Expected Gains:** Hit Rate +35-50%, MRR +30-40%, MTTC -2 to -3 turns
**Token Cost:** ~150-300 tokens/turn
**Implementation Difficulty:** High (requires tuning 4 models + ensemble weights)

---

### **Architecture #8: Reinforcement Learning Policy with Offline Training**
**Ranking: 8**

**Components:**
- **State Representation**:
  - Conversation history (last N messages)
  - Current top-10 candidates
  - User profile vector
  - Attributes asked so far
  
- **RL Agent**:
  - Offline training on public dataset (200 sessions)
  - Learn policy: state → {best_next_question, ask_attribute}
  - Reward: positive for hits, scaled by (11 - turn)
  - Use policy gradient or Q-learning
  
- **Exploration Strategy**:
  - Epsilon-greedy: 90% follow learned policy, 10% explore
  - Helps discover better question orderings on private test set
  
- **Fallback Heuristics**:
  - If confidence < threshold, fall back to rule-based strategy
  - Protects against RL overfitting to public set
  
- **Intent Override Handling**:
  - RL learns to detect and adapt to preference changes
  - Retrain state embedding on override signal

**Why #8:**
- Learns optimal question-asking strategy from data
- Adapts to different scenario types automatically
- Potentially better long-term performance than hand-crafted rules
- Handles user preference variations well
- Challenge: Limited training data (200 sessions), risk of overfitting

**Expected Gains:** Hit Rate +25-45%, MRR +20-35%, MTTC -1.5 to -3 turns (if well-tuned)
**Token Cost:** ~50-150 tokens/turn
**Implementation Difficulty:** Very High (requires RL expertise + offline training infrastructure)

---

### **Architecture #9: LLM Few-Shot Chain-of-Thought with Self-Correction**
**Ranking: 9**

**Components:**
- **Few-Shot Examples**:
  - Select 5-10 best exemplar sessions from public set
  - Format as: "Customer: [msg] → Agent Reasoning: [chain-of-thought] → Best Question: [attr] → Top Rec: [asin]"
  
- **LLM Generation Pipeline**:
  - Prompt LLM with: {current_message, conversation_history, user_profile, few_shot_examples}
  - LLM generates: reasoning → best next question → top-5 ASINs
  
- **Self-Correction Loop**:
  - Generate initial response
  - Verify: Do recommended ASINs actually exist? Do they match constraints?
  - If invalid, re-prompt LLM with feedback
  - Max 2 correction iterations
  
- **Retrieval Augmentation**:
  - Use LLM reasoning to refine BM25 query
  - Search with refined query, pass results back to LLM
  - LLM reranks results by reasoning quality
  
- **Intent Override Detection**:
  - LLM explicitly detects "Actually..." or contradiction patterns
  - Signals constraint change to retrieval module

**Why #9:**
- Simple to implement (LLM API only)
- Few-shot learning captures competition-specific patterns
- Chain-of-thought reasoning explains decisions
- Self-correction improves reliability
- Struggle: LLM can "hallucinate" non-existent products (need strict validation)

**Expected Gains:** Hit Rate +20-40%, MRR +15-30%, MTTC -1 to -2.5 turns
**Token Cost:** ~250-400 tokens/turn (high)
**Implementation Difficulty:** Low-Medium (LLM API dependency only)

---

### **Architecture #10: Active Learning Loop with Human-in-the-Loop Tuning**
**Ranking: 10**

**Components:**
- **Baseline System**:
  - Start with Architecture #2 (Constraint-Driven Filtering)
  - Run on public 200-session set
  
- **Performance Analysis**:
  - Identify failure modes: low-rank misses, false negatives, override failures
  - Cluster failures by scenario type & constraint type
  
- **Targeted Improvements**:
  - For each failure cluster, implement specialized retrieval logic
  - Example: "Material-related misses? → Add material-specific BM25 weighting"
  
- **Human Expert Loop** (if team has 2+ people):
  - Person A implements Architecture #2
  - Person B reviews failure cases
  - Person A implements Person B's suggested fixes
  - Iterate 2-3 times
  
- **Hyperparameter Tuning**:
  - Grid search over: question-sequencing strategies, filter thresholds, reranking weights
  - Use 5-fold CV on public set
  
- **Ensemble Final Attempt**:
  - Combine best variants via voting or weighted averaging

**Why #10:**
- No fundamental innovation (ranked lowest)
- High implementation effort for marginal gains
- Requires strong domain understanding & iteration
- Risk of overfitting to public set
- Useful as **post-launch tuning strategy** after implementing a base architecture

**Expected Gains:** Hit Rate +15-30%, MRR +10-20%, MTTC -0.5 to -1.5 turns
**Token Cost:** Varies
**Implementation Difficulty:** Medium (requires experimentation & analysis)

---

## QUICK SELECTION GUIDE

**Choose Architecture by Priority:**

| **Your Priority** | **Best Architecture** | **Rationale** |
|---|---|---|
| Maximize Hit Rate | #1 (Hybrid) or #2 (Constraint) | Both combine multiple retrieval signals |
| Maximize MRR (rank quality) | #4 (Dense) or #1 (Hybrid) | Semantic + reranking captures relevance |
| Minimize MTTC (efficiency) | #2 (Constraint) or #6 (Two-Stage) | Coarse→fine filtering reduces wasted turns |
| Handle Intent Override well | #2 (Constraint) or #3 (Multi-Route) | Explicit constraint state management |
| Minimize token cost | #2, #4, or #5 (all <150 tokens/turn) | Avoid heavy LLM use |
| Fastest implementation | #9 (Few-Shot CoT) | Just prompt-engineer an LLM |
| Most robust/production-ready | #3 (Multi-Route) or #7 (Ensemble) | Multiple fallbacks, explicit scenario handling |

---

## RECOMMENDED IMPLEMENTATION PATH

**Phase 1 (Baseline - Week 1):**
- Implement Architecture #2 (Constraint-Driven)
- Expected: 35-50% hit rate, 0.03-0.04 MRR, 6-7 MTTC

**Phase 2 (Hybrid - Week 2):**
- Add Architecture #1 query rewriting
- Switch from Constraint-only to Constraint + LLM fusion
- Expected: 45-60% hit rate, 0.04-0.05 MRR, 5-6 MTTC

**Phase 3 (Ensemble - Week 3):**
- Combine Arch #1 (LLM rewriting) + #4 (Dense retrieval) + #2 (Constraint)
- Weighted ensemble voting
- Expected: 50-65% hit rate, 0.05-0.06 MRR, 4-5 MTTC

**Phase 4 (Tuning - Week 4):**
- Fine-tune weights on public set (5-fold CV)
- Implement scenario-specific routing
- Expected: 55-70% hit rate, 0.06-0.08 MRR, 3.5-4.5 MTTC

---

## CRITICAL SUCCESS FACTORS

1. **Intent Override Handling**: Must detect & adapt on turn 3-4
2. **Browsing Scenario Excellence**: Most scenarios (40%), hardest to solve
3. **Question Quality**: One question per turn → 10 turns max
4. **Constraint Satisfaction**: Ensure top-10 actually match user's explicit requirements
5. **Profile Personalization**: Anonymized profile contains valuable signals
6. **Early Filtering**: Reduce candidate pool quickly to enable good ranking
7. **Reranking at End**: Cross-encoder or LLM reranking of top-100 → top-10

---

## WHEN TO OVERRIDE TO DIFFERENT ARCHITECTURE

- **If baseline performs <20% hit rate**: Try #1 (Hybrid) or #3 (Multi-Route)
- **If MRR very low (<0.05)**: Problem is ranking → add reranker (try #1 or #7)
- **If MTTC > 8 turns**: Questions are ineffective → switch to #2 or #6 (smarter question selection)
- **If intent override scenarios fail**: Implement #3 (explicit scenario routing)
- **If token costs explode**: Reduce LLM calls → switch to #2, #4, or #5

---

## ATTRIBUTE INTERACTION INSIGHTS

**Attribute Frequency (useful for question ordering):**
1. **Category/Use Case** (broadest) → ask first, narrows 50%+ of candidates
2. **Budget** (strongly correlates with product tier) → ask early for Buying scenarios
3. **Style** (high variance within category) → ask mid-session
4. **Material** (mid-variance, strong customer preference) → ask mid-session
5. **Color** (high variance, low discriminative power) → ask late
6. **Size** (matches customer fit, narrow discriminative power) → ask last

**Recommended Question Order (Browsing scenario):**
Turn 1: Budget range? → Turn 2: Use case? → Turn 3: Material? → Turn 4: Style? → Turn 5+: Size/Color

---

## USER INTERACTION PATTERNS

Expect user to change priorities mid-session:
- **Turn 1 Focus**: "I'm looking for X" (broad intent)
- **Turn 2-3 Refinement**: "Actually, I prefer Y" (soft preference)
- **Turn 3-4 Override**: "Wait, I really need Z" (hard constraint override)
- **Turn 5+ Confirmation**: "Anything else like this?" (seeking similar products)

**Agent should:**
1. Accumulate soft preferences (turns 1-3)
2. Handle constraint swaps (turn 3-4)
3. Shift from questioning to confirmation (turn 5+)
4. Ensure top-10 are similar quality (ranking matters)

---

