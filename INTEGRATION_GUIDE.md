# How to Integrate Tuned Weights into Your Agent
## Quick Integration Guide

---

## Step 1: Run Weight Tuning (One Time)

```bash
# Copy weight_tuner.py to your project root
python3 weight_tuner.py

# Output: optimal_ranking_weights.json
```

This generates:
```json
{
  "optimal_weights": {
    "constraint_match": 0.550,
    "bm25_normalized": 0.250,
    "profile_similarity": 0.120,
    "popularity": 0.050,
    "category_match": 0.030
  },
  "score": 0.452,
  "method": "random_search + grid_search"
}
```

---

## Step 2: Update starter/agent.py

Add ranking feature computation and weighting:

```python
# At top of file, add imports
import json
from pathlib import Path

# In Agent.__init__(), add ranking weights
class Agent:
    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        # ... existing initialization ...
        
        # NEW: Load optimal ranking weights
        self.ranking_weights = self._load_ranking_weights()
        
        # Track session state
        self.sessions = {}
    
    def _load_ranking_weights(self) -> dict:
        """Load optimal weights from tuning, fallback to defaults"""
        weights_file = Path('optimal_ranking_weights.json')
        
        if weights_file.exists():
            try:
                with open(weights_file) as f:
                    config = json.load(f)
                    print(f"✅ Loaded optimal weights from {weights_file}")
                    return config['optimal_weights']
            except Exception as e:
                print(f"⚠️ Could not load weights: {e}, using defaults")
        
        # Default fallback weights
        return {
            'constraint_match': 0.50,
            'bm25_normalized': 0.25,
            'profile_similarity': 0.15,
            'popularity': 0.05,
            'category_match': 0.05
        }

# In respond() method, update the ranking section:
    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        # ... existing retrieval logic ...
        
        # After getting candidates from BM25, rank them using tuned weights
        
        # Step 1: Extract constraints from user message
        constraints = self._extract_constraints_regex(user_message)
        
        # Step 2: If no constraints, try LLM fallback
        if not constraints:
            constraints = self._extract_constraints_llm(user_message)
        
        # Step 3: BM25 search to get candidates
        bm25_results = self.connection.execute(
            "SELECT parent_asin FROM products WHERE products MATCH ?",
            (user_message,)
        ).fetchall()
        candidate_ids = [row[0] for row in bm25_results[:100]]  # Top 100
        
        # Step 4: Rank candidates using tuned weights
        scored_candidates = []
        
        for asin in candidate_ids:
            product = self.products.get(asin, {})
            
            # Compute ranking features
            features = self._compute_ranking_features(
                product=product,
                user_message=user_message,
                constraints=constraints,
                user_profile=self.sessions[session_id]['user_profile'],
                top_k_candidates=len(candidate_ids)
            )
            
            # Score using tuned weights
            score = self._score_product(features, self.ranking_weights)
            
            scored_candidates.append((asin, score))
        
        # Step 5: Return top-k
        recommendations = [
            {'parent_asin': asin}
            for asin, score in sorted(scored_candidates, key=lambda x: -x[1])[:top_k]
        ]
        
        # Step 6: Generate question and return response
        question = self._generate_next_question(session_id)
        next_attr = self._get_best_attribute(session_id)
        
        return {
            "message": question,
            "ask_attribute": next_attr,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0}
        }

# NEW METHODS to add:

    def _compute_ranking_features(self, product, user_message, constraints, user_profile, top_k_candidates):
        """Compute all ranking features for a product"""
        features = {}
        
        # Feature 1: Constraint Satisfaction
        if constraints:
            satisfied = sum(
                1 for attr, val in constraints.items()
                if self._constraint_matches(product, attr, val)
            )
            features['constraint_match'] = satisfied / len(constraints)
        else:
            features['constraint_match'] = 0.5
        
        # Feature 2: BM25 Score (estimated from keyword overlap)
        keywords = set(user_message.lower().split())
        product_text = self._get_product_text(product).lower()
        keyword_matches = sum(1 for kw in keywords if kw in product_text)
        features['bm25_normalized'] = min(keyword_matches / 10.0, 1.0)
        
        # Feature 3: Profile Similarity
        profile_score = 0.0
        brand_rating = user_profile.get('brand_ratings', {}).get(product.get('brand', ''), 0)
        profile_score += (brand_rating / 5.0) * 0.5
        
        try:
            price = float(product.get('price', 0))
            price_range = user_profile.get('price_range', (0, 10000))
            if price_range[0] <= price <= price_range[1]:
                profile_score += 0.5
            else:
                profile_score += 0.25
        except:
            profile_score += 0.25
        
        features['profile_similarity'] = min(profile_score, 1.0)
        
        # Feature 4: Popularity
        try:
            rating = float(product.get('average_rating', 0)) / 5.0
            count = min(int(product.get('rating_number', 0)), 1000) / 1000.0
            features['popularity'] = (rating * count) ** 0.5
        except:
            features['popularity'] = 0.5
        
        # Feature 5: Category Match
        product_cats = set(str(c).lower() for c in product.get('categories', []))
        user_cats = set(str(c).lower() for c in user_profile.get('purchased_categories', []))
        
        if user_cats:
            features['category_match'] = len(product_cats & user_cats) / len(user_cats)
        else:
            features['category_match'] = 0.5
        
        return features
    
    def _score_product(self, features, weights):
        """Compute weighted score"""
        score = 0.0
        for feature_name, weight in weights.items():
            if feature_name in features:
                score += features[feature_name] * weight
        return score
    
    def _constraint_matches(self, product, attr, val):
        """Check if product satisfies a constraint"""
        if attr == 'material':
            return any(m.lower() == val.lower() for m in self._get_materials(product))
        elif attr == 'color':
            return any(c.lower() == val.lower() for c in self._get_colors(product))
        elif attr == 'budget':
            try:
                return float(product.get('price', 0)) <= val
            except:
                return False
        elif attr == 'size':
            return any(s.lower() == val.lower() for s in self._get_sizes(product))
        else:
            return val.lower() in self._get_product_text(product).lower()
    
    def _get_product_text(self, product):
        """Extract searchable text from product"""
        parts = []
        for field in ['title', 'description', 'features']:
            val = product.get(field)
            if isinstance(val, list):
                parts.extend(str(v) for v in val)
            elif val:
                parts.append(str(val))
        return ' '.join(parts)
    
    def _get_materials(self, product):
        materials = []
        for mat in ['cotton', 'polyester', 'nylon', 'leather', 'wool', 'spandex', 'silk', 'rayon']:
            if mat in self._get_product_text(product).lower():
                materials.append(mat)
        return materials
    
    def _get_colors(self, product):
        colors = []
        for color in ['black', 'white', 'blue', 'red', 'pink', 'green', 'brown', 'gray', 'purple', 'yellow', 'orange']:
            if color in self._get_product_text(product).lower():
                colors.append(color)
        return colors
    
    def _get_sizes(self, product):
        sizes = []
        for size in ['xs', 's', 'm', 'l', 'xl', 'xxl', '32', '34', '36', '38']:
            if size in self._get_product_text(product).lower():
                sizes.append(size)
        return sizes
```

