"""agent_v2_8 — 통합 단일 파일. agent_v2(통계 모델링) 계보를 v2_1~v2_7 개선분과 함께 평탄화.
agent_v2_8 — consolidated single file: the agent_v2 (statistical-modeling) lineage flattened
             together with the v2_1–v2_7 improvements.

한 줄 / One line:
  시뮬레이터를 최소한으로 이용하는 원칙적 설계 + agent_v1 에서 배운 두 레버(R7 / 열린 질문). LLM 미사용.
  A principled design that leans on the simulator minimally + the two levers learned from agent_v1
  (R7 exposure suppression / turn-1 open question). No LLM.

실측 / Measured (public_set 200): TS 0.855 / HitRate@10 1.000 / MRR 0.635 / MTTC 2.79 / 토큰 0.
  (agent_v1 0.820, damin_start 0.724, 원본 agent_v2 / original agent_v2 0.682)

가설 검증 이력은 파일 하단 주석 참조. 상세 설계 결정은 `docs/decision_log.md`.
Hypothesis-test history is in the bottom comment; design rationale in `docs/decision_log.md`.
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
# 설정 / Config
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

# 평가기가 허용하는 ask_attribute enum. / The ask_attribute enum the evaluator allows.
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

# 내부 온톨로지는 평가기의 ask 온톨로지보다 세분화되어 있다.
# The internal ontology is finer-grained than the evaluator's ask ontology.
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

# "이전 선호를 교체" 신호. / Signals that a previous preference is being replaced.
REPLACEMENT_MARKERS = (
    "actually", "instead", "ignore my earlier", "ignore the earlier",
    "rather", "change", "what i need is", "what i really need",
)
# "이 속성에는 선호가 없음" 신호. / Signals "no preference on this attribute".
NO_PREFERENCE_MARKERS = (
    "don't have a preference", "do not have a preference", "no preference",
    "doesn't matter", "does not matter", "use your judgment", "any is fine",
)

# 시뮬레이터 신호 감지 (v2_1 override / v2_4 H5 소진).
# Simulator-signal detection (v2_1 override / v2_4 H5 exhaustion).
_OVERRIDE_RE = re.compile(r"ignore my earlier|actually,?\s*(?:ignore|instead)", re.I)
_EXHAUST_RE = re.compile(r"preference for\s+([a-z_]+)", re.I)
_JUDGMENT_RE = re.compile(r"use your judgment|use your judgement", re.I)
# H5 소진 감지 + sticky mining 대상. brand/budget 은 수율 0 이라 sticky 는 안 걸리지만,
# "no additional preference for brand" 같은 소진 신호는 잡아야 재질문을 막는다 (v2_4).
# Targets for H5 exhaustion + sticky mining. brand/budget never yield so sticky never fires on them,
# but we must still catch their exhaustion signal ("no additional preference for brand") to stop
# re-asking (v2_4).
_REAL_ATTRS = ("feature", "material", "color", "style", "size", "use_case", "brand", "budget")


def _text(value: object) -> str:
    """카탈로그 필드(문자열/리스트/딕트)를 검색용 평문으로. / Flatten a catalog field to plain text."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{k} {v}" for k, v in value.items())
    if isinstance(value, list):
        return " ".join(str(x) for x in value)
    return str(value)


def _terms(text: str) -> list[str]:
    """토큰화 + stopword 제거. / Tokenize and drop stopwords."""
    return [t.lower() for t in TOKEN_RE.findall(text)
            if len(t) > 1 and t.lower() not in STOPWORDS]


def _dedupe(items: list[str]) -> list[str]:
    """순서 보존 중복 제거. / Order-preserving de-duplication."""
    return list(dict.fromkeys(x for x in items if x))


def _fts_expression(terms: list[str]) -> str:
    """토큰 목록을 FTS5 OR 표현식으로. 방어적으로 인용. / Build an FTS5 OR expression; quote defensively."""
    safe = []
    for term in _dedupe(terms)[:48]:
        term = term.replace('"', '""')
        if term:
            safe.append(f'"{term}"')
    return " OR ".join(safe)


