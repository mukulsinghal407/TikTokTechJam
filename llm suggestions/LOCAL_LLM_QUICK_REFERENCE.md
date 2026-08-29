# Local LLM Architecture Quick Reference
## Ollama + Mistral 7B + Limited Resources (8GB)

---

## THE 7 VIABLE ARCHITECTURES (Local LLM + 8GB)

| Rank | Architecture | Hit Rate | MTTC | LLM/Turn | Latency | Setup | Best For |
|------|---|---|---|---|---|---|---|
| **1** 🟢 | Constraint + Light LLM | 40-50% | 5-6 | 0-2 | <500ms | 2w | **RECOMMENDED** |
| **2** 🔵 | Two-Stage + LLM | 35-50% | 6-7 | 1 | ~800ms | 2w | Browsing fallback |
| **3** 🟠 | Multi-Route Classification | 42-55% | 5-6 | 0.14 | <500ms | 2-3w | Smart routing |
| **4** 🟡 | Embeddings + LLM | 38-50% | 6-7 | 0-1 | ~300ms | 2-3w | Semantic search |
| **5** 🟣 | Ensemble Voting | 40-52% | 5-6 | 1 | ~600ms | 3w | Robustness |
| **6** 🔴 | Knowledge Graph + LLM | 35-48% | 6-7 | 1 | ~700ms | 3-4w | Transparency |
| **7** ⚫ | Few-Shot CoT | 25-40% | 7-8 | 1 | 1-3s | 1-2w | AVOID (too slow) |

---

## PERFORMANCE COMPARISON

### Technical Score (0.50×HR + 0.30×MRR + 0.20×Eff)
```
#1 Constraint+LLM:    0.40-0.55 ⭐⭐⭐⭐⭐ (BEST)
#3 Multi-Route:       0.42-0.55 ⭐⭐⭐⭐⭐
#5 Ensemble:          0.40-0.52 ⭐⭐⭐⭐
#2 Two-Stage:         0.35-0.50 ⭐⭐⭐⭐
#4 Embeddings:        0.38-0.50 ⭐⭐⭐⭐
#6 Knowledge Graph:   0.35-0.48 ⭐⭐⭐
#7 Few-Shot:          0.20-0.40 ⭐⭐ (AVOID)
```

### Scenario Performance
```
                Buying  Browsing  Override  Boundary  Weighted
#1 Constraint   70%     25%       40%       35%       50%
#3 Multi-Route  70%     35%       50%       40%       53%
#5 Ensemble     55%     35%       35%       35%       45%
#2 Two-Stage    50%     40%       30%       35%       42%
#4 Embeddings   30%     50%       20%       45%       37%
#6 KG           50%     15%       25%       20%       35%
#7 Few-Shot     35%     30%       25%       20%       30%
```

### Latency (Important for 8GB Laptop)
```
#4 Embeddings:        ~300ms  (fast - embedding lookup)
#1 Constraint+LLM:    <500ms  (mostly regex)
#3 Multi-Route:       <500ms  (1 LLM call turn 1 only)
#5 Ensemble:          ~600ms  (3 systems)
#6 Knowledge Graph:   ~700ms  (LLM + KG lookup)
#2 Two-Stage:         ~800ms  (stage 2 LLM reranking)
#7 Few-Shot:          1-3s    (SLOW - full LLM generation)
```

### LLM Calls Per Turn
```
#3 Multi-Route:       0.14 (1 call per session turn 1, then none)
#4 Embeddings:        0-1 (optional reranking)
#1 Constraint+LLM:    0-2 (only if regex fails)
#2 Two-Stage:         1 (turn 5+ only)
#5 Ensemble:          1 (reranking)
#6 Knowledge Graph:   1 (per turn)
#7 Few-Shot:          1 (per turn, full generation)
```

---

## WHICH ONE SHOULD YOU PICK?

### **Quick Decision: 30 seconds**

**Q1: How much time?**
- <1 week → #1 (Phase 1 only, no LLM)
- 1-2 weeks → #1 (Phase 1-2) ← BEST FIT
- 2-3 weeks → #3 (Multi-Route) 
- 3+ weeks → #5 (Ensemble)

