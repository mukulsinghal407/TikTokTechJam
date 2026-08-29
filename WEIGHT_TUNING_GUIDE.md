# Rule-Based Ranking: Weight Tuning Guide
## Systematic Hyperparameter Tuning for Local Competition

---

## Overview

You have ranking features:
```
score = w1 * constraint_match + w2 * bm25_score + w3 * profile_similarity + w4 * popularity
```

**Goal:** Find optimal weights (w1, w2, w3, w4) that maximize technical score on public set, without overfitting to private test set.

**Constraint:** 200 public sessions only (small dataset)

---

## Step 1: Define Your Features

First, decide which features to rank by. Recommended:

```python
def compute_ranking_features(product: dict, user_message: str, constraints: dict, user_profile: dict, turn: int) -> dict:
    """
    Compute all ranking features for a product.
    Returns dict with features normalized to [0, 1]
    """
    
    features = {}
    
    # Feature 1: Constraint Satisfaction (0-1)
    # How many explicit constraints does this product satisfy?
    satisfied_constraints = sum(
        1 for attr, value in constraints.items()
        if matches_constraint(product, attr, value)
    )
    features['constraint_match'] = satisfied_constraints / max(len(constraints), 1)
    
    # Feature 2: BM25 Score (normalized 0-1)
    # How well does product text match the query?
    bm25_score = get_bm25_score(product, user_message)  # Already from search
    features['bm25_normalized'] = min(bm25_score / 100, 1.0)  # Cap at 1.0
    
    # Feature 3: Profile Similarity (0-1)
    # Does this product match user's historical preferences?
    user_rating_for_brand = user_profile.get('brand_ratings', {}).get(product['brand'], 0)
    user_price_affinity = 1.0 if product['price'] in user_profile.get('price_range', (0, 10000)) else 0.5
    features['profile_similarity'] = (user_rating_for_brand + user_price_affinity) / 2
    
    # Feature 4: Popularity (0-1)
    # Is this product popular/well-reviewed?
    features['popularity'] = (product.get('average_rating', 0) / 5.0) * (min(product.get('rating_number', 0), 1000) / 1000)
    
    # Feature 5: Recency of Constraints (turn-aware)
    # Recent constraints are more important than old ones
    features['recency_boost'] = 1.0 + (turn / 10.0) * 0.1  # Slightly boost popular products over time
    
    # Feature 6: Category Match (0-1)
    # Does product category match user's preferences?
    user_categories = user_profile.get('purchased_categories', [])
    product_categories = product.get('categories', [])
    category_overlap = len(set(user_categories) & set(product_categories)) / max(len(user_categories), 1)
    features['category_match'] = category_overlap
    
    return features

def score_product(features: dict, weights: dict) -> float:
    """
    Compute final score as weighted combination of features.
    
    weights = {
        'constraint_match': 0.50,
        'bm25_normalized': 0.20,
        'profile_similarity': 0.15,
        'popularity': 0.10,
        'category_match': 0.05
    }
    """
    score = sum(features.get(feat, 0) * weights.get(feat, 0) for feat in weights)
    return score
```

**Key insight:** Normalize all features to [0, 1] so weights are comparable.

---

## Step 2: Grid Search for Optimal Weights

