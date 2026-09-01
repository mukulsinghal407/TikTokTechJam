from starter.helper.dataclasses import SessionState, Evidence
from starter.helper.utils import _dedupe, _terms
from starter.helper.config import ALLOWED_ATTRIBUTES

def active_evidence(
    state: SessionState,
) -> list[Evidence]:
    return [
        evidence
        for bucket in state.evidence.values()
        for evidence in bucket
        if evidence.status == "ACTIVE"
    ]


def active_terms(state: SessionState) -> list[str]:
    terms = []

    for evidence in active_evidence(state):
        terms.extend(_terms(evidence.value))

    return _dedupe(terms)


def unknown_attributes(
    state: SessionState,
) -> list[str]:
    known = {
        attribute
        for attribute, bucket in state.evidence.items()
        if any(ev.status == "ACTIVE" for ev in bucket)
    }

    known |= state.no_preference

    return [
        attribute
        for attribute in ALLOWED_ATTRIBUTES
        if attribute not in known
        and attribute not in {"category", "other"}
    ]


def intent_uncertainty(state: SessionState) -> float:
    active = active_evidence(state)

    hard = sum(ev.hard for ev in active)

    certainty = min(
        1.0,
        0.16 * len(active)
        + 0.18 * hard
        + (0.18 if state.category_terms else 0.0),
    )

    return 1.0 - certainty