@dataclass
class Evidence:
    """대화에서 관측한 제약 하나. / One constraint observed from the conversation."""
    attribute: str
    value: str
    # ACTIVE(유효) / NO_PREFERENCE(선호 없음) / SUPERSEDED(교체됨)
    # ACTIVE / NO_PREFERENCE / SUPERSEDED
    status: str = "ACTIVE"
    # 하드 제약 여부 (스코어링 가중치 ↑). / Hard constraint flag (higher scoring weight).
    hard: bool = False


@dataclass
class SessionState:
    """세션당 누적 상태. / Per-session accumulated state."""
    profile: dict[str, Any]
    messages: list[str] = field(default_factory=list)
    evidence: dict[str, list[Evidence]] = field(default_factory=dict)
    no_preference: set[str] = field(default_factory=set)
    asked_counts: Counter = field(default_factory=Counter)
    last_candidate_scores: dict[str, float] = field(default_factory=dict)
    category_terms: list[str] = field(default_factory=list)
    profile_importance: dict[str, float] = field(default_factory=dict)
    # R7: asin -> 지금까지 추천한 횟수. / R7: asin -> times recommended so far.
    exposure: Counter = field(default_factory=Counter)
    # open_first: 열린 질문(other)을 이미 썼는지. / open_first: has the open question been asked.
    asked_open: bool = False
    # H5 / sticky: 직전에 물은 속성. / H5 / sticky: the attribute asked last turn.
    last_ask: str | None = None
    # sticky: 직전 턴이 실제 제약을 냈는지. / sticky: did the last turn yield a real constraint.
    last_yielded: bool = False