```python
import json
from itertools import product
from pathlib import Path
from evaluator.local_evaluator import (
    load_jsonl, catalog_index, normalize_recommendations, 
    evaluate, coarse_category, initial_message, customer_reply,
    intent_card, behavior_for, materialize_hidden_fields,
    metric_summary
)
from starter.agent import Agent

class WeightTuner:
    """
    Systematically search for best ranking weights.
    """
    
    def __init__(self, agent_class, public_set_path: str, catalog_path: str):
        self.agent_class = agent_class
        self.public_set = load_jsonl(public_set_path)
        self.catalog_ids, self.categories, self.products = catalog_index(catalog_path)
    
    def grid_search(
        self,
        weight_ranges: dict,
        step_size: float = 0.1,
        use_cross_validation: bool = True,
        n_folds: int = 5
    ) -> dict:
        """
        Grid search over weight ranges.
        
        Args:
            weight_ranges: {
                'constraint_match': (0.2, 0.7),  # min, max
                'bm25_normalized': (0.1, 0.5),
                'profile_similarity': (0.05, 0.3),
                'popularity': (0.0, 0.2),
                'category_match': (0.0, 0.2),
            }
            step_size: How fine-grained the search (0.1 = coarse, 0.05 = fine)
            use_cross_validation: Use 5-fold CV instead of full train
            n_folds: Number of CV folds
        
        Returns:
            {
                'best_weights': {...},
                'best_score': 0.45,
                'search_results': [all_configurations],
                'cv_scores': [list of scores per fold]
            }
        """
        
        # Generate all weight combinations
        weight_keys = list(weight_ranges.keys())
        min_vals = [weight_ranges[k][0] for k in weight_keys]
        max_vals = [weight_ranges[k][1] for k in weight_keys]
        
        # Create grid
        ranges = [
            [v for v in np.arange(mn, mx + step_size, step_size)]
            for mn, mx in zip(min_vals, max_vals)
        ]
        
        print(f"Searching {np.prod([len(r) for r in ranges]):.0f} weight combinations...")
        
        best_score = -1
        best_weights = None
        all_results = []
        
        for weight_combo in product(*ranges):
            weights = {k: v for k, v in zip(weight_keys, weight_combo)}
            
            # Normalize weights to sum to 1.0
            weight_sum = sum(weights.values())
            weights = {k: v/weight_sum for k, v in weights.items()}
            
            if use_cross_validation:
                # 5-fold cross-validation
                cv_scores = self._cross_validate_weights(weights, n_folds)
                avg_score = np.mean(cv_scores)
                std_score = np.std(cv_scores)
            else:
                # Full evaluation (risk of overfitting)
                agent = self.agent_class()
                results = self._evaluate_weights(weights, agent)
                avg_score = results['recommended_technical_score']
                std_score = 0
                cv_scores = None
            
            result = {
                'weights': weights,
                'score': avg_score,
                'std': std_score,
                'cv_scores': cv_scores
            }
            all_results.append(result)
            
            if avg_score > best_score:
                best_score = avg_score
                best_weights = weights
                print(f"New best: score={avg_score:.4f}, weights={weights}")
        
        return {
            'best_weights': best_weights,
            'best_score': best_score,
            'search_results': all_results,
            'top_10': sorted(all_results, key=lambda x: x['score'], reverse=True)[:10]
        }
    
    def _cross_validate_weights(self, weights: dict, n_folds: int = 5) -> list:
        """
        5-fold cross-validation on public set.
        Returns list of scores per fold.
        """
        from sklearn.model_selection import StratifiedKFold
        
        cv_scores = []
        
        # Stratify by scenario type (to preserve distribution)
        scenarios = [s['scenario_type'] for s in self.public_set]
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
        
        for fold_idx, (train_idx, val_idx) in enumerate(skf.split(self.public_set, scenarios)):
            # Note: We don't actually train on train_idx, we just test on val_idx
            # The weights are fixed, we're just checking robustness across different data splits
            
            val_samples = [self.public_set[i] for i in val_idx]
            
            # Create agent with these weights
            agent = self.agent_class()
            agent.ranking_weights = weights  # Inject weights
            
            # Evaluate on validation fold
            results = self._evaluate_on_samples(weights, agent, val_samples)
            fold_score = results['recommended_technical_score']
            cv_scores.append(fold_score)
            
            print(f"  Fold {fold_idx+1}/{n_folds}: {fold_score:.4f}")
        
        return cv_scores
    
    def _evaluate_weights(self, weights: dict, agent: 'Agent') -> dict:
        """
        Evaluate weights on full public set.
        Returns metrics dict.
        """
        agent.ranking_weights = weights
        results = evaluate(agent, self.public_set, self.catalog_ids, self.categories, self.products)
        return results
    
    def _evaluate_on_samples(self, weights: dict, agent: 'Agent', samples: list) -> dict:
        """
        Evaluate weights on specific samples.
        """
        agent.ranking_weights = weights
        results = evaluate(agent, samples, self.catalog_ids, self.categories, self.products)
        return results

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

import numpy as np

# Define weight ranges to search
weight_ranges = {
    'constraint_match': (0.3, 0.7),      # High impact: explicit constraints
    'bm25_normalized': (0.1, 0.4),       # Medium: keyword matching
    'profile_similarity': (0.05, 0.25),  # Low-medium: user preferences
    'popularity': (0.0, 0.15),           # Low: overall popularity
    'category_match': (0.0, 0.15),       # Low: category alignment
}

# Initialize tuner
tuner = WeightTuner(
    agent_class=Agent,
    public_set_path='data/public_set.jsonl',
    catalog_path='data/catalog.jsonl'
)

# Grid search
print("Starting grid search with 5-fold CV...")
results = tuner.grid_search(
    weight_ranges=weight_ranges,
    step_size=0.1,           # Coarse-grained (5x5 per feature)
    use_cross_validation=True,
    n_folds=5
)

# Display results
print("\n" + "="*60)
print("GRID SEARCH RESULTS")
print("="*60)
print(f"\nBest Technical Score: {results['best_score']:.4f}")
print(f"Best Weights: {results['best_weights']}")

print("\nTop 10 Weight Configurations:")
for i, result in enumerate(results['top_10'], 1):
    print(f"\n{i}. Score: {result['score']:.4f} (std: {result['std']:.4f})")
    print(f"   Weights: {result['weights']}")
    if result['cv_scores']:
        print(f"   CV scores: {[f'{s:.4f}' for s in result['cv_scores']]}")

# Save results
with open('weight_tuning_results.json', 'w') as f:
    # Convert numpy types to JSON-serializable
    clean_results = {
        'best_weights': results['best_weights'],
        'best_score': float(results['best_score']),
        'top_10': [
            {
                'score': float(r['score']),
                'std': float(r['std']),
                'weights': r['weights'],
                'cv_scores': [float(s) for s in r['cv_scores']] if r['cv_scores'] else None
            }
            for r in results['top_10']
        ]
    }
    json.dump(clean_results, f, indent=2)
    print("\n✅ Results saved to weight_tuning_results.json")
```

