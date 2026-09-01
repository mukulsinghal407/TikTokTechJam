from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    """One constraint observed from the conversation."""
    attribute: str
    value: str
    # ACTIVE / NO_PREFERENCE / SUPERSEDED
    status: str = "ACTIVE"
    # Hard constraint flag (higher scoring weight).
    hard: bool = False


@dataclass
class SessionState:
    """Per-session accumulated state."""
    profile: dict[str, Any]
    messages: list[str] = field(default_factory=list)
    evidence: dict[str, list[Evidence]] = field(default_factory=dict)
    no_preference: set[str] = field(default_factory=set)
    asked_counts: Counter = field(default_factory=Counter)
    last_candidate_scores: dict[str, float] = field(default_factory=dict)
    category_terms: list[str] = field(default_factory=list)
    profile_importance: dict[str, float] = field(default_factory=dict)
    # asin -> times recommended so far (exposure decay lever).
    exposure: Counter = field(default_factory=Counter)
    # Whether the open ("other") question has already been asked.
    asked_open: bool = False
    # The attribute asked last turn (sticky follow-up guard).
    last_ask: str | None = None
    # Did the last turn yield a real constraint.
    last_yielded: bool = False
    # Dimensions newly disclosed in the last reply.
    last_grew: list[str] = field(default_factory=list)
    # New evidence count by dimension (conversation-depth signal).
    last_growth_counts: dict[str, int] = field(default_factory=dict)
