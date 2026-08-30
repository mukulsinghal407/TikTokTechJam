from collections import Counter
from dataclasses import dataclass, field
from typing import Any

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

export = {
    "Evidence": Evidence,
    "SessionState": SessionState,
}