---

## Step 3: Random Search (Faster Alternative)

If grid search is too slow:

```python
import random
import numpy as np

def random_search(
    agent_class,
    public_set_path: str,
    catalog_path: str,
    weight_ranges: dict,
    n_iterations: int = 100,
    n_folds: int = 5
) -> dict:
    """
    Random search instead of grid search.
    Faster for large weight spaces, finds good solutions quickly.
    """
    
    tuner = WeightTuner(agent_class, public_set_path, catalog_path)
    
    best_score = -1
    best_weights = None
    all_results = []
    
    print(f"Random search: {n_iterations} iterations with {n_folds}-fold CV...")
    
    for iteration in range(n_iterations):
        # Sample random weights
        weights = {}
        for feature, (min_w, max_w) in weight_ranges.items():
            weights[feature] = random.uniform(min_w, max_w)
        
        # Normalize
        weight_sum = sum(weights.values())
        weights = {k: v/weight_sum for k, v in weights.items()}
        
        # Cross-validate
        cv_scores = tuner._cross_validate_weights(weights, n_folds)
        avg_score = np.mean(cv_scores)
        
        result = {
            'weights': weights,
            'score': avg_score,
            'std': np.std(cv_scores),
            'cv_scores': cv_scores
        }
        all_results.append(result)
        
        if avg_score > best_score:
            best_score = avg_score
            best_weights = weights
            print(f"Iteration {iteration+1}: New best score={avg_score:.4f}")
    
    return {
        'best_weights': best_weights,
        'best_score': best_score,
        'search_results': all_results,
        'top_10': sorted(all_results, key=lambda x: x['score'], reverse=True)[:10]
    }
```

---

## Step 4: Iterative Manual Tuning (Quickest)

If you want fastest feedback:

```python
def manual_tune(agent_class, public_set_path: str, catalog_path: str):
    """
    Manually tune weights with immediate feedback.
    Best for quick iteration.
    """
    
    tuner = WeightTuner(agent_class, public_set_path, catalog_path)
    
    # Start with baseline
    current_weights = {
        'constraint_match': 0.50,
        'bm25_normalized': 0.25,
        'profile_similarity': 0.15,
        'popularity': 0.05,
        'category_match': 0.05
    }
    
    print("Starting manual tuning...")
    print(f"Initial weights: {current_weights}")
    
    iteration = 0
    
    while True:
        # Evaluate current weights
        agent = agent_class()
        cv_scores = tuner._cross_validate_weights(current_weights, n_folds=5)
        avg_score = np.mean(cv_scores)
        
        print(f"\nIteration {iteration}")
        print(f"  Score: {avg_score:.4f} (std: {np.std(cv_scores):.4f})")
        print(f"  Weights: {current_weights}")
        
        # Try small perturbations
        best_new_weights = current_weights
        best_new_score = avg_score
        
        feature_order = ['constraint_match', 'bm25_normalized', 'profile_similarity', 'popularity', 'category_match']
        
        for feature in feature_order:
            # Try +10% and -10% adjustments
            for delta in [0.1, -0.1]:
                new_weights = current_weights.copy()
                new_weights[feature] += delta
                
                # Normalize
                weight_sum = sum(new_weights.values())
                if weight_sum > 0:
                    new_weights = {k: v/weight_sum for k, v in new_weights.items()}
                    
                    # Quick eval (just 3-fold, faster)
                    cv_scores = tuner._cross_validate_weights(new_weights, n_folds=3)
                    new_score = np.mean(cv_scores)
                    
                    if new_score > best_new_score:
                        best_new_score = new_score
                        best_new_weights = new_weights
                        print(f"    ✓ Improve by adjusting {feature}: {new_score:.4f}")
        
        # If no improvement found, stop
        if best_new_score <= avg_score:
            print("\nNo improvement found. Stopping.")
            break
        
        current_weights = best_new_weights
        iteration += 1
        
        if iteration > 20:
            print("Max iterations reached.")
            break
    
    print(f"\nFinal weights: {current_weights}")
    return current_weights
```