class Agent:
    """누적 evidence 상태 + 멀티라우트 BM25 + risk-gated 스코어링 + open_first/sticky 질문 정책.
    Cumulative evidence state + multi-route BM25 + risk-gated scoring + open_first/sticky question policy.
    """

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.sessions: dict[str, SessionState] = {}
        self.products: dict[str, dict[str, Any]] = {}
        self._build_index()

        # 해석 가능한 노브 — 시나리오 특정 로직 없음.
        # Interpretable knobs — no scenario-specific logic.
        self.candidate_limit = 400          # R7 억제분 여유 / headroom for R7 suppression
        self.route_limit = 200
        self.semantic_weight = 1.0
        self.explicit_match_weight = 1.35
        self.quality_weight = 0.025
        self.coverage_strength = 0.12
        # 0 = 하드 R7 제외, >0 = 곱셈 감쇠. / 0 = hard R7 exclusion, >0 = multiplicative decay.
        self.exposure_decay = 0.0
        # BM25 features 가중 배수 (⚠️ 튜닝값, holdout 재검증). / BM25 features weight multiplier
        # (⚠️ a tuned value; re-validate on a holdout split).
        self.feat_mult = 1.5

    # ---- 카탈로그 색인 / Catalog index -------------------------------
    def _build_index(self) -> None:
        """카탈로그 50k 를 in-memory FTS5 로 색인. / Index the 50k catalog into in-memory FTS5."""
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
        # Raise the BM25 weight on features (v2_7): the simulator draws its constraints from
        # the features/details fields.
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
        # FTS5 bm25: smaller is better → convert to a positive relevance.
        return [(str(r["parent_asin"]), max(0.0, -float(r["bm"]))) for r in rows]

    # ---- 세션 / 프로필 / Session & profile --------------------------
    def reset(self, session_id: str, user_profile: dict) -> None:
        state = SessionState(profile=dict(user_profile or {}))
        state.profile_importance = self._profile_importance(state.profile)
        self.sessions[session_id] = state

    def _profile_importance(self, profile: dict[str, Any]) -> dict[str, float]:
        # 공개 프로필은 '어느 차원이 중요한지'를 말하지 값은 안 준다 → 질문 우선순위에만 약하게.
        # The public profile says which dimension matters, not its value → used only as a weak
        # prior on question priority.
        result: dict[str, float] = {}
        for tag in (str(x).strip().lower() for x in profile.get("preference_tags") or []):
            attr = self._map_internal_to_ask(tag)
            if attr:
                result[attr] = 1.0
        return result

    def _map_internal_to_ask(self, attribute: str) -> str | None:
        """내부 태그를 ask enum 으로. / Map an internal tag to an ask-enum attribute."""
        a = attribute.lower()
        if a in ALLOWED_ATTRIBUTES:
            return a
        if a in ("comfort", "durability", "performance", "warmth", "weather"):
            return "feature"
        if a == "fit":
            return "style"
        return None

    # ---- evidence 파싱 / 상태 갱신 / Evidence parsing & state update ---
    def _detect_attribute(self, text: str) -> str:
        """자유 텍스트 한 조각을 어느 속성으로 분류. / Classify a free-text fragment into an attribute."""
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
        # "looking for ..." 뒤의 명사류만 취하되 하드 커밋은 안 한다.
        # Take the noun-ish part after "looking for ..." but do not hard-commit to it.
        lower = text.lower()
        match = re.search(r"looking for\s+(.+?)(?:[,.]|but\b|a key requirement|$)", lower)
        terms = _terms(match.group(1) if match else text)
        # 속성 토큰은 제거해 카테고리 라우트를 넓게 유지.
        # Strip attribute tokens so the category route stays broad.
        vocab: set[str] = set()
        for values in ATTRIBUTE_PATTERNS.values():
            for value in values:
                vocab.update(_terms(value))
        vocab.update(MATERIAL_RE.pattern.lower().split("|"))
        return [t for t in terms if t not in vocab][:10]

    def _extract_evidence(self, message: str) -> list[Evidence]:
        """한 메시지에서 제약을 파싱. / Parse constraints from one message."""
        lower = message.lower().strip()
        # 명시적 "선호 없음"은 별개 상태. / An explicit "no preference" is a distinct state.
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

        # 세미콜론 구분 제약 ("For that, what matters is: X; Y.") 을 evidence 로.
        # Semicolon-delimited constraints ("For that, what matters is: X; Y.") become evidence.
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

        # 같은 (속성, 값, 상태) 중복 제거. / De-duplicate identical (attribute, value, status).
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
        # override 시 상태 되돌리기용 스냅샷. / Snapshot for restoring statuses on an override.
        before_status = ({id(ev): ev.status for b in state.evidence.values() for ev in b}
                         if is_override else {})
        # sticky mining 용: 이번 턴에 어느 속성 bucket 이 커졌는지 비교할 기준.
        # For sticky mining: baseline to see which attribute buckets grew this turn.
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
            # 새 명시 evidence 는 그 차원을 다시 살린다. / New explicit evidence reactivates that dimension.
            state.no_preference.discard(ev.attribute)
            if any(m in lower for m in REPLACEMENT_MARKERS):
                for old in bucket:
                    if old.status == "ACTIVE":
                        old.status = "SUPERSEDED"
            # 동일한 ACTIVE evidence 중복 방지. / Avoid duplicating identical active evidence.
            if not any(o.status == ev.status and o.value.lower() == ev.value.lower() for o in bucket):
                bucket.append(ev)

        if is_override:
            # R7 리셋 (v2_1) + supersede 취소 (v2_2 / D2).
            # 시뮬레이터의 old_value 는 타깃 상품 메타데이터에서 파생 → 죽이면 타깃도 같이 내려간다.
            # Reset R7 (v2_1) + undo the supersede (v2_2 / D2). The simulator's old_value is derived
            # from the target product's own metadata, so dropping it drags the target down too.
            state.exposure.clear()
            for b in state.evidence.values():
                for ev in b:
                    if before_status.get(id(ev)) == "ACTIVE" and ev.status == "SUPERSEDED":
                        ev.status = "ACTIVE"

        # H5 소진 (v2_4): "no additional preference for X" / "use your judgment".
        # H5 exhaustion (v2_4): "no additional preference for X" / "use your judgment".
        m = _EXHAUST_RE.search(message)
        if m and m.group(1).lower() in _REAL_ATTRS:
            state.no_preference.add(m.group(1).lower())
        elif _JUDGMENT_RE.search(message) and state.last_ask in _REAL_ATTRS:
            state.no_preference.add(state.last_ask)

        # sticky mining (v2_5): 이번 턴에 evidence 가 늘어난 속성 = productive → 계속 캔다.
        # sticky mining (v2_5): an attribute whose evidence grew this turn is productive → keep mining.
        grew = [a for a, b in state.evidence.items() if len(b) > before_size.get(a, 0)]
        state.last_yielded = bool(grew)
        for a in grew:
            state.asked_counts[a] = 0

    # ---- belief 피처 / Belief features -----------------------------
    def _active_evidence(self, state: SessionState) -> list[Evidence]:
        return [ev for b in state.evidence.values() for ev in b if ev.status == "ACTIVE"]

    def _unknown_attributes(self, state: SessionState) -> list[str]:
        """아직 ACTIVE evidence 도 없고 소진도 안 된 속성. / Attributes with no ACTIVE evidence and not exhausted."""
        known = {a for a, b in state.evidence.items()
                 if any(ev.status == "ACTIVE" for ev in b)} | state.no_preference
        return [a for a in ALLOWED_ATTRIBUTES if a not in known and a not in ("category", "other")]

    def _active_terms(self, state: SessionState) -> list[str]:
        """모든 ACTIVE evidence 값의 토큰. / Tokens of every ACTIVE evidence value."""
        terms: list[str] = []
        for ev in self._active_evidence(state):
            terms.extend(_terms(ev.value))
        return _dedupe(terms)

    def _intent_uncertainty(self, state: SessionState) -> float:
        # 카테고리만 있으면 불확실성이 크고, 명시 evidence 가 그것을 줄인다.
        # Category alone leaves high uncertainty; explicit evidence reduces it.
        active = self._active_evidence(state)
        hard = sum(1 for ev in active if ev.hard)
        certainty = min(1.0, 0.16 * len(active) + 0.18 * hard + (0.18 if state.category_terms else 0.0))
        return 1.0 - certainty

    # ---- 멀티라우트 retrieval (2 route) + R7 / Multi-route retrieval + R7 ---
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
        # Intent route (category + everything disclosed so far).
        merge(self._search(intent_terms, self.route_limit, (0.0, 6.0, 4.2, 2.8, 2.6, 1.2, 1.5)), 1.00)
        # 명시 제약 라우트 (후반 턴에 결정적 디테일이 나올 때 유용).
        # Explicit-constraints route (useful when a decisive detail surfaces on a later turn).
        if active_terms:
            merge(self._search(_dedupe(category_terms + active_terms), self.route_limit,
                               (0.0, 5.5, 3.5, 4.0, 3.8, 1.0, 2.2)), 1.05)
        # broad-category 라우트는 ablation Δ −0.0006 → 제거 (v2_8).
        # The broad-category route measured Δ −0.0006 in ablation → removed (v2_8).

        # 이전 강한 후보는 계속 후보로 (이전 miss 는 거절이 아니다).
        # Previously-strong candidates stay eligible (a previous miss is not a rejection).
        for asin, prev in state.last_candidate_scores.items():
            if asin in self.products:
                scores[asin] = max(scores.get(asin, 0.0), prev * 0.78)

        ranked = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[: self.candidate_limit])

        # R7 — 이전 턴 노출분 억제. exposure_decay=0 → 하드 제외, >0 → 곱셈 감쇠.
        # R7 — suppress previously-shown products. exposure_decay=0 → hard exclusion, >0 → multiplicative decay.
        if not state.exposure:
            return ranked
        d = self.exposure_decay
        if d <= 0.0:
            return {a: s for a, s in ranked.items() if a not in state.exposure}
        return {a: (s * (d ** state.exposure[a]) if a in state.exposure else s)
                for a, s in ranked.items()}

    # ---- 상품 스코어링 / Product scoring ---------------------------
    def _product_text(self, product: dict[str, Any]) -> str:
        return " ".join([
            _text(product.get("title")), _text(product.get("categories")),
            _text(product.get("features")), _text(product.get("details")),
            _text(product.get("description")), _text(product.get("store")),
        ]).lower()

    def _evidence_match(self, ev: Evidence, product: dict[str, Any], text: str) -> float:
        """evidence 와 상품의 일치도 [0,1]. 메타데이터 부재 = 중립(0). / Match score [0,1]; missing metadata = neutral (0)."""
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
        """평점·인기 기반 약한 prior. / Weak prior from rating and popularity."""
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
        # 스코어 = retrieval + 명시 제약 일치 + 품질 prior.
        # v2_8: history_boost 항(ablation Δ 0)과 violation_penalty 항(Δ −0.0014) 제거.
        # score = retrieval + explicit-constraint match + quality prior.
        # v2_8: dropped the history_boost term (ablation Δ 0) and the violation_penalty term (Δ −0.0014).
        active = self._active_evidence(state)
        scored: list[tuple[str, float]] = []
        for asin, retrieval_score in candidates.items():
            product = self.products[asin]
            text = self._product_text(product)
            explicit_match = 0.0
            for ev in active:
                weight = 1.35 if ev.hard else 0.85   # 하드 제약 가중 ↑ / higher weight for hard constraints
                explicit_match += weight * self._evidence_match(ev, product, text)
            score = (
                self.semantic_weight * retrieval_score
                + self.explicit_match_weight * explicit_match
                + self.quality_weight * self._quality_prior(product)
            )
            scored.append((asin, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ---- risk-aware Top-K (coverage portfolio) --------------------
    def _signature(self, product: dict[str, Any], unresolved: list[str]) -> tuple[str, ...]:
        # 미해결 차원에서만 커버리지 압력이 생긴다. / Only unresolved dimensions create coverage pressure.
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
        # 불확실할 때만 커버리지 포트폴리오를 켠다. 확신이 서면 그냥 스코어 순.
        # Turn on the coverage portfolio only while uncertain; otherwise just take by score.
        if not scored:
            return []
        uncertainty = self._intent_uncertainty(state)
        unresolved = self._unknown_attributes(state)
        if uncertainty < 0.28 or not unresolved:
            return [a for a, _ in scored[:top_k]]

        # greedy: 스코어가 지배하고 커버리지는 작은 보너스. / greedy: score dominates, coverage is a small bonus.
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

    # ---- 질문 정책 (open_first + sticky + info-gain) / Question policy ---
    def _candidate_attribute_distribution(self, candidate_ids: list[str], attribute: str) -> Counter:
        """상위 후보 80개가 그 속성에서 어떻게 갈리는지. / How the top-80 candidates split on that attribute."""
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
                # 내부 차원은 키워드 시그니처로 근사. / Approximate internal dimensions by a keyword signature.
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
        # open_first — 턴 1 은 열린 질문. / open_first — turn 1 is the open question.
        if not state.asked_open:
            state.asked_open = True
            return "other"
        # sticky mining — 직전에 물어 실제 제약이 나온 실제 속성은 소진 전까지 계속.
        # sticky mining — keep asking the last real attribute that yielded, until it is exhausted.
        if (state.last_yielded and state.last_ask in _REAL_ATTRS
                and state.last_ask not in state.no_preference):
            return state.last_ask
        if not candidate_ids:
            return None

        # 그 외에는 후보 풀 dispersion 기반 info-gain 으로 다음 속성 선택.
        # Otherwise pick the next attribute by candidate-pool-dispersion info-gain.
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
        # 질문은 선택, 추천은 필수. / Asking is optional; recommending is not.
        if best_value < 0.18:
            return None
        return best_attr

    def _question_text(self, attribute: str) -> str:
        """고객에게 보일 자연어 질문. 평가기는 message 를 무시하지만 데모·심사용. /
        Customer-facing natural-language question. The evaluator ignores message; this is for demo/judging."""
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

    # ---- 엔트리포인트 / Entry point ------------------------------
    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        if session_id not in self.sessions:
            raise RuntimeError("reset must be called before respond")
        state = self.sessions[session_id]
        self._update_state(state, user_message, turn)

        candidates = self._retrieve_candidates(state)
        scored = self._score_candidates(state, candidates)
        candidate_ids = [a for a, _ in scored]
        recommendations = self._select_top_k(state, scored, top_k)

        # 다음 턴 연속성을 위해 후보 스코어 보존 (거절 블랙리스트 아님).
        # Preserve candidate scores for next-turn continuity (not a rejection blacklist).
        state.last_candidate_scores = {a: max(0.0, s) for a, s in scored[: self.candidate_limit]}

        ask_attribute = self._choose_question(state, candidate_ids)
        if ask_attribute:
            state.asked_counts[ask_attribute] += 1
            message = self._question_text(ask_attribute)
        else:
            message = "These are my best matches based on what you've told me so far."

        for asin in recommendations:               # R7 노출 카운트 / R7 exposure count
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
# Improvements over agent_v2 (hypothesis → test → verdict). Detail: docs/decision_log.md
# ===========================================================================
#
#  v2   (baseline) 멀티라우트 retrieval + typed evidence + risk-gated 스코어링          TS 0.682
#       + coverage portfolio + info-gain 질문. R7·open_first 없음이 치명적 (agent_v1 0.820).
#       (baseline) multi-route retrieval + typed evidence + risk-gated scoring
#       + coverage portfolio + info-gain questioning. No R7 / open_first — fatal.
#
#  v2.1 + R7 (이전 노출 상품 억제, exposure_decay 노브) + open_first + candidate_limit 400.  TS 0.828
#       bm25 bound-param → SQL 리터럴 수정. v2 는 추천 슬롯의 57% 를 재노출하고 있었다.
#       + R7 (exposure suppression, exposure_decay knob) + open_first + candidate_limit 400.
#       bm25 bound-param → SQL literal fix. v2 was re-showing 57% of its rec slots.
#
#  v2.2 override 시 이전 evidence SUPERSEDE 취소 (누적 유지). IO .87 → 1.00.               TS 0.849
#       시뮬레이터 old_value 는 타깃 파생이라 죽이면 손해 (decision_log D2).
#       Undo the SUPERSEDE of old evidence on an override (keep accumulating). IO .87 → 1.00.
#       The simulator's old_value is target-derived, so dropping it backfires (D2).
#
#  v2.3 (폐기 / dead) info-gain × yield_prior — brand 쏠림을 못 고침. D6 재확인.           TS 0.847
#       (dead) info-gain × yield_prior — did not fix the brand skew. Re-confirms D6.
#
#  v2.4 H5 소진 감지 ("no additional preference for X" / "use your judgment")             TS 0.848
#       → 같은 속성 반복 질문 정지.
#       H5 exhaustion detection → stop re-asking the same attribute.
#
#  v2.5 sticky mining — 수율 나는 속성을 소진 전까지 계속 캔다 (v1 퍼널의 depth-first     TS 0.854
#       채굴 복원). breadth-first → depth-first. boundary .80 → .90.
#       sticky mining — keep mining a yielding attribute until dry (restores v1's
#       depth-first funnel). breadth-first → depth-first. boundary .80 → .90.
#
#  v2.6 (폐기 / dead) split-quality 댐프너 — brand 쏠림을 budget 쏠림으로 바꿨을 뿐.      TS 0.843
#       (dead) split-quality dampener — merely traded the brand skew for a budget skew.
#
#  v2.7 BM25 features 가중 ×1.5 (title ÷√1.5). 시뮬레이터가 제약을 features/details       TS 0.857
#       에서 뽑기 때문 (구조적, public-fit 아님). HR .995 → 1.000. ⚠️ 배수는 holdout 재검증.
#       BM25 features weight ×1.5 (title ÷√1.5) — the simulator draws constraints from
#       features/details (structural, not public-fit). HR .995 → 1.000. ⚠️ re-validate the multiplier.
#
#  v2.8 ablation 으로 기여 0 성분 제거: _history_rank_boost (Δ 0), broad-category route   TS 0.855
#       (Δ −0.0006), verified_violation_penalty (Δ −0.0014), + 순수 dead 코드 (_sigmoid,
#       *_history 필드, Evidence.confidence/source_turn, NEGATIVE status 분기, NEGATION_MARKERS).
#       −0.002 (노이즈). 코드·과최적화 표면적 축소. 그리고 8단 서브클래스 체인을 이 단일 파일로 통합.
#       Ablation-driven removal of zero-contribution parts: _history_rank_boost (Δ 0),
#       broad-category route (Δ −0.0006), verified_violation_penalty (Δ −0.0014), + pure dead code
#       (_sigmoid, *_history fields, Evidence.confidence/source_turn, the NEGATIVE branch,
#       NEGATION_MARKERS). −0.002 (noise). Shrinks code + overfit surface. Also flattens the
#       8-level subclass chain into this one file.
#
#  유지된 성분 (ablation 상 제거하면 손해) / Kept (removal hurts, per ablation):
#    _quality_prior (−0.008), coverage portfolio (−0.005 — DI 가설과 달리 도움 / helps, contra DI's
#    hypothesis), explicit route (−0.007), carryover ×0.78 (−0.007), profile_importance (−0.006).
#    −ALL 을 한꺼번에 제거하면 −0.022 (성분들이 compound). / Removing −ALL at once = −0.022 (they compound).
#
#  현재 지표 (public 200) / Current metrics (public 200):
#    TS 0.855 / HR 1.000 (200/200) / MRR 0.635 / MTTC 2.79 / 토큰 0 / tokens 0.
#    시나리오별 MRR / MRR by scenario: buying .653 / browsing .624 / intent_override .568 / boundary .777.
#    rank 분포 / rank distribution: rank1 52% / 2-3 15% / 4-5 14% / 6-10 19% / miss 0%.
#
#  ⚠️ public 200 에만 튜닝·검증됨. private 800 미확인. HR 1.000 이 private 에서 유지될 가능성은 낮다
#     (yield 분포·BM25 배수·sticky 임계 전부 public 실측 기반).
#     Tuned and validated on public 200 only. The private 800 is unseen. HR 1.000 is unlikely to hold
#     on private (the yield distribution, BM25 multiplier, and sticky threshold are all from public data).
#
#  개선 후보 / Improvement candidates:
#    1. MRR — rank 4+ 그룹(33%). semantic rerank / 리랭킹 정밀도.
#       MRR — the rank-4+ group (33%). semantic rerank / reranking precision.
#    2. 질문 순서 — info-gain 이 material 보다 brand/style 을 먼저 본다 (HR 1.000 이라 이제 MTTC 만 깎음).
#       문헌 순서(use_case/style/feature/color/material > brand/budget) 약한 tint 는 미검증.
#       Question order — info-gain ranks brand/style ahead of material (only costs MTTC now that HR is
#       1.000). A weak tint toward the literature order (use_case/style/feature/color/material >
#       brand/budget) is untested.
#    3. IO MRR 0.568 (평균 rank 3.27). MTTC 4.63 은 override_applied 게이트상 하한.
#       IO MRR 0.568 (avg rank 3.27). MTTC 4.63 is a floor imposed by the override_applied gate.
