"""damin-start — spare improved baseline.

공식 스타터 대비 바뀐 것:
  1. 대화 전체를 누적해서 BM25 검색 (마지막 메시지만 보지 않음)
  2. 매 턴 실측 수율 순서로 미소진 속성 하나를 질문 (feature→material→color→style→size→use_case→other)
  3. history 를 절대 지우지 않음 (intent_override 때도)
  4. profile_terms 로 약한 재랭킹

playground 용으로 `debug_state()` 만 추가했다 (respond 동작 불변).
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

LABEL = "damin-start"

TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
}


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _terms(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    ]


# public_set 200개 실측 기준(classify_constraint가 실제로 이 카테고리를 배정하는 비율):
# feature 96% > material 76% > color 26% > style 9% > size 4% > use_case 2% > brand/budget 0%.
ATTRIBUTE_ORDER = ("feature", "material", "color", "style", "size", "use_case", "other")
ATTRIBUTE_PROMPTS = {
    "feature": "Is there a specific feature you're looking for?",
    "material": "What material are you looking for?",
    "color": "Do you have a color preference?",
    "style": "Any particular style or fit you prefer?",
    "size": "What size do you need?",
    "use_case": "What will you be using this for?",
    "other": "Is there anything else I should know about what you're looking for?",
}

# 이전 질문에 새 정보가 안 나왔음을 알리는 신호. "your judgment"(boundary 1회성 대사)도 묶는다 —
# 세션 중단이 아니라 "그 속성만 소진"으로 취급한다.
NO_NEW_INFO_RE = re.compile(r"additional preference|not quite right yet|your judg", re.IGNORECASE)


class _SessionState:
    __slots__ = ("history", "exhausted", "last_attribute", "repeat_count", "profile_terms")

    def __init__(self) -> None:
        self.history: list[str] = []
        self.exhausted: set[str] = set()
        self.last_attribute: str | None = None
        self.repeat_count = 0
        self.profile_terms: list[str] = []


class Agent:
    """BM25 retrieval over the accumulated conversation + turn-by-turn attribute questioning."""

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self.connection = sqlite3.connect(":memory:")
        self._sessions: dict[str, _SessionState] = {}
        self._build_index()

    def _build_index(self) -> None:
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
                batch.append(
                    (
                        str(product["parent_asin"]),
                        _text(product.get("title")),
                        _text(product.get("categories")),
                        _text(product.get("features")),
                        _text(product.get("details")),
                        _text(product.get("store")),
                        _text(product.get("description")),
                    )
                )
                if len(batch) >= 1000:
                    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
        if batch:
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        self.connection.commit()

    def reset(self, session_id: str, user_profile: dict) -> None:
        # preference_tags/summary 는 정답을 직접 가리키지 않는 약한 신호라 낮은 가중치 재랭킹에만 쓴다.
        state = _SessionState()
        if isinstance(user_profile, dict):
            tags = user_profile.get("preference_tags") or []
            summary = user_profile.get("summary") or ""
            profile_text = " ".join([*(str(tag) for tag in tags), str(summary)])
            state.profile_terms = list(dict.fromkeys(_terms(profile_text)))[:20]
        self._sessions[session_id] = state

    def _query_terms(self, state: _SessionState) -> list[str]:
        return list(dict.fromkeys(_terms(" ".join(state.history))))[:60]

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        state = self._sessions.get(session_id)
        if state is None:
            raise RuntimeError("reset must be called before respond")

        # history 는 절대 지우지 않는다 (intent_override 포함).
        state.history.append(user_message)

        if state.last_attribute is not None:
            if NO_NEW_INFO_RE.search(user_message):
                state.exhausted.add(state.last_attribute)
                state.repeat_count = 0
            else:
                state.repeat_count += 1
                if state.repeat_count >= 2:
                    state.exhausted.add(state.last_attribute)
                    state.repeat_count = 0

        unique_terms = self._query_terms(state)
        expression = " OR ".join(f'"{term}"' for term in unique_terms)
        weights = "0.0, 6.0, 4.0, 2.5, 2.5, 1.5, 1.0"
        if not expression:
            recommendations: list[dict] = []
        else:
            candidate_pool = max(top_k * 5, 50)
            scores = {
                str(asin): float(score)
                for asin, score in self.connection.execute(
                    f"SELECT parent_asin, bm25(products, {weights}) AS score "
                    "FROM products WHERE products MATCH ? ORDER BY score LIMIT ?",
                    (expression, candidate_pool),
                ).fetchall()
            }
            if state.profile_terms and scores:
                profile_expr = " OR ".join(f'"{term}"' for term in state.profile_terms)
                for asin, pscore in self.connection.execute(
                    f"SELECT parent_asin, bm25(products, {weights}) AS score "
                    "FROM products WHERE products MATCH ? ORDER BY score LIMIT ?",
                    (profile_expr, candidate_pool * 4),
                ).fetchall():
                    key = str(asin)
                    if key in scores:
                        scores[key] += 0.2 * float(pscore)
            ranked = sorted(scores, key=lambda asin: scores[asin])[:top_k]
            recommendations = [{"parent_asin": asin} for asin in ranked]

        ask_attribute = None
        message = "Here are the closest matches I found."
        if turn < 10:
            for attribute in ATTRIBUTE_ORDER:
                if attribute not in state.exhausted:
                    ask_attribute = attribute
                    message = ATTRIBUTE_PROMPTS[attribute]
                    break
        state.last_attribute = ask_attribute

        return {
            "message": message,
            "ask_attribute": ask_attribute,
            "recommendations": recommendations,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }

    def debug_state(self, session_id: str) -> dict:
        state = self._sessions.get(session_id)
        if state is None:
            return {"memory_kind": "cumulative (not started)"}
        return {
            "memory_kind": "cumulative — every turn's message kept",
            "query_scope": "full conversation",
            "query_terms": self._query_terms(state),
            "exhausted_attributes": sorted(state.exhausted),
            "last_attribute": state.last_attribute,
            "repeat_count": state.repeat_count,
            "turns_in_history": len(state.history),
            "profile_terms": state.profile_terms,
        }
