from typing import Any

from starter.helper.config import ALLOWED_ATTRIBUTES, REPLACEMENT_MARKERS
from starter.helper.dataclasses import SessionState
from starter.helper.utils import _EXHAUST_RE, _JUDGMENT_RE, _OVERRIDE_RE, _REAL_ATTRS
from starter.intent.evidence_extractor import EvidenceExtractor


class StateManager:
    """Own SessionState creation and all conversation-state transitions."""

    def __init__(self, evidence_extractor: EvidenceExtractor) -> None:
        self.extractor = evidence_extractor

    def create_state(self, profile: dict[str, Any]) -> SessionState:
        state = SessionState(profile=dict(profile or {}))
        state.profile_importance = self._profile_importance(state.profile)
        return state

    def _profile_importance(self, profile: dict[str, Any]) -> dict[str, float]:
        result: dict[str, float] = {}
        for tag in (str(x).strip().lower() for x in profile.get("preference_tags") or []):
            attr = self._map_internal_to_ask(tag)
            if attr:
                result[attr] = 1.0
        return result

    @staticmethod
    def _map_internal_to_ask(attribute: str) -> str | None:
        attr = attribute.lower()
        if attr in ALLOWED_ATTRIBUTES:
            return attr
        if attr in ("comfort", "durability", "performance", "warmth", "weather"):
            return "feature"
        if attr == "fit":
            return "style"
        return None

    def update(self, state: SessionState, message: str, turn: int) -> None:
        # turn is intentionally accepted for API parity; original v2.8.4.1 does not use it.
        del turn
        state.messages.append(message)
        if not state.category_terms:
            state.category_terms = self.extractor.extract_category_terms(message)

        lower = message.lower()
        is_override = bool(_OVERRIDE_RE.search(message))
        before_status = (
            {id(ev): ev.status for bucket in state.evidence.values() for ev in bucket}
            if is_override
            else {}
        )
        before_size = {attr: len(bucket) for attr, bucket in state.evidence.items()}

        for evidence in self.extractor.extract(message):
            bucket = state.evidence.setdefault(evidence.attribute, [])
            if evidence.status == "NO_PREFERENCE":
                state.no_preference.add(evidence.attribute)
                for old in bucket:
                    if old.status == "ACTIVE":
                        old.status = "SUPERSEDED"
                bucket.append(evidence)
                continue

            state.no_preference.discard(evidence.attribute)
            if any(marker in lower for marker in REPLACEMENT_MARKERS):
                for old in bucket:
                    if old.status == "ACTIVE":
                        old.status = "SUPERSEDED"

            if not any(
                old.status == evidence.status and old.value.lower() == evidence.value.lower()
                for old in bucket
            ):
                bucket.append(evidence)

        if is_override:
            state.exposure.clear()
            for bucket in state.evidence.values():
                for evidence in bucket:
                    if before_status.get(id(evidence)) == "ACTIVE" and evidence.status == "SUPERSEDED":
                        evidence.status = "ACTIVE"

        exhausted = _EXHAUST_RE.search(message)
        if exhausted and exhausted.group(1).lower() in _REAL_ATTRS:
            state.no_preference.add(exhausted.group(1).lower())
        elif _JUDGMENT_RE.search(message) and state.last_ask in _REAL_ATTRS:
            state.no_preference.add(state.last_ask)

        grew = [
            attr
            for attr, bucket in state.evidence.items()
            if len(bucket) > before_size.get(attr, 0)
        ]
        state.last_yielded = bool(grew)
        state.last_grew = list(grew)
        state.last_growth_counts = {
            attr: len(state.evidence.get(attr, [])) - before_size.get(attr, 0)
            for attr in grew
        }
        for attr in grew:
            state.asked_counts[attr] = 0

    @staticmethod
    def record_candidate_scores(
        state: SessionState,
        scored: list[tuple[str, float]],
        limit: int,
    ) -> None:
        state.last_candidate_scores = {
            asin: max(0.0, score) for asin, score in scored[:limit]
        }

    @staticmethod
    def record_response(
        state: SessionState,
        ask_attribute: str | None,
        recommendations: list[str],
    ) -> None:
        if ask_attribute:
            state.asked_counts[ask_attribute] += 1
        for asin in recommendations:
            state.exposure[asin] += 1
        state.last_ask = ask_attribute