---

## Step 5: Integrate into Your Agent

Once you have best weights:

```python
# In starter/agent.py

class Agent:
    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        # ... existing init ...
        
        # Load tuned weights from tuning results
        self.ranking_weights = {
            'constraint_match': 0.50,     # ← Your tuned values here
            'bm25_normalized': 0.25,
            'profile_similarity': 0.15,
            'popularity': 0.05,
            'category_match': 0.05
        }
    
    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        # ... existing retrieval logic ...
        
        # Get top 100 candidates
        candidates = self._retrieve_candidates(user_message, k=100)
        
        # Rank using tuned weights
        scored_candidates = []
        for product in candidates:
            features = compute_ranking_features(product, user_message, constraints, user_profile, turn)
            score = score_product(features, self.ranking_weights)
            scored_candidates.append((product['parent_asin'], score))
        
        # Return top 10
        recommendations = [
            {'parent_asin': asin}
            for asin, score in sorted(scored_candidates, key=lambda x: -x[1])[:top_k]
        ]
        
        return {
            "message": question,
            "ask_attribute": attr,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0}
        }
```

---

## Step 6: Comparison - Which Tuning Method?

| Method | Speed | Accuracy | Risk | Best For |
|---|---|---|---|---|
| **Grid Search** | Slow (hours) | Best | Lowest (exhaustive) | Final optimization |
| **Random Search** | Medium (30 min) | Good | Low (samples well) | First pass |
| **Manual Tuning** | Fast (5 min/iter) | Good | Medium (greedy) | Quick iteration |
| **Bayesian Opt** | Medium (1 hour) | Best | Low | If you know ML |

**My recommendation: Start with Random Search (fast), then Grid Search (best).**

---

## Step 7: Avoid Overfitting to Public Set

**Critical rule:** Don't tune too aggressively!

```python
# ❌ BAD: Overfitting
tuner = WeightTuner(...)
results = tuner.grid_search(weight_ranges, use_cross_validation=False)
# Result: Great on public (95%), terrible on private (35%)

# ✅ GOOD: Cross-validation prevents overfitting
tuner = WeightTuner(...)
results = tuner.grid_search(weight_ranges, use_cross_validation=True, n_folds=5)
# Result: Good on public (45%), good on private (42-48%)
```

**Why?** 5-fold CV simulates having different test sets. If weights overfit to one fold, they'll perform worse on average. This correlates with private set performance.

---

## Step 8: Interpret Results

```python
# After tuning
results = tuner.grid_search(...)

print("Best weights by feature importance:")
weights = results['best_weights']
sorted_weights = sorted(weights.items(), key=lambda x: -x[1])

for feature, weight in sorted_weights:
    print(f"  {feature}: {weight:.3f} ({weight*100:.1f}%)")

# Example output:
#   constraint_match: 0.550 (55.0%)   ← Most important
#   bm25_normalized: 0.250 (25.0%)
#   profile_similarity: 0.120 (12.0%)
#   category_match: 0.050 (5.0%)
#   popularity: 0.030 (3.0%)           ← Least important
```

**Interpretation:**
- `constraint_match=0.55`: Explicit constraints matter most (as expected!)
- `bm25_normalized=0.25`: Keyword relevance is secondary
- `profile_similarity=0.12`: User preferences help but less critical
- `popularity/category=0.08`: Minor boosters

If results show very different weights (e.g., constraint=0.1), you might have:
- ❌ Bugs in constraint extraction
- ❌ Bad feature normalization
- ❌ Overfitting
- → Re-check your feature computation!

