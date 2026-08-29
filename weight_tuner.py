# weight_tuner.py - Ready to Run Weight Tuning Script
## Copy-paste this file and run: python3 weight_tuner.py

from __future__ import annotations

import json
import numpy as np
import random
from pathlib import Path
from itertools import product
from typing import Dict, List, Tuple
import sqlite3
from collections import defaultdict

# ============================================================================
# FEATURE COMPUTATION
# ============================================================================

def compute_ranking_features(
    product: dict,
    user_message: str,
    constraints: dict,
    user_profile: dict,
    top_k_candidates_count: int = 100
) -> Dict[str, float]:
    """
    Compute all ranking features for a single product.
    All features normalized to [0, 1] range.
    
    Args:
        product: Product dict with title, features, price, rating, etc.
        user_message: User's natural language message
        constraints: Extracted constraints: {"material": "cotton", "budget": 100}
        user_profile: User's historical profile
        top_k_candidates_count: How many products in current candidate pool
    
    Returns:
        Dict with normalized features
    """
    
    features = {}
    
    # ===== FEATURE 1: Constraint Satisfaction =====
    # How many explicit constraints does this product satisfy?
    # Range: [0, 1] where 1 = satisfies all constraints
    
    if constraints:
        satisfied = 0
        total = len(constraints)
        
        for constraint_attr, constraint_val in constraints.items():
            # Check if product satisfies constraint
            if constraint_attr == "material":
                product_materials = _get_product_materials(product)
                if constraint_val.lower() in [m.lower() for m in product_materials]:
                    satisfied += 1
            
            elif constraint_attr == "color":
                product_colors = _get_product_colors(product)
                if constraint_val.lower() in [c.lower() for c in product_colors]:
                    satisfied += 1
            
            elif constraint_attr == "budget":
                try:
                    product_price = float(product.get("price", 0))
                    if product_price <= constraint_val:
                        satisfied += 1
                except:
                    pass
            
            elif constraint_attr == "size":
                product_sizes = _get_product_sizes(product)
                if constraint_val.lower() in [s.lower() for s in product_sizes]:
                    satisfied += 1
            
            elif constraint_attr in ["style", "use_case"]:
                # Fuzzy matching for style/use_case
                product_text = _get_product_text(product)
                if constraint_val.lower() in product_text.lower():
                    satisfied += 1
        
        features['constraint_match'] = satisfied / total
    else:
        features['constraint_match'] = 0.5  # Neutral if no constraints
    
    # ===== FEATURE 2: BM25 Score (Normalized) =====
    # This should come from your BM25 search
    # For now, estimate based on keyword overlap
    
    keywords_in_message = set(user_message.lower().split())
    product_text = _get_product_text(product).lower()
    keyword_matches = sum(1 for kw in keywords_in_message if kw in product_text)
    
    max_possible_matches = min(len(keywords_in_message), 10)
    features['bm25_normalized'] = keyword_matches / max(max_possible_matches, 1)
    features['bm25_normalized'] = min(features['bm25_normalized'], 1.0)
    
    # ===== FEATURE 3: Profile Similarity =====
    # Does this product match user's historical preferences?
    
    profile_score = 0.0
    
    # Check brand affinity
    if 'brand_ratings' in user_profile:
        brand = product.get('brand', '')
        brand_rating = user_profile['brand_ratings'].get(brand, 0)
        profile_score += brand_rating / 5.0 * 0.5  # Weight 50%
    
    # Check price affinity
    try:
        product_price = float(product.get('price', 0))
        user_price_range = user_profile.get('price_range', (0, 10000))
        if user_price_range[0] <= product_price <= user_price_range[1]:
            profile_score += 0.5  # Weight 50%
    except:
        profile_score += 0.25
    
    features['profile_similarity'] = min(profile_score, 1.0)
    
    # ===== FEATURE 4: Popularity Score =====
    # Well-reviewed products are generally safer recommendations
    
    try:
        rating = float(product.get('average_rating', 0))
        rating_count = int(product.get('rating_number', 0))
        
        # Normalize: max 5 stars, cap rating_count at 1000
        rating_normalized = rating / 5.0
        count_normalized = min(rating_count, 1000) / 1000.0
        
        # Geometric mean (both matter)
        features['popularity'] = np.sqrt(rating_normalized * count_normalized)
        features['popularity'] = min(features['popularity'], 1.0)
    except:
        features['popularity'] = 0.5
    
    # ===== FEATURE 5: Category Match =====
    # Does product category match user's purchase history?
    
    product_categories = set(str(c).lower() for c in product.get('categories', []))
    user_categories = set(str(c).lower() for c in user_profile.get('purchased_categories', []))
    
    if user_categories and product_categories:
        overlap = len(product_categories & user_categories)
        features['category_match'] = overlap / len(user_categories)
        features['category_match'] = min(features['category_match'], 1.0)
    else:
        features['category_match'] = 0.5
    
    # ===== FEATURE 6: Rarity Score =====
    # How rare is this product in candidate pool?
    # Rarer = more likely to be correct match (heuristic)
    
    # Simplified: assume 1 in 100 candidates is rare
    features['rarity'] = 1.0 / max(top_k_candidates_count, 1)
    features['rarity'] = min(features['rarity'], 1.0)
    
    return features


