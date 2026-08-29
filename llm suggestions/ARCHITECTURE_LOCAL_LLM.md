# Architecture Recommendations: Local LLM Edition
## Local Ollama + Limited Resources (Laptop, <8GB RAM)

**Constraints:**
- ✅ Locally hosted LLM (Ollama with lightweight models)
- ✅ Sentence-Transformers for embeddings (CPU-friendly)
- ✅ SQLite FTS5 (already in baseline)
- ✅ Python standard library
- ❌ External APIs (OpenAI, etc.)
- ⚠️ Limited RAM (~8GB), slow on CPU

---

## Recommended LLM Setup

**Best for your constraints: Mistral 7B or Phi 2.5B**

```bash
# Install Ollama from https://ollama.ai
ollama pull mistral        # 4GB, good quality, ~500-800ms per inference
# OR for faster (but lower quality):
ollama pull phi            # 2.7GB, faster (~200-300ms), good for constraints
```

**In your Python code:**
```python
import requests
import json

def call_local_llm(prompt: str, model: str = "mistral") -> str:
    """Call locally-hosted Ollama LLM"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=30
    )
    return json.loads(response.text)["response"]
```

---

## TOP 7 VIABLE ARCHITECTURES (Local LLM + Limited Resources)

### 🥇 **Architecture #1: Constraint-Driven Filtering with Light LLM Enhancement**
**Ranking: 1 (BEST)**

**Components:**
- **Regex-Based Constraint Extraction** (primary - no LLM needed)
  - Material, color, budget, size patterns
  - Fast, deterministic, no latency
  
- **LLM Query Rewriting** (light usage, only when needed)
  - Use LLM ONLY if regex extracted nothing
  - Prompt: "Extract shopping attributes from: [message]"
  - Lightweight prompt (50-100 tokens), quick response
  - Cost: 1-2 LLM calls per turn max
  
- **BM25 Filtering** + constraint matching
  
- **Profile-Aware Fallback**
  
- **Intent Override State Machine**

**Why #1 for Local LLM:**
- ✅ Regex handles 80-90% of cases (no LLM needed)
- ✅ LLM only as fallback for vague messages
- ✅ Lightweight LLM usage → fast on CPU
- ✅ Low memory footprint
- ✅ Excellent for Buying (40%) + Override handling
- ✅ Best technical score for resource constraints

**Expected Gains:** Hit Rate 40-55%, MRR 0.035-0.048, MTTC 5-6 turns
**Technical Score:** 0.40-0.55 (3.7-5.1x better than baseline)
**LLM Calls:** ~1-2 per turn (lightweight)
**Latency:** <500ms per turn (regex primary, LLM fallback)
**Implementation:** 2 weeks
**Memory:** ~500MB (Ollama running separately)

**Code Skeleton:**
```python
class Agent:
    def __init__(self, catalog_path, ollama_model="mistral"):
        self.catalog_path = catalog_path
        self.ollama_model = ollama_model
        self.connection = sqlite3.connect(":memory:")
        self._build_index()
    
    def respond(self, session_id, user_message, turn, top_k):
        # Step 1: Try regex extraction (fast, no LLM)
        constraints = self._extract_constraints_regex(user_message)
        
        # Step 2: If nothing extracted, use LLM fallback
        if not constraints:
            constraints = self._extract_constraints_llm(user_message)
        
        # Step 3: BM25 + constraint filter
        results = self._filter_by_constraints(constraints, top_k)
        
        # Step 4: Generate question
        question = self._generate_question(session_id)
        
        return {
            "message": question,
            "ask_attribute": best_attr,
            "recommendations": results
        }
    
    def _extract_constraints_regex(self, message):
        # Regex patterns for material, color, budget, size
        # Returns dict if found, else {}
        pass
    
    def _extract_constraints_llm(self, message):
        # Lightweight LLM call only if regex failed
        prompt = f"Extract shopping constraints from: {message}"
        response = requests.post("http://localhost:11434/api/generate", ...)
        return parse_llm_response(response)
```

---

### 🥈 **Architecture #2: Two-Stage Ranking with LLM Clarification**
**Ranking: 2**