**Answer: Pick #1 (Constraint + Light LLM)**

---

## PHASE-BY-PHASE ROADMAP

### PHASE 1: Week 1 (Baseline - No LLM)
**Goal:** 35-40% hit rate foundation

```python
# Main changes to starter/agent.py:
1. Regex patterns for constraint extraction
   - Material: ("cotton", "polyester", "nylon", ...)
   - Color: ("black", "white", "blue", ...)
   - Budget: r'\$(\d+)-?(\d*)' 
   - Size: ("S", "M", "L", "XL", "32", "34", ...)
   - Style/Use Case: common patterns

2. Constraint-based BM25 filtering
   - Extract constraints from message
   - Build WHERE clause: "title MATCH 'cotton' AND price < 100"
   - Return top 10 products

3. Session state management
   - Track constraints per session
   - Track asked_attributes
   - Manage conversation history

4. Question generation (information gain)
   - Attribute priority: Budget > Use Case > Material > Style > Color > Size
   - Ask unanswered, high-value attributes first
```

**Testing:**
```bash
python3 -m evaluator.local_evaluator 2>&1 | tail -20
```

**Expected Result:**
- Hit Rate: 30-35%
- MRR: 0.025-0.030
- MTTC: 7-8
- Latency: <100ms/turn
- Status: ✅ Baseline working, pure Python

---

### PHASE 2: Week 2 (Add Light LLM)
**Goal:** 40-48% hit rate with Ollama

```bash
# Step 1: Install Ollama
curl https://ollama.ai/install.sh | sh  # or download from ollama.ai
ollama pull mistral
ollama serve &  # Start in background
```

```python
# Step 2: Add LLM fallback to agent.py
import requests

def respond(self, session_id, user_message, turn, top_k):
    # Try regex first (fast, no LLM)
    constraints = self._extract_constraints_regex(user_message)
    
    # If regex found nothing, use LLM fallback
    if not constraints:
        constraints = self._extract_constraints_llm(user_message)
    
    # Rest is same: BM25 filter, question gen, etc.
    ...

def _extract_constraints_llm(self, message: str) -> dict:
    """Only call LLM if regex extraction failed"""
    prompt = (
        "Extract shopping attributes (material, color, size, budget, style, use_case) "
        "from this customer message. Return as Python dict.\n\n"
        f"Message: {message}"
    )
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
            },
            timeout=10
        )
        # Parse response, extract dict
        return self._parse_llm_response(response.json()["response"])
    except:
        return {}  # Fall back to profile-based if LLM fails
```

**Testing:**
```bash
# Make sure Ollama running
curl http://localhost:11434/api/tags

# Run evaluator (will use LLM on failures)
python3 -m evaluator.local_evaluator
```

**Expected Result:**
- Hit Rate: 40-48% ⬆️
- MRR: 0.035-0.040 ⬆️
- MTTC: 5-6 ⬇️
- Latency: <500ms/turn (mostly regex, occasional LLM)
- LLM Calls: ~1-2 per session (only fallback cases)
- Status: ✅ Competitive! Ready to submit or continue tuning

---

### PHASE 3: Week 3 (Optional - Smart Routing)
**Goal:** 42-55% hit rate with scenario classification

```python
# Add turn-1 scenario classification
def respond(self, session_id, user_message, turn, top_k):
    if turn == 1:
        # Classify scenario once (buying/browsing/override/boundary)
        scenario = self._classify_scenario_llm(user_message)
        self.sessions[session_id]["scenario"] = scenario
    
    scenario = self.sessions[session_id].get("scenario", "browsing")
    
    # Route to best strategy per scenario
    if scenario == "buying":
        return self._respond_buying(user_message, session_id, top_k)
    elif scenario == "browsing":
        return self._respond_browsing(user_message, session_id, top_k)
    elif scenario == "override":
        return self._respond_override(user_message, session_id, top_k)
    else:  # boundary
        return self._respond_boundary(user_message, session_id, top_k)

def _classify_scenario_llm(self, message: str) -> str:
    prompt = (
        "Is this customer message representing:\n"
        "1. BUYING - explicit constraint mentioned (e.g., 'I want cotton, size M')\n"
        "2. BROWSING - vague, exploring options (e.g., 'something comfortable')\n"
        "3. OVERRIDE - changing mind (e.g., 'Actually, forget that, I need...')\n"
        "4. BOUNDARY - no preference (e.g., 'I don't have a preference')\n\n"
        f"Message: {message}\n\n"
        "Respond with only: BUYING, BROWSING, OVERRIDE, or BOUNDARY"
    )
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False},
        timeout=5
    )
    
    answer = response.json()["response"].strip().upper()
    return answer if answer in ["BUYING", "BROWSING", "OVERRIDE", "BOUNDARY"] else "browsing"
```