---

## Full Example: Run This End-to-End

```python
#!/usr/bin/env python3
"""
Complete weight tuning pipeline.
Run: python3 tune_weights.py
"""

import numpy as np
import json
from starter.agent import Agent
from weight_tuner import WeightTuner, random_search

def main():
    print("="*60)
    print("WEIGHT TUNING PIPELINE")
    print("="*60)
    
    # ===== STEP 1: Random Search (fast initial pass)
    print("\n[STEP 1] Random Search (100 iterations)...")
    random_results = random_search(
        agent_class=Agent,
        public_set_path='data/public_set.jsonl',
        catalog_path='data/catalog.jsonl',
        weight_ranges={
            'constraint_match': (0.3, 0.7),
            'bm25_normalized': (0.1, 0.4),
            'profile_similarity': (0.05, 0.25),
            'popularity': (0.0, 0.15),
            'category_match': (0.0, 0.15),
        },
        n_iterations=100,
        n_folds=3  # Quick, 3-fold
    )
    
    print(f"\nRandom Search Best Score: {random_results['best_score']:.4f}")
    print(f"Best Weights: {random_results['best_weights']}")
    
    # ===== STEP 2: Fine Grid Search around best random result
    print("\n[STEP 2] Fine Grid Search (5-fold CV)...")
    
    # Get ranges around best random result
    best_w = random_results['best_weights']
    fine_ranges = {
        'constraint_match': (max(0.0, best_w['constraint_match'] - 0.1), 
                            min(1.0, best_w['constraint_match'] + 0.1)),
        'bm25_normalized': (max(0.0, best_w['bm25_normalized'] - 0.1),
                           min(1.0, best_w['bm25_normalized'] + 0.1)),
        'profile_similarity': (max(0.0, best_w['profile_similarity'] - 0.05),
                              min(1.0, best_w['profile_similarity'] + 0.05)),
        'popularity': (max(0.0, best_w['popularity'] - 0.05),
                      min(1.0, best_w['popularity'] + 0.05)),
        'category_match': (max(0.0, best_w['category_match'] - 0.05),
                          min(1.0, best_w['category_match'] + 0.05)),
    }
    
    tuner = WeightTuner(Agent, 'data/public_set.jsonl', 'data/catalog.jsonl')
    grid_results = tuner.grid_search(
        weight_ranges=fine_ranges,
        step_size=0.05,  # Fine-grained
        use_cross_validation=True,
        n_folds=5
    )
    
    print(f"\nGrid Search Best Score: {grid_results['best_score']:.4f}")
    print(f"Best Weights: {grid_results['best_weights']}")
    
    # ===== STEP 3: Save final weights
    print("\n[STEP 3] Saving final weights...")
    
    final_config = {
        'weights': grid_results['best_weights'],
        'score': float(grid_results['best_score']),
        'method': 'grid_search_with_cv',
        'random_search_baseline': {
            'weights': random_results['best_weights'],
            'score': float(random_results['best_score'])
        }
    }
    
    with open('optimal_ranking_weights.json', 'w') as f:
        json.dump(final_config, f, indent=2)
    
    print("✅ Optimal weights saved to optimal_ranking_weights.json")
    
    # ===== STEP 4: Verify performance
    print("\n[STEP 4] Verifying performance...")
    agent = Agent()
    agent.ranking_weights = grid_results['best_weights']
    
    results = tuner._evaluate_weights(grid_results['best_weights'], agent)
    
    print(f"\nFinal Performance Metrics:")
    print(f"  Hit Rate: {results['hit_rate_at_10']:.1%}")
    print(f"  MRR: {results['mrr']:.4f}")
    print(f"  MTTC: {results['mttc']:.2f}")
    print(f"  Technical Score: {results['recommended_technical_score']:.4f}")

if __name__ == "__main__":
    main()
```

---

## Summary: Quick Decision

| Your Situation | Recommended Approach |
|---|---|
| "I have 1 hour, give me decent weights" | Random Search |
| "I want the BEST weights, have time" | Grid Search + CV |
| "I want to iterate quickly, learn weights" | Manual Tuning |
| "I'm on limited hardware (8GB)" | Random Search (fewer CV folds) |

**For your 8GB laptop with Ollama running:**
1. Start with Random Search: 50-100 iterations, 3-fold CV (15 min)
2. Then fine Grid Search: 0.05 step size, 5-fold CV (30 min)
3. Total: 45 minutes → optimal weights

---

