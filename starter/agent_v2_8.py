"""agent_v2_8 — 통합 단일 파일. agent_v2(통계 모델링) 계보를 v2_1~v2_7 개선분과 함께 평탄화.

한 줄: 시뮬레이터를 최소한으로 이용하는 원칙적 설계 + v1 에서 배운 두 레버(R7 / open question).
       LLM 미사용. public_set 200 실측 TS 0.855 / HitRate@10 1.000 / MTTC 2.79 / 토큰 0.
       (agent_v1 0.820, damin_start 0.724, 원본 agent_v2 0.682)

가설 검증 이력은 파일 하단 주석 참조. 상세 설계 결정은 `docs/decision_log.md`.

--- EN ---
Consolidated single file: the agent_v2 (statistical-modeling) lineage flattened together with the
v2_1–v2_7 improvements. Principled design that leans on the simulator minimally + the two levers
learned from agent_v1 (R7 exposure suppression / turn-1 open question). No LLM.
Measured on public_set 200: TS 0.855 / HitRate@10 1.000 / MTTC 2.79 / 0 tokens.
Hypothesis-test history is in the bottom comment; design rationale in docs/decision_log.md.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.IGNORECASE)
MONEY_RE = re.compile(r"(?:under|below|less than|max(?:imum)?|<=?)\s*\$?\s*(\d+(?:\.\d+)?)", re.I)
COLOR_RE = re.compile(
    r"\b(black|white|blue|red|pink|green|brown|gray|grey|purple|yellow|orange|navy|beige|tan|gold|silver)\b",
    re.I,
)
MATERIAL_RE = re.compile(
    r"\b(cotton|polyester|nylon|leather|wool|spandex|silk|rayon|linen|fleece|denim|suede|fabric)\b",
    re.I,
)

ALLOWED_ATTRIBUTES = (
    "category", "material", "color", "size", "style",
    "brand", "budget", "feature", "use_case", "other",
)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
    "im", "i'm", "still", "what", "matters", "need", "key", "requirement",
    "those", "options", "quite", "right", "yet", "about", "one", "specific",
    "attribute", "additional", "preference", "have", "dont", "don't",
}

# Internal ontology is richer than the evaluator's ask ontology.
ATTRIBUTE_PATTERNS: dict[str, tuple[str, ...]] = {
    "size": ("size", "sizing", "wide", "narrow", "width", "small", "medium", "large",
             "xl", "xxl", "petite", "plus size"),
    "style": ("style", "fit", "slim", "relaxed", "loose", "fitted", "sleeve",
              "neck", "neckline", "casual", "formal", "vintage", "classic"),
    "use_case": ("running", "hiking", "gym", "workout", "winter", "outdoor", "work",
                 "office", "wedding", "travel", "walking", "sports", "training"),
    "feature": ("waterproof", "breathable", "lightweight", "comfortable", "comfort",
                "cushion", "cushioned", "durable", "durability", "warm", "warmth",
                "stretch", "stretchy", "pocket", "closure", "heel", "insulated",
                "performance", "weather"),
    "brand": ("brand", "made by", "manufacturer"),
    "budget": ("budget", "price", "under", "below", "less than", "$"),
}

REPLACEMENT_MARKERS = (
    "actually", "instead", "ignore my earlier", "ignore the earlier",
    "rather", "change", "what i need is", "what i really need",
)
NO_PREFERENCE_MARKERS = (
    "don't have a preference", "do not have a preference", "no preference",
    "doesn't matter", "does not matter", "use your judgment", "any is fine",
)

# 시뮬레이터 신호 감지 (v2_1 override / v2_4 H5 소진).
_OVERRIDE_RE = re.compile(r"ignore my earlier|actually,?\s*(?:ignore|instead)", re.I)
_EXHAUST_RE = re.compile(r"preference for\s+([a-z_]+)", re.I)
_JUDGMENT_RE = re.compile(r"use your judgment|use your judgement", re.I)
# H5 소진 감지 + sticky mining 대상. brand/budget 은 수율 0 이라 sticky 는 안 걸리지만,
# "no additional preference for brand" 같은 소진 신호는 잡아야 재질문을 막는다 (v2_4).
_REAL_ATTRS = ("feature", "material", "color", "style", "size", "use_case", "brand", "budget")


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{k} {v}" for k, v in value.items())
    if isinstance(value, list):
        return " ".join(str(x) for x in value)
    return str(value)


def _terms(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)
            if len(t) > 1 and t.lower() not in STOPWORDS]


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(x for x in items if x))


def _fts_expression(terms: list[str]) -> str:
    safe = []
    for term in _dedupe(terms)[:48]:
        term = term.replace('"', '""')
        if term:
            safe.append(f'"{term}"')
    return " OR ".join(safe)


@dataclass
class Evidence:
    attribute: str
    value: str
    status: str = "ACTIVE"   # ACTIVE / NO_PREFERENCE / SUPERSEDED
    hard: bool = False


@dataclass
class SessionState:
    profile: dict[str, Any]
    messages: list[str] = field(default_factory=list)
    evidence: dict[str, list[Evidence]] = field(default_factory=dict)
    no_preference: set[str] = field(default_factory=set)
    asked_counts: Counter = field(default_factory=Counter)
    last_candidate_scores: dict[str, float] = field(default_factory=dict)
    category_terms: list[str] = field(default_factory=list)
    profile_importance: dict[str, float] = field(default_factory=dict)
    exposure: Counter = field(default_factory=Counter)   # R7: asin -> 추천 횟수
    asked_open: bool = False                             # open_first
    last_ask: str | None = None                          # H5 / sticky
    last_yielded: bool = False                           # sticky mining


class Agent:
    """누적 evidence 상태 + 멀티라우트 BM25 + risk-gated 스코어링 + open_first/sticky 질문 정책."""

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.sessions: dict[str, SessionState] = {}
        self.products: dict[str, dict[str, Any]] = {}
        self._build_index()

        # 해석 가능한 노브 — 시나리오 특정 로직 없음.
        self.candidate_limit = 400          # R7 억제분 여유
        self.route_limit = 200
        self.semantic_weight = 1.0
        self.explicit_match_weight = 1.35
        self.quality_weight = 0.025
        self.coverage_strength = 0.12
        self.exposure_decay = 0.0           # 0 = 하드 R7 제외, >0 = 곱셈 감쇠
        self.feat_mult = 1.5               # BM25 features 가중 배수 (⚠️ 튜닝값, holdout 재검증)

    # ---- 카탈로그 색인 -------------------------------------------------
    def _build_index(self) -> None:
        cur = self.connection.cursor()
        cur.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, title, categories, features, details, store, description, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        batch = []
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                product = json.loads(line)
                asin = str(product["parent_asin"])
                self.products[asin] = product
                batch.append((
                    asin,
                    _text(product.get("title")), _text(product.get("categories")),
                    _text(product.get("features")), _text(product.get("details")),
                    _text(product.get("store")), _text(product.get("description")),
                ))
                if len(batch) >= 1000:
                    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
        if batch:
            cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        self.connection.commit()

    def _search(self, terms: list[str], limit: int, weights: tuple[float, ...]) -> list[tuple[str, float]]:
        expr = _fts_expression(terms)
        if not expr:
            return []
        # BM25 features 가중 상향 (v2_7). 시뮬레이터가 제약을 features/details 에서 뽑기 때문.
        w = list(weights)
        w[3] *= self.feat_mult
        w[1] /= self.feat_mult ** 0.5
        weight_sql = ", ".join(str(float(x)) for x in w)
        rows = self.connection.execute(
            f"SELECT parent_asin, bm25(products, {weight_sql}) AS bm "
            "FROM products WHERE products MATCH ? ORDER BY bm LIMIT ?",
            (expr, limit),
        ).fetchall()
        # FTS5 bm25: 값이 작을수록 좋음 → 양의 relevance 로 변환.
        return [(str(r["parent_asin"]), max(0.0, -float(r["bm"]))) for r in rows]

    # ---- 세션 / 프로필 ----------------------------------------------
    def reset(self, session_id: str, user_profile: dict) -> None:
        state = SessionState(profile=dict(user_profile or {}))
        state.profile_importance = self._profile_importance(state.profile)
        self.sessions[session_id] = state

    def _profile_importance(self, profile: dict[str, Any]) -> dict[str, float]:
        # 공개 프로필은 '어느 차원이 중요한지'를 말하지 값은 안 준다 → 질문 우선순위에만 약하게.
        result: dict[str, float] = {}
        for tag in (str(x).strip().lower() for x in profile.get("preference_tags") or []):
            attr = self._map_internal_to_ask(tag)
            if attr:
                result[attr] = 1.0
        return result

    def _map_internal_to_ask(self, attribute: str) -> str | None:
        a = attribute.lower()
        if a in ALLOWED_ATTRIBUTES:
            return a
        if a in ("comfort", "durability", "performance", "warmth", "weather"):
            return "feature"
        if a == "fit":
            return "style"
        return None

    # ---- evidence 파싱 / 상태 갱신 -------------------------------------
    def _detect_attribute(self, text: str) -> str:
        lower = text.lower()
        if MATERIAL_RE.search(lower):
            return "material"
        if COLOR_RE.search(lower):
            return "color"
        if MONEY_RE.search(lower) or any(x in lower for x in ATTRIBUTE_PATTERNS["budget"]):
            return "budget"
        for attr in ("size", "style", "use_case", "feature", "brand"):
            if any(term in lower for term in ATTRIBUTE_PATTERNS[attr]):
                return attr
        return "other"

    def _extract_category_terms(self, text: str) -> list[str]:
        lower = text.lower()
        match = re.search(r"looking for\s+(.+?)(?:[,.]|but\b|a key requirement|$)", lower)
        terms = _terms(match.group(1) if match else text)
        vocab: set[str] = set()
        for values in ATTRIBUTE_PATTERNS.values():
            for value in values:
                vocab.update(_terms(value))
        vocab.update(MATERIAL_RE.pattern.lower().split("|"))
        return [t for t in terms if t not in vocab][:10]

    def _extract_evidence(self, message: str) -> list[Evidence]:
        lower = message.lower().strip()
        if any(m in lower for m in NO_PREFERENCE_MARKERS):
            attr = self._detect_attribute(lower)
            if attr != "other":
                return [Evidence(attr, "", status="NO_PREFERENCE")]

        replacement = any(m in lower for m in REPLACEMENT_MARKERS)
        found: list[Evidence] = []

        mat = MATERIAL_RE.search(message)
        if mat:
            found.append(Evidence("material", mat.group(1).lower(), hard=replacement))
        col = COLOR_RE.search(message)
        if col:
            found.append(Evidence("color", col.group(1).lower(), hard=replacement))
        mon = MONEY_RE.search(message)
        if mon:
            found.append(Evidence("budget", mon.group(1), hard=True))

        if "what matters is:" in lower:
            for raw in (x.strip() for x in message.split(":", 1)[-1].split(";") if x.strip()):
                found.append(Evidence(self._detect_attribute(raw), raw))
        elif "key requirement is:" in lower:
            raw = message.split(":", 1)[-1].strip()
            if raw:
                found.append(Evidence(self._detect_attribute(raw), raw, hard=True))
        elif replacement and "what i need is:" in lower:
            raw = re.split(r"what i need is:\s*", message, flags=re.I)[-1].strip(" .")
            if raw:
                found.append(Evidence(self._detect_attribute(raw), raw, hard=True))

        dedup: dict[tuple[str, str, str], Evidence] = {}
        for ev in found:
            dedup[(ev.attribute, ev.value.lower(), ev.status)] = ev
        return list(dedup.values())

    def _update_state(self, state: SessionState, message: str, turn: int) -> None:
        state.messages.append(message)
        if not state.category_terms:
            state.category_terms = self._extract_category_terms(message)

        lower = message.lower()
        is_override = bool(_OVERRIDE_RE.search(message))
        before_status = ({id(ev): ev.status for b in state.evidence.values() for ev in b}
                         if is_override else {})
        before_size = {a: len(b) for a, b in state.evidence.items()}

        for ev in self._extract_evidence(message):
            bucket = state.evidence.setdefault(ev.attribute, [])
            if ev.status == "NO_PREFERENCE":
                state.no_preference.add(ev.attribute)
                for old in bucket:
                    if old.status == "ACTIVE":
                        old.status = "SUPERSEDED"
                bucket.append(ev)
                continue
            state.no_preference.discard(ev.attribute)
            if any(m in lower for m in REPLACEMENT_MARKERS):
                for old in bucket:
                    if old.status == "ACTIVE":
                        old.status = "SUPERSEDED"
            if not any(o.status == ev.status and o.value.lower() == ev.value.lower() for o in bucket):
                bucket.append(ev)

        if is_override:
            # R7 리셋 (v2_1) + supersede 취소 (v2_2 / D2: old_value 는 타깃 파생이라 죽이면 손해).
            state.exposure.clear()
            for b in state.evidence.values():
                for ev in b:
                    if before_status.get(id(ev)) == "ACTIVE" and ev.status == "SUPERSEDED":
                        ev.status = "ACTIVE"

        # H5 소진 (v2_4): "no additional preference for X" / "use your judgment".
        m = _EXHAUST_RE.search(message)
        if m and m.group(1).lower() in _REAL_ATTRS:
            state.no_preference.add(m.group(1).lower())
        elif _JUDGMENT_RE.search(message) and state.last_ask in _REAL_ATTRS:
            state.no_preference.add(state.last_ask)

        # sticky mining (v2_5): 이번 턴 evidence 가 늘어난 속성 = productive.
        grew = [a for a, b in state.evidence.items() if len(b) > before_size.get(a, 0)]
        state.last_yielded = bool(grew)
        for a in grew:
            state.asked_counts[a] = 0

    # ---- belief features -------------------------------------------
    def _active_evidence(self, state: SessionState) -> list[Evidence]:
        return [ev for b in state.evidence.values() for ev in b if ev.status == "ACTIVE"]

    def _unknown_attributes(self, state: SessionState) -> list[str]:
        known = {a for a, b in state.evidence.items()
                 if any(ev.status == "ACTIVE" for ev in b)} | state.no_preference
        return [a for a in ALLOWED_ATTRIBUTES if a not in known and a not in ("category", "other")]

    def _active_terms(self, state: SessionState) -> list[str]:
        terms: list[str] = []
        for ev in self._active_evidence(state):
            terms.extend(_terms(ev.value))
        return _dedupe(terms)

    def _intent_uncertainty(self, state: SessionState) -> float:
        active = self._active_evidence(state)
        hard = sum(1 for ev in active if ev.hard)
        certainty = min(1.0, 0.16 * len(active) + 0.18 * hard + (0.18 if state.category_terms else 0.0))
        return 1.0 - certainty

    # ---- 멀티라우트 retrieval (2 route) + R7 --------------------------
    def _retrieve_candidates(self, state: SessionState) -> dict[str, float]:
        scores: dict[str, float] = {}

        def merge(rows: list[tuple[str, float]], route_weight: float) -> None:
            if not rows:
                return
            mx = max(s for _, s in rows) or 1.0
            for asin, s in rows:
                scores[asin] = max(scores.get(asin, 0.0), route_weight * s / mx)

        category_terms = state.category_terms
        active_terms = self._active_terms(state)
        intent_terms = _dedupe(category_terms + active_terms)

        # intent 라우트 (카테고리 + 지금까지 밝혀진 제약).
        merge(self._search(intent_terms, self.route_limit, (0.0, 6.0, 4.2, 2.8, 2.6, 1.2, 1.5)), 1.00)
        # 명시 제약 라우트 (후반 턴에 결정적 디테일이 나올 때).
        if active_terms:
            merge(self._search(_dedupe(category_terms + active_terms), self.route_limit,
                               (0.0, 5.5, 3.5, 4.0, 3.8, 1.0, 2.2)), 1.05)
        # (broad-category 라우트는 ablation Δ −0.0006 → 제거.)

        # 이전 강한 후보는 계속 후보 (이전 miss 는 거절 아님).
        for asin, prev in state.last_candidate_scores.items():
            if asin in self.products:
                scores[asin] = max(scores.get(asin, 0.0), prev * 0.78)

        ranked = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[: self.candidate_limit])

        # R7 — 이전 턴 노출분 억제. exposure_decay=0 → 하드 제외, >0 → 곱셈 감쇠.
        if not state.exposure:
            return ranked
        d = self.exposure_decay
        if d <= 0.0:
            return {a: s for a, s in ranked.items() if a not in state.exposure}
        return {a: (s * (d ** state.exposure[a]) if a in state.exposure else s)
                for a, s in ranked.items()}

    # ---- 상품 스코어링 ---------------------------------------------
    def _product_text(self, product: dict[str, Any]) -> str:
        return " ".join([
            _text(product.get("title")), _text(product.get("categories")),
            _text(product.get("features")), _text(product.get("details")),
            _text(product.get("description")), _text(product.get("store")),
        ]).lower()

    def _evidence_match(self, ev: Evidence, product: dict[str, Any], text: str) -> float:
        value = ev.value.lower().strip()
        if not value:
            return 0.0
        if ev.attribute == "budget":
            try:
                price = product.get("price")
                if price in (None, ""):
                    return 0.0
                return 1.0 if float(price) <= float(value) else 0.0
            except (TypeError, ValueError):
                return 0.0
        terms = _terms(value)
        if not terms:
            return 0.0
        hits = sum(1 for t in terms if re.search(rf"\b{re.escape(t)}\b", text))
        return hits / len(terms)

    def _quality_prior(self, product: dict[str, Any]) -> float:
        try:
            rating = float(product.get("average_rating") or 0.0) / 5.0
        except (TypeError, ValueError):
            rating = 0.0
        try:
            count = max(0.0, float(product.get("rating_number") or 0.0))
        except (TypeError, ValueError):
            count = 0.0
        popularity = min(1.0, math.log1p(count) / math.log1p(100000.0))
        return 0.65 * rating + 0.35 * popularity

    def _score_candidates(self, state: SessionState, candidates: dict[str, float]) -> list[tuple[str, float]]:
        active = self._active_evidence(state)
        scored: list[tuple[str, float]] = []
        for asin, retrieval_score in candidates.items():
            product = self.products[asin]
            text = self._product_text(product)
            explicit_match = 0.0
            for ev in active:
                weight = 1.35 if ev.hard else 0.85
                explicit_match += weight * self._evidence_match(ev, product, text)
            score = (
                self.semantic_weight * retrieval_score
                + self.explicit_match_weight * explicit_match
                + self.quality_weight * self._quality_prior(product)
            )
            scored.append((asin, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ---- risk-aware Top-K (coverage portfolio) ----------------------
    def _signature(self, product: dict[str, Any], unresolved: list[str]) -> tuple[str, ...]:
        text = self._product_text(product)
        sig: list[str] = []
        if "material" in unresolved:
            m = MATERIAL_RE.search(text)
            sig.append(f"m:{m.group(1).lower() if m else '?'}")
        if "color" in unresolved:
            c = COLOR_RE.search(text)
            sig.append(f"c:{c.group(1).lower() if c else '?'}")
        return tuple(sig)

    def _select_top_k(self, state: SessionState, scored: list[tuple[str, float]], top_k: int) -> list[str]:
        if not scored:
            return []
        uncertainty = self._intent_uncertainty(state)
        unresolved = self._unknown_attributes(state)
        if uncertainty < 0.28 or not unresolved:
            return [a for a, _ in scored[:top_k]]

        selected: list[str] = []
        sig_counts: Counter = Counter()
        remaining = scored[: min(len(scored), 80)]
        while remaining and len(selected) < top_k:
            best_idx, best_util = 0, -float("inf")
            for idx, (asin, base) in enumerate(remaining):
                sig = self._signature(self.products[asin], unresolved)
                novelty = (sum(1.0 / (1.0 + sig_counts[x]) for x in sig) / len(sig)) if sig else 0.0
                util = base + self.coverage_strength * uncertainty * novelty
                if util > best_util:
                    best_util, best_idx = util, idx
            asin, _ = remaining.pop(best_idx)
            selected.append(asin)
            for item in self._signature(self.products[asin], unresolved):
                sig_counts[item] += 1
        return selected

    # ---- 질문 정책 (open_first + sticky + info-gain) -----------------
    def _candidate_attribute_distribution(self, candidate_ids: list[str], attribute: str) -> Counter:
        dist: Counter = Counter()
        for asin in candidate_ids[:80]:
            product = self.products[asin]
            text = self._product_text(product)
            if attribute == "material":
                m = MATERIAL_RE.search(text)
                dist[m.group(1).lower() if m else "?"] += 1
            elif attribute == "color":
                c = COLOR_RE.search(text)
                dist[c.group(1).lower() if c else "?"] += 1
            elif attribute == "brand":
                store = str(product.get("store") or "").strip().lower()
                dist[store or "?"] += 1
            elif attribute == "budget":
                price = product.get("price")
                try:
                    p = float(price) if price not in (None, "") else None
                except (TypeError, ValueError):
                    p = None
                if p is None:
                    dist["?"] += 1
                else:
                    dist["<25" if p < 25 else "25-50" if p < 50 else "50-100" if p < 100 else "100+"] += 1
            else:
                vocab = ATTRIBUTE_PATTERNS.get(attribute, ())
                hits = tuple(term for term in vocab if term in text)[:3]
                dist[hits or ("?",)] += 1
        return dist

    def _normalized_entropy(self, dist: Counter) -> float:
        total = sum(dist.values())
        if total <= 1 or len(dist) <= 1:
            return 0.0
        entropy = -sum((c / total) * math.log(c / total + 1e-12) for c in dist.values())
        return entropy / math.log(len(dist))

    def _choose_question(self, state: SessionState, candidate_ids: list[str]) -> str | None:
        # open_first — 턴 1 열린질문.
        if not state.asked_open:
            state.asked_open = True
            return "other"
        # sticky mining — 직전에 물어 실제 제약이 나온 실제 속성은 소진 전까지 계속.
        if (state.last_yielded and state.last_ask in _REAL_ATTRS
                and state.last_ask not in state.no_preference):
            return state.last_ask
        if not candidate_ids:
            return None

        known = {a for a, b in state.evidence.items()
                 if any(ev.status == "ACTIVE" for ev in b)} | state.no_preference
        uncertainty = self._intent_uncertainty(state)
        best_attr, best_value = None, 0.0
        for attr in ALLOWED_ATTRIBUTES:
            if attr in ("category", "other") or attr in known:
                continue
            dist = self._candidate_attribute_distribution(candidate_ids, attr)
            entropy = self._normalized_entropy(dist)
            total = sum(dist.values()) or 1
            answerability = 1.0 - min(0.85, dist.get("?", 0) / total)
            history_importance = state.profile_importance.get(attr, 0.0)
            redundancy = min(0.85, 0.38 * state.asked_counts[attr])
            value = (0.52 * entropy + 0.20 * answerability + 0.18 * history_importance
                     + 0.10 * uncertainty - 0.30 * redundancy)
            if value > best_value:
                best_value, best_attr = value, attr
        if best_value < 0.18:
            return None
        return best_attr

    def _question_text(self, attribute: str) -> str:
        prompts = {
            "category": "What type of product are you looking for?",
            "material": "Do you have a material preference?",
            "color": "Do you have a color preference?",
            "size": "Is there a size or fit requirement I should prioritize?",
            "style": "What style or fit do you prefer?",
            "brand": "Do you have a brand preference?",
            "budget": "What budget range should I use?",
            "feature": "Which product feature matters most to you?",
            "use_case": "What will you mainly use it for?",
            "other": "Is there another requirement that would help narrow this down?",
        }
        return prompts.get(attribute, "What else matters most for this choice?")

    # ---- 엔트리포인트 ----------------------------------------------
    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        if session_id not in self.sessions:
            raise RuntimeError("reset must be called before respond")
        state = self.sessions[session_id]
        self._update_state(state, user_message, turn)

        candidates = self._retrieve_candidates(state)
        scored = self._score_candidates(state, candidates)
        candidate_ids = [a for a, _ in scored]
        recommendations = self._select_top_k(state, scored, top_k)

        state.last_candidate_scores = {a: max(0.0, s) for a, s in scored[: self.candidate_limit]}

        ask_attribute = self._choose_question(state, candidate_ids)
        if ask_attribute:
            state.asked_counts[ask_attribute] += 1
            message = self._question_text(ask_attribute)
        else:
            message = "These are my best matches based on what you've told me so far."

        for asin in recommendations:               # R7 노출 카운트
            state.exposure[asin] += 1
        state.last_ask = ask_attribute              # H5 / sticky

        return {
            "message": message,
            "ask_attribute": ask_attribute,
            "recommendations": [{"parent_asin": a} for a in recommendations],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }


# ===========================================================================
# agent_v2 대비 개선 이력 (가설 → 검증 → 판정). 상세: docs/decision_log.md
# Improvements vs agent_v2 (hypothesis → test → verdict). Detail: docs/decision_log.md
# ===========================================================================
#
#   버전   변경                                                         TS      비고
#   ----   --------------------------------------------------------     ------  ----------------------------
#   v2     (baseline) 멀티라우트 retrieval + typed evidence +           0.682   R7·open_first 없음이
#          risk-gated 스코어링 + coverage portfolio + info-gain 질문             치명적 (agent_v1 0.820)
#   v2.1   + R7 (이전 노출 상품 억제, exposure_decay 노브) + open_first  0.828   v2 는 추천 슬롯 57% 재노출
#          + candidate_limit 400. bm25 bound-param → SQL 리터럴 수정
#   v2.2   override 시 이전 evidence SUPERSEDE 취소 (누적 유지).         0.849   IO .87 → 1.00.
#          시뮬레이터 old_value 는 타깃 파생이라 죽이면 손해 (D2)
#   v2.3   (dead) info-gain × yield_prior — brand 쏠림 못 고침           0.847   폐기. D6 재확인
#   v2.4   H5 소진 감지 ("no additional preference for X" 등) →          0.848   반복 질문 정지
#          반복 질문 방지
#   v2.5   sticky mining — 수율 나는 속성을 소진 전까지 계속 캔다        0.854   breadth-first → depth-first.
#          (v1 퍼널의 depth-first 채굴 복원)                                     bnd .80 → .90
#   v2.6   (dead) split-quality 댐프너 — brand 쏠림을 budget 쏠림으로    0.843   폐기
#   v2.7   BM25 features 가중 ×1.5 (title ÷√1.5). 시뮬레이터가 제약을    0.857   HR .995 → 1.000.
#          features/details 에서 뽑기 때문 (구조적, public-fit 아님)             ⚠️ 배수는 holdout 재검증
#   v2.8   하울 성 무너뜨리기: ablation 으로 기여 0 성분 제거 —          0.855   −0.002 (노이즈).
#          _history_rank_boost (Δ 0), broad-category route (Δ −0.0006),          코드·과최적화 표면적 축소
#          verified_violation_penalty (Δ −0.0014), + 순수 dead 코드
#          (_sigmoid, *_history 필드, Evidence.confidence/source_turn,
#          NEGATIVE status 분기, NEGATION_MARKERS)
#
#   유지된 성분 (ablation 상 제거하면 손해): _quality_prior (−0.008),
#   coverage portfolio (−0.005 — DI 가설과 달리 도움), explicit route (−0.007),
#   carryover ×0.78 (−0.007), profile_importance (−0.006). −ALL = −0.022 (compound).
#
#   현재 지표 (public 200): TS 0.855 / HR 1.000 (200/200) / MRR 0.635 / MTTC 2.79 / 토큰 0.
#     시나리오별 MRR: buying .653 / browsing .624 / intent_override .568 / boundary .777.
#     rank 분포: rank1 52% / 2-3 15% / 4-5 14% / 6-10 19% / miss 0%.
#
#   ⚠️ public 200 에만 튜닝·검증됨. private 800 미확인. HR 1.000 이 private 에서 유지될
#      가능성은 낮다 (yield 분포·BM25 배수·sticky 임계 전부 public 실측 기반).
#
#   개선 후보:
#     1. MRR — rank 4+ 그룹(33%). semantic rerank / 리랭킹 정밀도.
#     2. 질문 순서 — info-gain 이 material 보다 brand/style 먼저 (HR 1.000 이라 이제 MTTC 만 깎음).
#        문헌 순서(use_case/style/feature/color/material > brand/budget) 약한 tint 는 미검증.
#     3. IO MRR 0.568 (평균 rank 3.27). MTTC 4.63 은 override_applied 게이트상 하한.
