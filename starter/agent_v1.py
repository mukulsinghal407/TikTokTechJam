"""agent_v1 — R2/R5/R7 상태관리 구조 도입 (이터레이션 1).
agent_v1 — introduces R2/R5/R7 state-management structure (iteration 1).

출발점 / Starting point: 공식 `starter/agent.py` (stateless BM25, 마지막 메시지만 검색) /
    the official `starter/agent.py` (stateless BM25, searches on the last message only).
참고 / Reference: `playground/agents/damin_start.py` (누적 검색·profile 재랭킹의 검증된 구현) /
    `playground/agents/damin_start.py` (validated cumulative-search + profile-rerank implementation).

이 버전이 새로 하는 것 (PRD `docs/prd_draft.md` 기준) / What this version adds (per PRD `docs/prd_draft.md`):
  R1  대화 전체 누적 검색 / cumulative search over the whole conversation      — from damin_start (validated)
  R3  profile term 0.2x 재랭킹 / weak 0.2x profile-term rerank                — from damin_start (validated)
  R4  누적 상태로 카탈로그 쿼리 구성 / build the catalog query from that state — follows from R1
  R2  intent override 감지 → seen-set 리셋 + 계속 누적 ("우선"은 emergent).            [신규 / new]
      intent-override detection → reset seen-set + keep accumulating ("priority" is emergent).
      음의 가중치 감점은 실측상 역효과라 기본 off (decision_log D2).
      negative-weight demotion measured as counterproductive here, so off by default (decision_log D2).
  R5  질문 정책 — open_first: 턴1 열린질문(other) → 턴2+ 수율순 퍼널 (D4, 정성 트랙 PRD).     [부분 / partial]
      question policy — open_first: turn 1 open question (other) → turn 2+ yield-ordered funnel.
      적응형 info-gain(greedy·dispersion 둘 다)은 아직 퍼널을 못 이김 → 백로그 (D6).
      adaptive info-gain (both greedy and dispersion) does not yet beat the funnel → backlog (D6).
  R7  이전 턴에 노출한 상품은 재노출 안 함 — 전량 제외 + override 경계 리셋 (D5).           [신규 / new]
      never re-show a product shown on a previous turn — full exclusion + reset at the override boundary.
  H5  NO_NEW_INFO 3패턴 분리 처리 / handle the 3 NO_NEW_INFO patterns separately             [신규 / new]

이번 이터레이션에서 하지 않는 것 / Out of scope for this iteration:
  - BM25 필드 가중치 튜닝 (H1a) — 현재값 유지, 다음 이터레이션.
    BM25 field-weight tuning (H1a) — kept as-is, next iteration.
  - dense/hybrid 재랭킹 (H1b), constraint slot 구조화 (H6), 적응형 순서 재설계 — 이후.
    dense/hybrid rerank (H1b), constraint-slot state (H6), adaptive-order redesign — later.

실측 / Measured (public_set 200): TS 0.820 / HR 0.970 / MRR 0.578 / MTTC 2.90
  (baseline 0.107, damin_start 0.724)

LLM 미사용 → usage 토큰 0 / No LLM → usage tokens 0.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

LABEL = "agent-v1"

TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
}
# 시뮬레이터 응답 템플릿의 상투어 — 쿼리 신호가 아니므로 제외한다.
# Boilerplate from the simulator's reply templates — not query signal, so drop it.
REPLY_NOISE = {
    "additional", "preference", "options", "quite", "right", "yet", "judgment",
    "judgement", "specific", "attribute", "ask", "matters", "actually", "need",
    "earlier", "ignore", "key", "requirement", "exploring", "still",
}

# intent override 감지 (R2). 시뮬레이터 override 메시지는 항상
#   "Actually, ignore my earlier preference. What I need is: {new_value}." 형태.
# 다른 어떤 시뮬레이터 템플릿에도 "ignore ... preference" 는 없다 → 오탐 위험 낮음.
# Intent-override detection (R2). The simulator's override message is always
#   "Actually, ignore my earlier preference. What I need is: {new_value}."
# No other simulator template contains "ignore ... preference" → low false-positive risk.
OVERRIDE_RE = re.compile(r"ignore my earlier preference|actually,?\s*(?:ignore|forget)", re.I)
NEW_INTENT_RE = re.compile(r"what i need is:\s*(.+)", re.I)
CONSTRAINT_RE = re.compile(r"what matters is:\s*(.+)", re.I)

# H5 — NO_NEW_INFO 3패턴 분리 / split the 3 NO_NEW_INFO patterns:
#   ADDITIONAL: "그 속성엔 더 줄 게 없음" → 그 속성만 소진, 진행 /
#               "nothing more for that attribute" → exhaust that attribute only, move on
#   NOT_RIGHT : ask_attribute=None 을 보냈을 때만 나옴 → "질문을 안 했다" 신호, 소진 아님 /
#               only appears when we sent ask_attribute=None → "we asked nothing" signal, not exhaustion
#   BOUNDARY  : 그 속성에 선호 없음 → 그 속성 소진 (1회성) /
#               no preference on that attribute → exhaust it (one-off)
ADDITIONAL_RE = re.compile(r"don't have an additional preference", re.I)
NOT_RIGHT_RE = re.compile(r"not quite right yet", re.I)
BOUNDARY_RE = re.compile(r"your judgment|your judgement|don't have a preference", re.I)

# 질문 정책 = open_first (decision_log D4, 정성 트랙 PRD §4.6).
#   턴 1: "other" 한 번 (열린 질문). 시뮬레이터에서 other 는 classify 게이트를 우회해
#         미공개 제약을 클래스 무관 2개 주지만, 매 턴 반복하면 "other 스팸" = 실서비스 편법.
#   턴 2+: FUNNEL 을 F5 실측 수율순으로. (info-gain 3축 모델은 R5 백로그.)
# Question policy = open_first (decision_log D4, PRD §4.6).
#   Turn 1: one "other" (open question). In the simulator, "other" bypasses the classify
#           gate and returns 2 undisclosed constraints of any class; asking it every turn is
#           "other spam" = a shortcut that fails in a real service.
#   Turn 2+: FUNNEL in F5-measured yield order. (The 3-axis info-gain model is R5 backlog.)
# brand/budget/category 는 시뮬레이터가 제약으로 공개하지 않으므로(F1) 목록에 없음.
# brand/budget/category are absent because the simulator never discloses constraints of those classes (F1).
OPEN_QUESTION = "other"
FUNNEL = ("feature", "material", "color", "style", "size", "use_case")
ATTRIBUTE_PROMPTS = {
    "feature": "Is there a specific feature you're looking for?",
    "material": "What material are you looking for?",
    "color": "Do you have a color preference?",
    "style": "Any particular style or fit you prefer?",
    "size": "What size do you need?",
    "use_case": "What will you be using this for?",
    "other": "Is there anything else I should know about what you're looking for?",
}

# H1a 대상, 이번엔 미변경 / H1a target, unchanged this iteration.
BM25_WEIGHTS = "0.0, 6.0, 4.0, 2.5, 2.5, 1.5, 1.0"
# R3, damin_start 값 유지 / R3, kept from damin_start.
PROFILE_BOOST = 0.2
# R2 감점 계수. 실측상 >0 은 IO 를 해침(_ingest_message 주석) → 기본 0, private knob 으로만 유지.
# R2 demotion coefficient. Measured: >0 hurts Intent Override (see _ingest_message) → default 0,
# kept only as a knob for a possibly-different private simulator.
DEMOTE_COEF = 0.0


def _text(value: object) -> str:
    """카탈로그 필드(문자열/리스트/딕트)를 검색용 평문으로 / flatten a catalog field to plain text."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _terms(text: str) -> list[str]:
    """토큰화 + stopword/boilerplate 제거 / tokenize and strip stopwords + reply boilerplate."""
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1
        and token.lower() not in STOPWORDS
        and token.lower() not in REPLY_NOISE
    ]