**Expected Result:**
- Hit Rate: 42-55% ⬆️
- MTTC: 5-6 (same)
- Latency: <500ms (1 LLM call turn 1, then no LLM turns 2-10)
- LLM Calls: ~0.14 per turn (1 per session!)
- Status: ✅ Very efficient! Scenario-optimized strategies

---

### PHASE 4: Week 4 (Optional - Ensemble Polish)
**Goal:** 45-60% hit rate with ensemble

```python
# Combine 3 retrieval systems
def respond(self, session_id, user_message, turn, top_k):
    # System A: Pure BM25
    results_bm25 = self._search_bm25(user_message, k=50)
    
    # System B: Constraint-based
    constraints = self._extract_constraints(user_message)
    results_constraint = self._filter_by_constraints(constraints, k=50)
    
    # System C: LLM reranking
    combined = self._merge_results([results_bm25, results_constraint])
    results_reranked = self._rerank_via_llm(combined, user_message, k=50)
    
    # Ensemble voting with scenario-adaptive weights
    scenario = self.sessions[session_id].get("scenario", "browsing")
    weights = self._get_weights_for_scenario(scenario)
    
    final_results = self._ensemble_vote(
        results_bm25, results_constraint, results_reranked,
        weights=[0.3, weights_constraint, weights_llm]
    )
    
    return {
        "message": question,
        "ask_attribute": attr,
        "recommendations": final_results[:top_k]
    }
```

**Expected Result:**
- Hit Rate: 45-60% ⬆️⬆️
- MTTC: 4-5 ⬇️
- Technical Score: 0.50-0.65 (winning territory!)
- Status: ✅ High-performance, ready to submit

---

## CODE STRUCTURE

### Minimal Changes to Baseline