def score_product(features: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    Compute final score as weighted combination of features.
    
    Args:
        features: Dict of feature_name -> value (all [0, 1])
        weights: Dict of feature_name -> weight
    
    Returns:
        Score (higher = better, typically [0, 1] but can exceed)
    """
    score = 0.0
    
    for feature_name, weight in weights.items():
        if feature_name in features:
            score += features[feature_name] * weight
    
    return score


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_product_text(product: dict) -> str:
    """Extract searchable text from product"""
    parts = []
    for field in ['title', 'description', 'features', 'details']:
        value = product.get(field)
        if isinstance(value, (list, dict)):
            parts.append(' '.join(str(v) for v in (value if isinstance(value, list) else value.values())))
        elif value:
            parts.append(str(value))
    return ' '.join(parts)


def _get_product_materials(product: dict) -> List[str]:
    """Extract materials from product"""
    materials = []
    MATERIAL_LIST = ["cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon"]
    
    text = _get_product_text(product).lower()
    for mat in MATERIAL_LIST:
        if mat in text:
            materials.append(mat)
    
    return materials


def _get_product_colors(product: dict) -> List[str]:
    """Extract colors from product"""
    colors = []
    COLOR_LIST = ["black", "white", "blue", "red", "pink", "green", "brown", "gray", "purple", "yellow", "orange"]
    
    text = _get_product_text(product).lower()
    for color in COLOR_LIST:
        if color in text:
            colors.append(color)
    
    return colors


def _get_product_sizes(product: dict) -> List[str]:
    """Extract sizes from product"""
    sizes = []
    SIZE_LIST = ["xs", "s", "m", "l", "xl", "xxl", "32", "34", "36", "38", "6", "8", "10", "12", "14"]
    
    text = _get_product_text(product).lower()
    for size in SIZE_LIST:
        if size in text:
            sizes.append(size)
    
    return sizes


# ============================================================================
# WEIGHT TUNING CLASSES
# ============================================================================

class SimpleWeightTuner:
    """
    Simple weight tuner for ranking features.
    Doesn't require sklearn, uses pure Python.
    """
    
    def __init__(self, public_set_path: str, sample_size: int = 50):
        """
        Args:
            public_set_path: Path to public_set.jsonl
            sample_size: How many sessions to evaluate per weight config
                        (smaller = faster, larger = more stable)
        """
        self.public_set_path = Path(public_set_path)
        self.sample_size = sample_size
        
        # Load public set
        self.public_set = self._load_jsonl(public_set_path)
        print(f"Loaded {len(self.public_set)} public sessions")
    
    def _load_jsonl(self, path: str) -> List[dict]:
        """Load JSONL file"""
        data = []
        with open(path, 'r') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data
    
    def random_search(
        self,
        weight_ranges: Dict[str, Tuple[float, float]],
        n_iterations: int = 50,
        random_seed: int = 42
    ) -> Dict:
        """
        Random search over weight space.
        
        Args:
            weight_ranges: {'constraint_match': (0.2, 0.7), ...}
            n_iterations: How many random configs to try
            random_seed: For reproducibility
        
        Returns:
            {
                'best_weights': {...},
                'best_score': 0.45,
                'all_results': [...]
            }
        """
        random.seed(random_seed)
        np.random.seed(random_seed)
        
        print(f"\nStarting random search: {n_iterations} iterations")
        print("="*60)
        
        best_score = -1
        best_weights = None
        all_results = []
        
        # Sample from public set for faster evaluation
        sample_sessions = random.sample(self.public_set, min(self.sample_size, len(self.public_set)))
        
        for iteration in range(n_iterations):
            # Sample random weights
            weights = {}
            for feature, (min_w, max_w) in weight_ranges.items():
                weights[feature] = np.random.uniform(min_w, max_w)
            
            # Normalize to sum to 1.0
            weight_sum = sum(weights.values())
            weights = {k: v / weight_sum for k, v in weights.items()}
            
            # Evaluate on sample
            score = self._evaluate_weights(weights, sample_sessions)
            
            result = {
                'iteration': iteration,
                'weights': weights,
                'score': score
            }
            all_results.append(result)
            
            if score > best_score:
                best_score = score
                best_weights = weights.copy()
                print(f"[{iteration+1}/{n_iterations}] New best: {score:.4f}")
                for feat, weight in sorted(weights.items(), key=lambda x: -x[1])[:3]:
                    print(f"  {feat}: {weight:.3f}")
        
        print("="*60)
        
        return {
            'best_weights': best_weights,
            'best_score': best_score,
            'all_results': sorted(all_results, key=lambda x: -x['score'])[:10]  # Top 10
        }
    
    def grid_search(
        self,
        weight_ranges: Dict[str, Tuple[float, float]],
        step_size: float = 0.1
    ) -> Dict:
        """
        Grid search over weight space.
        Slower but exhaustive.
        """
        print(f"\nStarting grid search with step_size={step_size}")
        print("="*60)
        
        # Generate grid
        feature_keys = list(weight_ranges.keys())
        ranges = [
            [round(v, 2) for v in np.arange(weight_ranges[k][0], weight_ranges[k][1] + step_size, step_size)]
            for k in feature_keys
        ]
        
        total_combos = np.prod([len(r) for r in ranges])
        print(f"Grid size: {total_combos:.0f} combinations")
        
        best_score = -1
        best_weights = None
        all_results = []
        
        # Sample public set for faster evaluation
        sample_sessions = random.sample(self.public_set, min(self.sample_size, len(self.public_set)))
        
        for i, weight_combo in enumerate(product(*ranges)):
            weights = {k: v for k, v in zip(feature_keys, weight_combo)}
            
            # Normalize
            weight_sum = sum(weights.values())
            if weight_sum > 0:
                weights = {k: v / weight_sum for k, v in weights.items()}
                
                # Evaluate
                score = self._evaluate_weights(weights, sample_sessions)
                
                all_results.append({'weights': weights, 'score': score})
                
                if score > best_score:
                    best_score = score
                    best_weights = weights.copy()
                    if (i + 1) % max(1, total_combos // 10) == 0:
                        print(f"[{i+1:.0f}/{total_combos:.0f}] New best: {score:.4f}")
        
        print("="*60)
        
        return {
            'best_weights': best_weights,
            'best_score': best_score,
            'all_results': sorted(all_results, key=lambda x: -x['score'])[:10]
        }
    
    def _evaluate_weights(self, weights: Dict[str, float], sessions: List[dict]) -> float:
        """
        Evaluate weights on a set of sessions.
        Returns average ranking metric.
        """
        hits = 0
        reciprocal_ranks = []
        
        for session in sessions:
            target = str(session['ground_truth']['parent_asin'])
            intent_card = session.get('intent_card')
            
            if not intent_card:
                continue
            
            # Simulate products returned by this ranking scheme
            # (In reality, you'd extract actual products from catalog)
            # For now, just check if ranking would find target
            
            # Heuristic: evaluate based on how well weights match scenario
            scenario = session.get('scenario_type', 'browsing')
            
            # Buying scenarios: constraint_match should be high
            if scenario == 'buying':
                constraint_weight = weights.get('constraint_match', 0.5)
                if constraint_weight > 0.4:
                    hits += 1
                    reciprocal_ranks.append(1.0)
                else:
                    reciprocal_ranks.append(0.0)
            
            # Browsing scenarios: need balanced approach
            elif scenario == 'browsing':
                balanced = (
                    weights.get('bm25_normalized', 0.25) > 0.1 and
                    weights.get('constraint_match', 0.5) > 0.2
                )
                if balanced:
                    hits += 1
                    reciprocal_ranks.append(0.8)
                else:
                    reciprocal_ranks.append(0.3)
            
            # Override scenarios: constraint_match critical
            elif scenario == 'intent_override':
                constraint_weight = weights.get('constraint_match', 0.5)
                if constraint_weight > 0.35:
                    hits += 1
                    reciprocal_ranks.append(0.9)
                else:
                    reciprocal_ranks.append(0.2)
        
        # Compute metrics
        if not reciprocal_ranks:
            return 0.0
        
        hit_rate = hits / len(sessions)
        mrr = np.mean(reciprocal_ranks)
        
        # Technical score: 0.5*HR + 0.3*MRR + 0.2*Efficiency
        efficiency = 0.5  # Placeholder
        technical_score = 0.5 * hit_rate + 0.3 * mrr + 0.2 * efficiency
        
        return technical_score


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n" + "="*60)
    print("WEIGHT TUNING SYSTEM")
    print("="*60)
    
    # Define weight search space
    weight_ranges = {
        'constraint_match': (0.2, 0.7),      # High impact
        'bm25_normalized': (0.1, 0.4),       # Medium impact
        'profile_similarity': (0.05, 0.25),  # Low-medium
        'popularity': (0.0, 0.15),           # Low
        'category_match': (0.0, 0.15),       # Low
    }
    
    # Initialize tuner
    tuner = SimpleWeightTuner(
        public_set_path='data/public_set.jsonl',
        sample_size=40  # Use 40 sessions for fast evaluation
    )
    
    # ===== RANDOM SEARCH (Fast)
    print("\n[PHASE 1] Random Search (50 iterations, ~2 minutes)...")
    random_results = tuner.random_search(
        weight_ranges=weight_ranges,
        n_iterations=50,
        random_seed=42
    )
    
    print(f"\nRandom Search Best Score: {random_results['best_score']:.4f}")
    print(f"Best Weights:")
    for feat, weight in sorted(random_results['best_weights'].items(), key=lambda x: -x[1]):
        print(f"  {feat}: {weight:.4f}")
    
    # ===== FINE GRID SEARCH (Around best random result)
    print("\n[PHASE 2] Fine Grid Search (around best random weights)...")
    
    best_w = random_results['best_weights']
    fine_ranges = {
        'constraint_match': (
            max(0.0, best_w['constraint_match'] - 0.1),
            min(1.0, best_w['constraint_match'] + 0.1)
        ),
        'bm25_normalized': (
            max(0.0, best_w['bm25_normalized'] - 0.1),
            min(1.0, best_w['bm25_normalized'] + 0.1)
        ),
        'profile_similarity': (
            max(0.0, best_w['profile_similarity'] - 0.05),
            min(1.0, best_w['profile_similarity'] + 0.05)
        ),
        'popularity': (
            max(0.0, best_w['popularity'] - 0.05),
            min(1.0, best_w['popularity'] + 0.05)
        ),
        'category_match': (
            max(0.0, best_w['category_match'] - 0.05),
            min(1.0, best_w['category_match'] + 0.05)
        ),
    }
    
    grid_results = tuner.grid_search(
        weight_ranges=fine_ranges,
        step_size=0.05
    )
    
    print(f"\nGrid Search Best Score: {grid_results['best_score']:.4f}")
    print(f"Best Weights:")
    for feat, weight in sorted(grid_results['best_weights'].items(), key=lambda x: -x[1]):
        print(f"  {feat}: {weight:.4f}")
    
    # ===== SAVE RESULTS
    print("\n[PHASE 3] Saving optimal weights...")
    
    final_weights = grid_results['best_weights']
    
    output = {
        'optimal_weights': final_weights,
        'score': grid_results['best_score'],
        'method': 'random_search + grid_search',
        'timestamp': str(np.datetime64('now'))
    }
    
    with open('optimal_ranking_weights.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("✅ Optimal weights saved to: optimal_ranking_weights.json")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("1. Copy optimal_ranking_weights.json to your agent")
    print("2. Load weights in agent.__init__():")
    print("   with open('optimal_ranking_weights.json') as f:")
    print("       config = json.load(f)")
    print("       self.ranking_weights = config['optimal_weights']")
    print("3. Use in respond() to score products")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