**Components:**
- **Stage 1 (Turns 1-3): Broad BM25 filtering**
  - No LLM needed yet
  - Just keyword matching → top 500 candidates
  
- **Stage 2 (Turns 4-10): LLM Clarification + Reranking**
  - Use LLM to understand nuanced preferences
  - Prompt: "Given the products [list], which best matches user's request: [message]?"
  - Rerank top-100 using LLM scoring
  - Still lightweight (shorter prompt than #9)

- **Profile-Based Fallback**

- **Question Generation** (info gain ordering)

**Why #2:**
- ✅ Minimal LLM usage (only stage 2)
- ✅ Works well for Browsing scenarios (vague initial → refined later)
- ✅ Natural progression: broad then specific
- ✅ Gives early results without waiting for LLM

**Expected Gains:** Hit Rate 35-50%, MRR 0.03-0.04, MTTC 6-7
**LLM Calls:** ~3-4 per session (turns 5-10 only)
**Latency:** Stage 1 <100ms, Stage 2 ~500-1000ms per turn
**Implementation:** 2 weeks
**Memory:** ~500MB

---

### 🥉 **Architecture #3: Multi-Route Scenario Classification with LLM**
**Ranking: 3**

**Components:**
- **Lightweight Scenario Classifier** (LLM-based, turn 1 only)
  - Prompt: "Is this Buying (explicit constraint), Browsing (vague), or Override? Message: [message]"
  - ~50-100 tokens, fast response
  - Route to best strategy
  
- **Route 1 (Buying → Constraint-Driven):**
  - Regex extraction + BM25 (no more LLM for this turn)
  
- **Route 2 (Browsing → Two-Stage):**
  - Question-driven exploration
  
- **Route 3 (Override → State Machine):**
  - Track old vs new constraints
  
- **Route 4 (Boundary → Profile-Based):**
  - User said "no preference" → recommend similar to past purchases

**Why #3:**
- ✅ Smart routing: each scenario gets optimized strategy
- ✅ Single LLM call (turn 1 classification only)
- ✅ Then falls back to fast regex/BM25 for remaining turns
- ✅ Excellent override handling
- ✅ Very efficient on limited resources

**Expected Gains:** Hit Rate 42-55%, MRR 0.035-0.045, MTTC 5-6
**LLM Calls:** 1 per session (turn 1 only!)
**Latency:** ~500ms turn 1, <100ms turns 2-10
**Implementation:** 2-3 weeks
**Memory:** ~500MB

---

### **Architecture #4: Hybrid Retrieval with Self-Hosted Embeddings**
**Ranking: 4**

**Components:**
- **Sentence-Transformers Embeddings** (local, CPU-friendly)
  - Model: "all-MiniLM-L6-v2" (22MB, fast on CPU)
  - Pre-embed products at startup (~30 seconds for 50K products)
  - No external API needed
  
- **Dual Retrieval:**
  - Dense: FAISS index for semantic similarity
  - Sparse: BM25 for keyword matching
  - Hybrid fusion: 0.3×dense + 0.7×sparse (adjust per scenario)
  
- **LLM Query Rewriting** (optional, lightweight)
  - Only for very vague queries
  - Prompt: "Paraphrase this shopping query with more detail: [message]"
  
- **Reranking:** Cross-scorer (could be LLM or rule-based)

**Why #4:**
- ✅ No external embedding API (self-hosted)
- ✅ All-MiniLM-L6-v2 extremely fast on CPU
- ✅ Semantic + keyword coverage
- ✅ Good for Browsing scenarios
- ⚠️ Pre-embedding takes ~30 seconds at startup
- ⚠️ FAISS library adds ~50MB

**Expected Gains:** Hit Rate 38-50%, MRR 0.03-0.045, MTTC 6-7
**Embedding Model:** all-MiniLM-L6-v2 (22MB)
**LLM Calls:** 0-1 per turn (optional)
**Latency:** ~200-300ms per turn
**Implementation:** 2-3 weeks
**Memory:** ~200MB (embeddings) + ~100MB (FAISS index)

**Setup:**
```bash
pip install sentence-transformers faiss-cpu
```

---

### **Architecture #5: Ensemble with Weighted Voting**
**Ranking: 5**

**Components:**
- **System A: BM25** (baseline, 30% weight)
  - Fast, reliable, no LLM
  
- **System B: Constraint-Driven** (50% weight)
  - Regex + light LLM fallback
  
- **System C: LLM Reranking** (20% weight)
  - Takes top-50 from A+B, reranks via LLM
  - Lightweight prompt: "Rank these products by relevance to [query]"
  
- **Scenario-Adaptive Weights:**
  - Buying: increase B to 0.70
  - Browsing: increase A to 0.40
  - Override: keep balanced

**Why #5:**
- ✅ Combines strengths of multiple approaches
- ✅ Robustness via fallbacks
- ✅ LLM used efficiently (reranking only, not generation)
- ✅ Handles all scenario types

**Expected Gains:** Hit Rate 40-52%, MRR 0.035-0.047, MTTC 5-6
**LLM Calls:** 1 per turn (reranking)
**Latency:** ~400-600ms per turn
**Implementation:** 3 weeks
**Memory:** ~500MB

---

### **Architecture #6: Knowledge Graph + LLM Extraction**
**Ranking: 6**

**Components:**
- **LLM for Attribute Extraction** (main usage)
  - Prompt: "Extract material, color, size, budget, use_case from: [message]"
  - Structured output parsing
  - More flexible than regex (handles synonyms)
  
- **Materialized KG** (pre-computed)
  - Product → material → cotton, etc.
  - Enable fast constraint lookup
  
- **Graph Traversal Search**
  - Join on materialized relationships
  - Find products matching extracted attributes
  
- **Profile-Aware Reranking**

**Why #6:**
- ✅ LLM handles fuzzy attribute matching (e.g., "organic" → "material:natural")
- ✅ KG provides fast lookup
- ✅ More flexible than pure regex
- ⚠️ Requires LLM per turn (slower)
- ⚠️ Data engineering overhead

**Expected Gains:** Hit Rate 35-48%, MRR 0.030-0.040, MTTC 6-7
**LLM Calls:** 1 per turn
**Latency:** ~500-800ms per turn
**Implementation:** 3-4 weeks
**Memory:** ~200-300MB (materialized KG)

---

### **Architecture #7: Lightweight Few-Shot CoT**
**Ranking: 7 (Risky on Limited Resources)**

**Components:**
- **Few-Shot Examples** (3-5 good sessions from public set)
  - Format: "Customer: [message] → Agent: [reasoning] → Best question: [attr]"
  
- **LLM Generation** (full chain-of-thought)
  - Prompt template: "Given examples: [few_shots]\n\nCustomer: [message]\n\nAgent reasoning:"
  - ~300-500 tokens per turn
  
- **Self-Correction** (if output invalid)
  - Re-prompt if recommended products don't exist
  - Up to 2 correction loops
  
- **Retrieval Augmentation**
  - LLM reasoning → refined query
  - Search with refined query

**Why #7:**
- ✅ Simple prompt engineering
- ⚠️ Heavy LLM usage (full generation every turn)
- ⚠️ Slow on CPU (1-2 seconds per turn)
- ⚠️ Risk of hallucination (invalid product IDs)
- ⚠️ High token cost per session

**Expected Gains:** Hit Rate 25-40%, MRR 0.02-0.03, MTTC 7-8
**LLM Calls:** 1 per turn (heavy, 300-500 tokens)
**Latency:** 1-3 seconds per turn (SLOW)
**Implementation:** 1-2 weeks (easiest)
**Memory:** ~500MB
**⚠️ Not recommended for limited resources**

---

## RECOMMENDED IMPLEMENTATION PATH (Local LLM)

### **Phase 1 (Week 1): Constraint-Driven as Baseline**
```
✅ Regex patterns for material, color, budget, size
✅ BM25 filtering
✅ Session state management
✅ Question generation (info gain)
✅ Basic override detection
```
**Result:** 35-40% hit rate, 0.03 MRR, 7 MTTC
**No LLM yet!**

### **Phase 2 (Week 2): Add Light LLM Fallback**
```
✅ Install Ollama + Mistral 7B model
✅ Add LLM fallback for constraint extraction (only if regex fails)
✅ Implement override detection via LLM (turn 3-4 only)
✅ Lightweight prompts (<100 tokens)
```
**Result:** 40-48% hit rate, 0.035-0.04 MRR, 5-6 MTTC
**LLM usage: 1-2 calls per turn**

### **Phase 3 (Week 3): Add Scenario Routing (Optional)**
```
✅ Turn 1: LLM classifies scenario (1 call only)
✅ Route to optimized strategy per scenario
✅ No LLM for turns 2-10 (unless needed)
```
**Result:** 42-52% hit rate, 0.04-0.048 MRR, 5-6 MTTC
**LLM usage: 1 call per session (turn 1 only)**

### **Phase 4 (Week 4): Ensemble + Polish**
```
✅ Combine BM25 + Constraint + Light LLM reranking
✅ Scenario-adaptive weighting
✅ Fallback strategies
✅ Final tuning
```
**Result:** 45-60% hit rate, 0.045-0.065 MRR, 4-5 MTTC
**LLM usage: 1 call per turn (efficient)**

---

## LOCAL LLM STRATEGY

### Model Selection (Ollama)

**Mistral 7B** (Recommended)
```
Size: 4GB
Speed: 500-800ms per inference
Quality: Excellent
RAM: 6-8GB total with Ollama
Command: ollama pull mistral
```

**Phi 2.5B** (If very slow)
```
Size: 1.6GB
Speed: 200-300ms per inference
Quality: Good (but worse than Mistral)
RAM: 4-6GB total
Command: ollama pull phi
```

### Prompt Optimization (CPU Speed)

**For Constraint Extraction:**
```
FAST: "Extract attributes from: [message]" (50 tokens, ~200ms)
SLOW: "You are a shopping assistant... extract..." (200 tokens, ~800ms)
```

**For Scenario Classification:**
```
FAST: "Buying/Browsing/Override? [message]" (40 tokens, ~150ms)
SLOW: "Classify scenario with explanation..." (150 tokens, ~500ms)
```

**Key Rule:** Keep prompts <100 tokens per turn

---

## DECISION TREE (Local LLM + Limited Resources)

```
START
│
├─ How much time do you have?
│  ├─ 1 week → #1 (Constraint-Driven) + LLM fallback
│  ├─ 2 weeks → #1 (Phase 1-2) ← RECOMMENDED
│  ├─ 3 weeks → #3 (Multi-Route classification)
│  └─ 4 weeks → #5 (Ensemble)
│
├─ What scenarios matter most?
│  ├─ Buying (40%) → #1 (Constraint dominates)
│  ├─ Browsing (40%) → #2 (Two-Stage) or #4 (Embeddings)
│  ├─ Override (15%) → #1 or #3 (explicit handling)
│  └─ All equal → #5 (Ensemble) or #3 (Routing)
│
├─ Do you want fastest response?
│  ├─ YES → #1 (Phase 2) - <500ms/turn
│  ├─ NO (quality OK) → #2 (Two-Stage) - ~1s/turn
│  └─ Quality critical → #5 (Ensemble) - ~600ms/turn
│
└─ Best choice for you → #1 (Constraint-Driven with Light LLM)
   Why: Fast, low resource, high hit rate, easy to implement
   Timeline: 2 weeks (Phase 1-2)
   Expected: 40-48% hit rate (3.7-4.5x better than baseline)

ALTERNATIVE:
→ If Browsing scenarios critical: Add #2 (Two-Stage) as Phase 2 fallback
→ If want experimentation: Try #3 (Routing) week 3 + #4 (Embeddings) week 4
```

---

## QUICK SETUP GUIDE

### 1. Install Ollama
```bash
# macOS: https://ollama.ai
# Linux: curl https://ollama.ai/install.sh | sh
# Windows: https://ollama.ai/download/windows

# Pull Mistral
ollama pull mistral

# Start Ollama server (runs in background)
ollama serve
```

### 2. Install Python Dependencies
```bash
pip install requests sqlite3 numpy
# For optional Embeddings (Phase 4+):
pip install sentence-transformers faiss-cpu
```

### 3. Update Agent Code
```python
import requests

class Agent:
    def __init__(self, catalog_path: str = "data/catalog.jsonl"):
        self.catalog_path = catalog_path
        self.ollama_model = "mistral"  # Local LLM
        # ... rest of init
    
    def _extract_constraints_llm(self, message: str) -> dict:
        """Fallback LLM extraction (only if regex found nothing)"""
        prompt = f"Extract shopping attributes (material, color, size, budget, style) from: {message}"
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                timeout=5
            )
            return json.loads(response.text)["response"]
        except:
            return {}  # Fall back to profile-based if LLM fails
```

### 4. Test Locally
```bash
python3 -m evaluator.local_evaluator
# Should see results, including LLM latency stats
```

---

## Performance Expectations

| Architecture | Hit Rate | MTTC | LLM Calls/Turn | Latency | Setup |
|---|---|---|---|---|---|
| **#1 Constraint+LLM** | 40-50% | 5-6 | 0-2 | <500ms | 2w |
| #2 Two-Stage+LLM | 35-50% | 6-7 | 1 | ~800ms | 2w |
| #3 Routing+LLM | 42-55% | 5-6 | 0.14 | <500ms | 2-3w |
| #4 Embeddings+LLM | 38-50% | 6-7 | 0-1 | ~300ms | 2-3w |
| #5 Ensemble+LLM | 40-52% | 5-6 | 1 | ~600ms | 3w |
| #6 KG+LLM | 35-48% | 6-7 | 1 | ~700ms | 3-4w |
| #7 Few-Shot CoT | 25-40% | 7-8 | 1 | 1-3s | 1-2w |

---

## FAQ: Local LLM Edition

**Q: Will Ollama + Mistral fit in 8GB RAM?**
A: Yes! Ollama runs separately (uses ~4GB), your Python process uses <1GB. Total ~5GB. Safe.

**Q: How fast are LLM calls on CPU?**
A: Mistral 7B: 500-800ms per call (acceptable). Phi 2.5B: 200-300ms (fast).

**Q: Can I use GPU to speed up?**
A: Yes! If NVIDIA GPU available, Ollama uses it automatically. 10-50x faster.

**Q: Should I keep Ollama running in background?**
A: Yes! Ollama stays running. Your Python code makes HTTP requests to localhost:11434.

**Q: What if Ollama not installed?**
A: Add fallback: if LLM call fails (timeout), use regex-only mode.

**Q: Can I use different models?**
A: Yes! Try Mistral → Phi (faster) or Neural Chat (fine-tuned). Just `ollama pull [model]`.

**Q: How many tokens per session?**
A: Architecture #1: ~100-500 tokens/session. #7 Few-Shot: ~3000-5000 tokens/session. Free locally!

**Q: Will this beat the baseline?**
A: Yes! Expected: 40-55% hit rate vs 12.5% baseline = 3.2-4.4x better.

---

## Risk Assessment

**Low Risk (#1, #2):**
- ✅ Mostly regex-based
- ✅ LLM as fallback only
- ✅ Predictable performance

**Medium Risk (#3, #4, #5):**
- ⚠️ Moderate LLM usage
- ⚠️ Some dependency on model quality
- ⚠️ Possible latency spikes

**High Risk (#6, #7):**
- ❌ Heavy LLM usage
- ❌ Slow on CPU (1-3s per turn)
- ❌ Hallucination risk

---

## My Recommendation

**Start with #1 (Constraint-Driven + Light LLM):**
1. Week 1: Implement pure regex version (no LLM)
   - Expected: 35-40% hit rate
   
2. Week 2: Add Ollama + Mistral as fallback
   - Use only when regex extraction fails
   - Expected: 40-48% hit rate
   - Fast (<500ms/turn), low resource

3. Week 3+: If time permits, explore #3 (Routing) or #5 (Ensemble)

This gives you:
- ✅ Competitive hit rate (40-48%)
- ✅ Fast latency (<500ms/turn)
- ✅ Low memory footprint (8GB)
- ✅ Easy to debug (mostly rules + light LLM)
- ✅ Clear path to improve

---

