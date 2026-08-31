"""gen_holdout_sets.py — D1 holdout_mirror + D2 holdout_natural_cards 생성.
gen_holdout_sets.py — build D1 holdout_mirror + D2 holdout_natural_cards.

배경 / rationale: docs/todo_h7.md.
- D1: public_set 분포를 재현하되 user/target disjoint. "특정 200개에 과최적화됐나" 체크. intent_card omit.
- D2: organizer 스타일 intent_card + 슬라이드 3 스타일 자연어 override 를 verbatim 동봉.
      "진짜 intent card / 패러프레이즈된 override 에서 무너지나" 체크.

실행 / run:  python3 -m tools.gen_holdout_sets
출력 / output:  data/holdout_mirror.jsonl (300), data/holdout_natural_cards.jsonl (200)
검증 / verify:  python3 -m evaluator.bench starter.agent_v1 --dataset data/holdout_mirror.jsonl
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from evaluator.local_evaluator import (
    intent_card, coarse_category, MATERIAL_RE, searchable_text, load_jsonl,
)

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog.jsonl"
PUBLIC = ROOT / "data" / "public_set.jsonl"
SEED = 20260830

# --- public_set 에서 고정한 분포 / distributions locked from public_set -----------------
RN_BUCKETS = [  # (label, lo, hi, weight) — public target rating_number 분포 근사.
    # public 은 10k+ 가 38% 지만 disjoint 카탈로그에 초대형(rn>=10k) 의류가 ~103개뿐 →
    # 10k+ 와 1k-10k 를 "1k+" 로 병합. 여전히 카탈로그 상위 ~3% (= candidate-target 풀).
    # public has 38% at 10k+, but only ~103 mega-popular clothing items remain disjoint →
    # merge 10k+ and 1k-10k into "1k+". Still the top ~3% of the catalog (= the candidate-target pool).
    ("1k+", 1000, 10**12, 0.745),
    ("100-1k", 100, 1000, 0.205),
    ("<100", 0, 100, 0.05),
]
RATING_STYLE_JOINT = [  # (rating_style, average_prior_rating, weight) — public 관측 joint
    ("usually positive", 5.0, 0.62),
    ("critical", 1.0, 0.07),
    ("critical", 2.0, 0.05),
    ("critical", 3.0, 0.11),
    ("mixed", 4.0, 0.10),
    ("usually positive", 4.0, 0.05),
]
N_TAGS_DIST = [(4, 0.60), (2, 0.22), (3, 0.14), (1, 0.04)]
PURCHASE_FREQ_DIST = [("3-4 prior purchases", 0.7), ("1-2 prior purchases", 0.15), ("5+ prior purchases", 0.15)]

# public tag vocab (9). 카테고리/소재 신호를 여기로 매핑 / map category+material signals to this vocab.
TAG_VOCAB = ["fit", "comfort", "durability", "material", "performance", "style", "warmth", "weather", "general shopping"]
CAT_TAG_HINTS = {
    "Shoes": ["fit", "comfort", "performance", "durability"],
    "Clothing": ["fit", "comfort", "style", "material"],
    "Jewelry": ["style", "material"],
    "Accessories": ["style", "durability", "material"],
    "Watches": ["style", "durability"],
}
WARM_WORDS = ("coat", "jacket", "sweater", "fleece", "parka", "hoodie", "thermal", "wool", "down", "puffer", "knit")

# --- D2 자연어 템플릿 / D2 natural-language templates ----------------------------------
# D2 의 목적은 (1) organizer 스타일 intent_card 를 verbatim 동봉, (2) 슬라이드 3 스타일 자연어
# override — agent 의 `_OVERRIDE_RE` 가 못 잡는 형태. 제약 문구는 정규식으로 못 만들어내므로
# `intent_card()` 원문을 정리만 해서 쓴다 (타깃 검색 가능성 유지). 패러프레이즈는 override 에 집중.
# D2 tests (1) a verbatim organizer-style intent_card and (2) a slide-3-style natural override that
# the agent's `_OVERRIDE_RE` misses. Constraint wording can't be regex-manufactured, so we just clean
# `intent_card()`'s raw phrases (keeps the target retrievable) and put the paraphrase on the override.
OVERRIDE_MSGS = [  # 슬라이드 3 스타일 — 템플릿 마커 없음 / slide-3 style, no template markers
    "Actually, make it {new}.",
    "On second thought, I'd rather have {new}.",
    "Wait — let's change that. I want {new} instead.",
    "Hmm, {new} would actually be better.",
    "Let me reconsider — {new} is really what I'm after.",
    "Changed my mind — go with {new}.",
    "Actually scratch that. I need {new}.",
]
OLD_VALUE_CLAUSES = [
    "I've mostly been looking at {s}.",
    "So far I've been leaning toward {s}.",
    "I had {s} in mind.",
    "I was thinking {s}.",
]


def weighted(rng: random.Random, pairs):
    items, weights = zip(*pairs)
    return rng.choices(items, weights=weights, k=1)[0]


def coarse_leaf(product: dict) -> str:
    cats = product.get("categories") or []
    for part in reversed(cats):
        p = str(part).strip()
        if p in ("Shoes", "Clothing", "Jewelry", "Accessories", "Watches"):
            return p
    return "Clothing"


def derive_tags(target: dict, priors: list[dict], rng: random.Random) -> list[str]:
    """가짜 prior purchase 들의 신호를 public tag vocab 으로 집계 / aggregate fake-history signals into the vocab."""
    pool: list[str] = []
    for prod in [target, *priors]:
        pool += CAT_TAG_HINTS.get(coarse_leaf(prod), ["fit", "comfort", "style"])
        corpus = searchable_text(prod).lower()
        if MATERIAL_RE.search(corpus):
            pool.append("material")
        if any(w in corpus for w in WARM_WORDS):
            pool += ["warmth", "weather"]
    n = weighted(rng, N_TAGS_DIST)
    # 빈도순으로 뽑되 약간의 무작위성 / frequency-ranked with light jitter
    ranked = sorted(set(pool), key=lambda t: (-pool.count(t), rng.random()))
    tags = ranked[:n]
    return tags or ["general shopping"]


def make_profile(target: dict, catalog: list[dict], by_leaf: dict[str, list[dict]], rng: random.Random) -> dict:
    leaf = coarse_leaf(target)
    same = by_leaf.get(leaf, catalog)
    k = rng.randint(3, 6)
    priors = rng.sample(same, min(k, len(same)))
    tags = derive_tags(target, priors, rng)
    style, avg = None, None
    style, avg = weighted(rng, [((s, a), w) for s, a, w in RATING_STYLE_JOINT])
    freq = weighted(rng, PURCHASE_FREQ_DIST)
    summary = f"Prior purchases emphasize {', '.join(tags[:3])}; ratings are {style}."
    return {
        "average_prior_rating": avg,
        "preference_tags": tags,
        "purchase_frequency": freq,
        "rating_style": style,
        "summary": summary,
    }


def _valid_card(p: dict) -> bool:
    card = intent_card(p)
    return len(set(map(str, card["hard_constraints"] + card["soft_preferences"]))) >= 2


def sample_targets(pool_by_bucket: dict, n: int, used: set, rng: random.Random) -> list[str]:
    out: list[str] = []
    for label, _lo, _hi, w in RN_BUCKETS:
        want = round(n * w)
        cands = [p for p in pool_by_bucket[label]
                 if p["parent_asin"] not in used and _valid_card(p)]
        rng.shuffle(cands)
        for p in cands[:want]:
            out.append(p["parent_asin"])
            used.add(p["parent_asin"])
    # 반올림/풀 부족 보정 — 남는 슬롯은 아무 버킷에서나 / fill rounding + pool shortfall from any bucket
    if len(out) < n:
        rest = [p for label, *_ in RN_BUCKETS for p in pool_by_bucket[label]
                if p["parent_asin"] not in used and _valid_card(p)]
        rng.shuffle(rest)
        for p in rest[: n - len(out)]:
            out.append(p["parent_asin"])
            used.add(p["parent_asin"])
    return out[:n]


import re as _re

_KEYPREFIX = _re.compile(r"^[A-Z][A-Za-z /]{1,24}:\s*")   # "Upper Material: ", "Lining: "
_NONASCII = _re.compile(r"[^\x00-\x7f]")


def clean_phrase(s: str, max_words: int = 8) -> str:
    """`intent_card()` 원문 조각을 카드에 넣을 만한 짧은 구로 정리 / tidy a raw fragment into a short phrase."""
    t = _NONASCII.sub("", str(s)).strip()
    t = _KEYPREFIX.sub("", t)
    t = _re.sub(r"\s+", " ", t).strip(" -–—;,.\t")
    words = t.split()
    if len(words) > max_words:
        t = " ".join(words[:max_words])
    return t.lower() if t[:1].isupper() and not t.split()[0].isupper() else t


def build_natural_card(target: dict, rng: random.Random) -> dict:
    raw = intent_card(target)
    hard = [p for p in (clean_phrase(c, max_words=6) for c in raw["hard_constraints"]) if p]
    soft = [p for p in (clean_phrase(c, max_words=5) for c in raw["soft_preferences"]) if p]
    if not hard:
        hard = [clean_phrase(raw["target_category"])]
    return {
        "target_category": raw["target_category"],
        "hard_constraints": hard[:2],
        "soft_preferences": soft[:2] or hard[:1],
    }


def build_override(card: dict, rng: random.Random) -> dict:
    new_np = clean_phrase(card["hard_constraints"][0], max_words=4)
    old_src = (card["soft_preferences"] or card["hard_constraints"])[-1]
    old_clause = rng.choice(OLD_VALUE_CLAUSES).format(s=clean_phrase(old_src, max_words=5))
    return {
        "turn": rng.choice([3, 4]),
        "old_value": old_clause,
        "new_value": new_np,
        "message": rng.choice(OVERRIDE_MSGS).format(new=new_np),
    }


def main() -> None:
    rng = random.Random(SEED)
    catalog = load_jsonl(CATALOG)
    by_asin = {p["parent_asin"]: p for p in catalog}
    public_targets = {s["ground_truth"]["parent_asin"] for s in load_jsonl(PUBLIC)}

    pool = [p for p in catalog if p["parent_asin"] not in public_targets and (p.get("features") or [])]
    pool_by_bucket = {label: [] for label, *_ in RN_BUCKETS}
    for p in pool:
        rn = p.get("rating_number") or 0
        for label, lo, hi, _w in RN_BUCKETS:
            if lo <= rn < hi:
                pool_by_bucket[label].append(p)
                break
    by_leaf: dict[str, list[dict]] = {}
    for p in catalog:
        by_leaf.setdefault(coarse_leaf(p), []).append(p)

    used: set = set()

    # ---- D1 holdout_mirror (300) ----
    d1_targets = sample_targets(pool_by_bucket, 300, used, rng)
    d1_scen = (["buying"] * 120 + ["browsing"] * 120 + ["intent_override"] * 45 + ["boundary"] * 15)
    rng.shuffle(d1_scen)
    d1_diff = (["easy", "medium", "hard"] * 100)
    rng.shuffle(d1_diff)
    d1_rows = []
    for i, asin in enumerate(d1_targets):
        d1_rows.append({
            "category_bucket": "clothing",
            "difficulty_bucket": d1_diff[i],
            "ground_truth": {"parent_asin": asin},
            "sample_id": f"holdout_mirror_{i + 1:04d}",
            "scenario_type": d1_scen[i],
            "user_profile": make_profile(by_asin[asin], catalog, by_leaf, rng),
        })
    (ROOT / "data" / "holdout_mirror.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in d1_rows) + "\n", encoding="utf-8")

    # ---- D2 holdout_natural_cards (200) ----
    d2_targets = sample_targets(pool_by_bucket, 200, used, rng)
    d2_scen = (["intent_override"] * 120 + ["buying"] * 50 + ["browsing"] * 30)
    rng.shuffle(d2_scen)
    d2_diff = (["easy", "medium", "hard"] * 67)
    rng.shuffle(d2_diff)
    d2_rows = []
    for i, asin in enumerate(d2_targets):
        scen = d2_scen[i]
        card = build_natural_card(by_asin[asin], rng)
        behavior = {"scenario_type": scen}
        if scen == "intent_override":
            behavior["override"] = build_override(card, rng)
        clean_card = {k: v for k, v in card.items() if not k.startswith("_")}
        d2_rows.append({
            "category_bucket": "clothing",
            "difficulty_bucket": d2_diff[i],
            "ground_truth": {"parent_asin": asin},
            "sample_id": f"holdout_natural_{i + 1:04d}",
            "scenario_type": scen,
            "user_profile": make_profile(by_asin[asin], catalog, by_leaf, rng),
            "intent_card": clean_card,
            "behavior": behavior,
        })
    (ROOT / "data" / "holdout_natural_cards.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in d2_rows) + "\n", encoding="utf-8")

    # ---- 요약 / summary ----
    import collections
    for name, rows in [("holdout_mirror", d1_rows), ("holdout_natural_cards", d2_rows)]:
        rb = collections.Counter()
        for r in rows:
            x = by_asin[r["ground_truth"]["parent_asin"]].get("rating_number") or 0
            rb["<100" if x < 100 else "100-1k" if x < 1000 else "1k-10k" if x < 10000 else "10k+"] += 1
        print(f"\n{name}: {len(rows)} rows")
        print("  scenario:", dict(collections.Counter(r["scenario_type"] for r in rows)))
        print("  rn bucket:", dict(rb))
        print("  disjoint from public:", all(r["ground_truth"]["parent_asin"] not in public_targets for r in rows))
    overlap = {r["ground_truth"]["parent_asin"] for r in d1_rows} & {r["ground_truth"]["parent_asin"] for r in d2_rows}
    print("\nD1 ∩ D2 target overlap:", len(overlap))


if __name__ == "__main__":
    main()