class _SessionState:
    __slots__ = (
        "history", "demoted_terms", "seen_asins", "exhausted", "last_attribute",
        "repeat_count", "profile_terms", "override_seen", "forced_question", "asked_open",
    )

    def __init__(self) -> None:
        # R1: 모든 유저 메시지, 절대 삭제 안 함 / every user message, never cleared.
        self.history: list[str] = []
        # R2: override 이전 선호 term (유지하되 감점) / pre-override preference terms (kept but demoted).
        self.demoted_terms: set[str] = set()
        # R7: 지금까지 추천한 asin 전체 / every asin recommended so far.
        self.seen_asins: set[str] = set()
        # 더 나올 게 없는 속성 / attributes with nothing left to give.
        self.exhausted: set[str] = set()
        self.last_attribute: str | None = None
        self.repeat_count = 0
        self.profile_terms: list[str] = []     # R3
        self.override_seen = False             # R2
        # H5: "not quite right yet" 받으면 다음 턴 강제 질문 / force a question next turn after "not quite right yet".
        self.forced_question = False
        # open_first: 열린 질문(other) 1회 사용 여부 / whether the one open question (other) has been asked.
        self.asked_open = False


class Agent:
    """누적 BM25 검색 + open_first 질문 + override/seen-set 상태관리.
    Cumulative BM25 retrieval + open_first questioning + override/seen-set state management.
    """

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self.connection = sqlite3.connect(":memory:")
        self._sessions: dict[str, _SessionState] = {}
        self._build_index()

    def _build_index(self) -> None:
        """카탈로그 50k 를 in-memory FTS5 로 색인 / index the 50k catalog into in-memory FTS5."""
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, title, categories, features, details, store, description, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        batch: list[tuple[str, str, str, str, str, str, str]] = []
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                batch.append((
                    str(product["parent_asin"]),
                    _text(product.get("title")),
                    _text(product.get("categories")),
                    _text(product.get("features")),
                    _text(product.get("details")),
                    _text(product.get("store")),
                    _text(product.get("description")),
                ))
                if len(batch) >= 1000:
                    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
        if batch:
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        self.connection.commit()

    def reset(self, session_id: str, user_profile: dict) -> None:
        state = _SessionState()
        if isinstance(user_profile, dict):
            # R3: preference_tags/summary 는 정답을 직접 가리키지 않는 약한 신호 → 낮은 가중치 재랭킹에만.
            # R3: preference_tags/summary are a weak signal that does not point at the answer →
            #     used only for a low-weight rerank.
            tags = user_profile.get("preference_tags") or []
            summary = user_profile.get("summary") or ""
            profile_text = " ".join([*(str(tag) for tag in tags), str(summary)])
            state.profile_terms = list(dict.fromkeys(_terms(profile_text)))[:20]
        self._sessions[session_id] = state

    # ---- 대화 상태 갱신 / update conversation state -------------------------

    def _ingest_message(self, state: _SessionState, message: str, turn: int) -> None:
        state.history.append(message)

        # R2 — intent override 감지 (턴 3~, 메시지 패턴) / detect intent override (turn 3+, message pattern).
        if not state.override_seen and turn >= 3 and OVERRIDE_RE.search(message):
            state.override_seen = True
            # 이터레이션 1 실측: 버려진 선호(old_value)를 음의 가중치로 감점하면 IO 붕괴 (0.87→0.20/0.90).
            # 이유 — 시뮬레이터의 old_value 는 타깃 상품 메타데이터에서 파생된다. 노이즈가 아니라
            # 여전히 타깃을 가리키는 신호라, 감점하면 타깃도 같이 내려간다. override 의 new_value 는
            # 교체가 아니라 '추가' 신호일 뿐 → 누적만으로 자연히 우선된다.
            # Iteration-1 measurement: demoting the abandoned preference (old_value) collapses IO
            # (0.87 → 0.20 / 0.90). Reason — the simulator's old_value is derived from the target
            # product's own metadata. It is not noise; it still points at the target, so demoting it
            # drags the target down too. The override's new_value is an *additional* signal, not a
            # replacement → accumulation alone makes it dominate.
            # DEMOTE_COEF 는 private set 대비 knob 으로 남기되 기본 0 /
            # DEMOTE_COEF stays as a knob for a possibly-different private simulator; default 0.
            if DEMOTE_COEF > 0 and state.history:
                first = state.history[0]
                tail = first.split(". ", 1)[1] if ". " in first else ""
                stale = set(_terms(tail))
                new_intent = NEW_INTENT_RE.search(message)
                if new_intent:
                    stale.difference_update(_terms(new_intent.group(1)))
                state.demoted_terms.update(stale)
            # R7 예외 — override 경계에서 seen-set 리셋 (핵심). F4: override 전 히트는 무집계라,
            # 그때 노출한 타깃을 이후에 차단하면 안 된다.
            # R7 exception — reset seen-set at the override boundary (critical). F4: pre-override hits
            # are not scored, so a target shown then must not be blocked afterwards.
            state.seen_asins.clear()
            state.last_attribute = None
            state.repeat_count = 0
            return

        # H5 — NO_NEW_INFO 3패턴 분리 / branch on the 3 NO_NEW_INFO patterns.
        if state.last_attribute is not None:
            if NOT_RIGHT_RE.search(message):
                # ask_attribute=None 이었다는 신호 → 소진 아님, 다음 턴 반드시 질문.
                # signal that we sent ask_attribute=None → not exhaustion; must ask next turn.
                state.forced_question = True
                state.repeat_count = 0
            elif ADDITIONAL_RE.search(message) or BOUNDARY_RE.search(message):
                # 그 속성 소진 / exhaust that attribute.
                state.exhausted.add(state.last_attribute)
                state.repeat_count = 0
            elif CONSTRAINT_RE.search(message):
                # 실제 제약이 공개됨 → 반복 카운터만 리셋 (누적은 history 가 함).
                # a real constraint was disclosed → just reset the repeat counter (history does the accumulating).
                state.repeat_count = 0
            else:
                state.repeat_count += 1
                if state.repeat_count >= 2:
                    state.exhausted.add(state.last_attribute)
                    state.repeat_count = 0

    # ---- 검색 / retrieval (R4) ---------------------------------------------

    def _search(self, state: _SessionState, top_k: int) -> list[dict]:
        # R1/R4: 누적 대화에서 쿼리 term, 감점 term 은 제외 / query terms from the whole conversation,
        # minus demoted terms.
        query_terms = [
            t for t in dict.fromkeys(_terms(" ".join(state.history)))
            if t not in state.demoted_terms
        ][:60]
        if not query_terms:
            return []
        # R7 로 상당수가 제외되므로 후보 풀을 넉넉히 / big pool because R7 excludes many.
        pool = max(top_k * 20, 200)
        expr = " OR ".join(f'"{t}"' for t in query_terms)
        scores = {
            str(asin): float(score)
            for asin, score in self.connection.execute(
                f"SELECT parent_asin, bm25(products, {BM25_WEIGHTS}) AS score "
                "FROM products WHERE products MATCH ? ORDER BY score LIMIT ?",
                (expr, pool),
            ).fetchall()
        }
        if not scores:
            return []

        # R3 — profile term 약한 가산. bm25 는 음수(작을수록 좋음)라 음수 pscore 를 더하면 순위 상승.
        # R3 — weak additive boost from profile terms. bm25 is negative (smaller = better), so adding
        # a negative pscore lifts the rank.
        if state.profile_terms:
            pexpr = " OR ".join(f'"{t}"' for t in state.profile_terms)
            for asin, pscore in self.connection.execute(
                f"SELECT parent_asin, bm25(products, {BM25_WEIGHTS}) AS score "
                "FROM products WHERE products MATCH ? ORDER BY score LIMIT ?",
                (pexpr, pool * 4),
            ).fetchall():
                key = str(asin)
                if key in scores:
                    scores[key] += PROFILE_BOOST * float(pscore)

        # R2 — 감점 term 매칭 후보에 페널티. 음수 pscore 를 빼면 점수 상승 = 순위 하락. (기본 off)
        # R2 — penalty on candidates matching demoted terms. Subtracting a negative pscore raises the
        # score = worse rank. (off by default)
        if state.demoted_terms:
            dexpr = " OR ".join(f'"{t}"' for t in list(state.demoted_terms)[:60])
            for asin, dscore in self.connection.execute(
                f"SELECT parent_asin, bm25(products, {BM25_WEIGHTS}) AS score "
                "FROM products WHERE products MATCH ? ORDER BY score LIMIT ?",
                (dexpr, pool * 4),
            ).fetchall():
                key = str(asin)
                if key in scores:
                    scores[key] -= DEMOTE_COEF * float(dscore)

        # R7 — 이전 턴 노출분 제외 후 top_k / drop previously-shown asins, then take top_k.
        ranked = [a for a in sorted(scores, key=lambda x: scores[x]) if a not in state.seen_asins]
        top = ranked[:top_k]
        state.seen_asins.update(top)
        return [{"parent_asin": a} for a in top]

    # ---- 질문 선택 / question selection (open_first) ----------------------
    #
    # 적응형 info-gain 순서(R5)는 이터레이션 1에서 폐기 (decision_log D6): greedy mining 구현이
    # 정적 순서보다 TS -0.015, DI 정성 트랙의 dispersion 기반 info-gain 도 아직 퍼널과 동률.
    # 문헌 기반 재설계(후보 풀 최대 분할 / stage-aware)는 백로그.
    # Adaptive info-gain ordering (R5) was dropped in iteration 1 (decision_log D6): the greedy-mining
    # version scored TS -0.015 vs the static order, and the qualitative track's dispersion-based
    # info-gain still only ties the funnel. Literature-based redesign (max candidate-pool split /
    # stage-aware) is backlog.

    def _next_attribute(self, state: _SessionState, turn: int) -> str | None:
        if turn >= 10:
            return None
        if not state.asked_open:          # open_first: 턴 1 열린 질문 한 번 / one open question on turn 1.
            state.asked_open = True
            return OPEN_QUESTION
        for attribute in FUNNEL:          # 이후 F5 수율순 퍼널 / then the F5 yield-ordered funnel.
            if attribute not in state.exhausted:
                return attribute
        if OPEN_QUESTION not in state.exhausted:
            return OPEN_QUESTION          # 퍼널 소진 후에만 other 재사용 / reuse "other" only after the funnel is spent.
        return None

    # ---- 엔트리포인트 / entry point --------------------------------------

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        state = self._sessions.get(session_id)
        if state is None:
            raise RuntimeError("reset must be called before respond")

        self._ingest_message(state, user_message, turn)
        recommendations = self._search(state, top_k)

        ask_attribute = self._next_attribute(state, turn)
        if ask_attribute is None and state.forced_question and turn < 10:
            # H5 — "not quite right yet"(= 직전에 ask_attribute=None) 이후엔 반드시 질문.
            # H5 — after "not quite right yet" (= we sent ask_attribute=None last turn), must ask.
            for candidate in (*FUNNEL, OPEN_QUESTION):
                if candidate not in state.exhausted:
                    ask_attribute = candidate
                    break
        state.forced_question = False

        if ask_attribute is not None:
            message = ATTRIBUTE_PROMPTS[ask_attribute]
        else:
            message = "Here are the closest matches I found."
        state.last_attribute = ask_attribute

        return {
            "message": message,
            "ask_attribute": ask_attribute,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }

    def debug_state(self, session_id: str) -> dict:
        """playground 용 상태 스냅샷 (respond 동작 불변) / state snapshot for the playground (does not affect respond)."""
        state = self._sessions.get(session_id)
        if state is None:
            return {"memory_kind": "cumulative (not started)"}
        return {
            "memory_kind": "cumulative — every turn kept",
            "turns_in_history": len(state.history),
            "override_seen": state.override_seen,
            "demoted_terms": sorted(state.demoted_terms),
            "seen_asins": len(state.seen_asins),
            "exhausted_attributes": sorted(state.exhausted),
            "asked_open": state.asked_open,
            "last_attribute": state.last_attribute,
            "profile_terms": state.profile_terms,
        }