---

## Step 3: Test Integration

```bash
# Run local evaluator
python3 -m evaluator.local_evaluator

# Look for improved metrics:
# - Hit Rate should increase (hopefully to 40-50%)
# - MTTC should decrease (hopefully to 5-6 turns)
# - MRR should improve (hopefully to 0.035-0.048)
```

---

## Step 4: Iterate if Needed

If metrics don't improve as expected:

```bash
# Re-tune weights with more iterations
python3 weight_tuner.py --iterations 100

# Check if constraint_match weight is too high/low
# Expected: constraint_match should be 0.45-0.65
```

---

## Troubleshooting

**Issue: Weights loaded but hit rate not improving**
→ Check: Are features computing correctly?
→ Debug: Print feature values for a sample product
```python
product = self.products[list(self.products.keys())[0]]
features = self._compute_ranking_features(product, "test", {'material': 'cotton'}, {}, 100)
print("Features:", features)
print("Score:", self._score_product(features, self.ranking_weights))
```

**Issue: MTTC getting worse**
→ Check: Is constraint extraction working?
→ Debug: Print extracted constraints per turn
```python
constraints = self._extract_constraints_regex(user_message)
print(f"Turn {turn}: Constraints = {constraints}")
```

**Issue: Profile similarity always 0.5**
→ Check: Is user_profile populated correctly?
→ Debug: Print user profile in reset()
```python
def reset(self, session_id, user_profile):
    print(f"User profile: {user_profile}")
    # ... rest of reset
```

---

## Performance Tracking

After integration, track these metrics:

```python
# In your evaluation script
import json

with open('results.json') as f:
    results = json.load(f)

print(f"Hit Rate: {results['hit_rate_at_10']:.1%}")
print(f"MRR: {results['mrr']:.4f}")
print(f"MTTC: {results['mttc']:.2f}")
print(f"Technical Score: {results['recommended_technical_score']:.4f}")

# Compare with baseline
baseline_score = 0.107
improvement = (results['recommended_technical_score'] - baseline_score) / baseline_score * 100
print(f"Improvement over baseline: {improvement:.0f}%")
```

---

## When to Re-tune

Re-run `weight_tuner.py` if:
- Hit rate plateaus (not improving with more tuning)
- You add new features to ranking
- You change feature computation logic
- You get access to more data (tune again on expanded set)

---

## Quick Checklist

- [ ] Ran `python3 weight_tuner.py` successfully
- [ ] `optimal_ranking_weights.json` created
- [ ] Updated `starter/agent.py` with new methods
- [ ] Added `_load_ranking_weights()` to `__init__()`
- [ ] Updated `respond()` to use weighted ranking
- [ ] Ran `python3 -m evaluator.local_evaluator`
- [ ] Metrics improved (hit rate > 40%)?
- [ ] Saved optimal weights to git

---

