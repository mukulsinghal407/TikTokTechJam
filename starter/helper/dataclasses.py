from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

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
    # v2_8_4: 직전 응답에서 새로 공개된 차원들. / dimensions newly disclosed in the last reply.
    last_grew: list[str] = field(default_factory=list)
    # v2_8_4: 차원별 이번 턴 신규 evidence 개수 (깊이 신호). / new evidence count by dimension (depth signal).
    last_growth_counts: dict[str, int] = field(default_factory=dict)

class TurnClassification(BaseModel):
    intent_changed: bool                    # True = OVERRIDE, False = ACCUMULATION
    confidence: float                       # 0.0-1.0
    reasoning: str                          # one short sentence -- useful for your run/iteration log
    all_updated_attributes: dict[str, str]      # all attributes tracked so far, including any new ones from this turn

@dataclass
class TokenUsage:
    """Per-turn token counts, read straight off Ollama's response object."""
    prompt_tokens: int
    completion_tokens: int
 
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

export = {
    "Evidence": Evidence,
    "SessionState": SessionState,
    "TurnClassification": TurnClassification,
    "TokenUsage": TokenUsage
}