```python
# starter/agent.py - Changes only

from __future__ import annotations
import json
import re
import sqlite3
import requests  # NEW
from pathlib import Path

# ... existing imports ...

class Agent:
    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        # ... existing init ...
        self.ollama_model = "mistral"  # NEW
        self.sessions = {}  # NEW: track per-session state
    
    def reset(self, session_id: str, user_profile: dict) -> None:
        # ... existing code ...
        # NEW: Initialize session state
        self.sessions[session_id] = {
            "user_profile": user_profile,
            "constraints": {},
            "asked_attributes": set(),
            "conversation_history": []
        }
    
    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        # NEW: Session state access
        if session_id not in self.sessions:
            raise RuntimeError("reset must be called before respond")
        
        session = self.sessions[session_id]
        
        # NEW: Extract constraints (regex primary)
        constraints = self._extract_constraints_regex(user_message)
        
        # NEW: LLM fallback if regex found nothing
        if not constraints:
            constraints = self._extract_constraints_llm(user_message)
        
        # ... existing BM25 logic but with constraint filtering ...
        
        # NEW: Question generation
        question = self._generate_next_question(session)
        
        # Return response
        return {
            "message": question,
            "ask_attribute": best_attr,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0}  # Could track LLM tokens
        }
    
    # NEW METHODS
    
    def _extract_constraints_regex(self, message: str) -> dict:
        """Fast regex-based constraint extraction"""
        constraints = {}
        
        # Material
        materials = ("cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon")
        for mat in materials:
            if re.search(rf'\b{mat}\b', message.lower()):
                constraints['material'] = mat
                break
        
        # Color
        colors = ("black", "white", "blue", "red", "pink", "green", "brown", "gray", "purple", "yellow", "orange")
        for color in colors:
            if re.search(rf'\b{color}\b', message.lower()):
                constraints['color'] = color
                break
        
        # Budget
        budget_match = re.search(r'\$(\d+)', message)
        if budget_match:
            constraints['budget'] = float(budget_match.group(1))
        
        # Size
        sizes = ("xs", "s", "m", "l", "xl", "xxl", "32", "34", "36", "6", "8", "10", "12")
        for size in sizes:
            if re.search(rf'\b{size}\b', message.lower()):
                constraints['size'] = size
                break
        
        return constraints
    
    def _extract_constraints_llm(self, message: str) -> dict:
        """LLM fallback for constraint extraction"""
        prompt = (
            "Extract shopping constraints from this message. "
            "Return as Python dict with keys: material, color, size, budget, style, use_case\n\n"
            f"Message: {message}\n\nDict:"
        )
        
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                timeout=5
            )
            response_text = json.loads(response.text)["response"]
            # Parse dict from response
            return self._parse_dict_from_text(response_text)
        except:
            return {}
    
    def _generate_next_question(self, session: dict) -> str:
        """Generate best next question based on information gain"""
        asked = session.get("asked_attributes", set())
        attributes = ["budget", "use_case", "material", "style", "color", "size"]
        
        # Find best unanswered attribute
        for attr in attributes:
            if attr not in asked:
                session["asked_attributes"].add(attr)
                
                questions = {
                    "budget": "What's your budget range?",
                    "use_case": "What will you use this for?",
                    "material": "Do you prefer a specific material?",
                    "style": "What style are you looking for?",
                    "color": "Do you have a color preference?",
                    "size": "What size do you need?"
                }
                return questions[attr]
        
        return "Let me show you the best options I found."
    
    def _parse_dict_from_text(self, text: str) -> dict:
        """Parse Python dict from LLM response"""
        try:
            # Try to extract dict from text
            import ast
            return ast.literal_eval(text)
        except:
            return {}
```

---

## TESTING CHECKLIST

- [ ] Ollama installed and running (`ollama serve`)
- [ ] Mistral model downloaded (`ollama pull mistral`)
- [ ] Ollama accessible at `http://localhost:11434`
- [ ] Phase 1 tests pass: `python3 -m evaluator.local_evaluator`
- [ ] Hit rate >30% on public set
- [ ] No crashes on edge cases (empty query, invalid input)
- [ ] Override detection working (turn 3-4)
- [ ] Phase 2: Add LLM fallback
- [ ] Hit rate >40% on public set
- [ ] Latency <500ms per turn
- [ ] LLM calls logged and trackable

---

## COMMON ISSUES & FIXES

**Issue:** "Connection refused: localhost:11434"
→ Fix: Start Ollama: `ollama serve`

**Issue:** "Mistral not found"
→ Fix: `ollama pull mistral`

**Issue:** LLM responses very slow (>2s per call)
→ Fix: Switch to Phi: `ollama pull phi`

**Issue:** Hit rate stuck at 30%
→ Fix: Improve regex patterns, add more constraint detection

**Issue:** MTTC still high (>7 turns)
→ Fix: Improve question sequencing, prioritize high-discriminative attributes

**Issue:** Memory usage >8GB
→ Fix: Make sure Ollama running separately in background, not in Python process

---

## SUCCESS METRICS

| Phase | Hit Rate | MTTC | Implementation | Status |
|---|---|---|---|---|
| Phase 1 (Regex only) | 30-35% | 7-8 | Day 1-5 | ✅ Foundation |
| Phase 2 (+ Light LLM) | 40-48% | 5-6 | Day 6-10 | ✅ Competitive |
| Phase 3 (+ Routing) | 42-55% | 5-6 | Day 11-15 | ✅ Optimized |
| Phase 4 (+ Ensemble) | 45-60% | 4-5 | Day 16-20 | ✅ High Performance |

**Target:** Phase 2 (40-48%) is competitive. Phase 3+ if time permits.

---

