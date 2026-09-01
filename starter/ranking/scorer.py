import math
import re
from typing import Any

from starter.catalog.repository import CatalogRepository
from starter.helper.dataclasses import Evidence, SessionState
from starter.helper.utils import _terms, product_text
from starter.intent.belief import active_evidence


class CandidateScorer:
    """Combine retrieval relevance, explicit evidence match, and quality prior."""

    def __init__(
        self,
        catalog: CatalogRepository,
        *,
        semantic_weight: float = 1.0,
        explicit_match_weight: float = 1.35,
        quality_weight: float = 0.025,
    ) -> None:
        self.catalog = catalog
        self.semantic_weight = semantic_weight
        self.explicit_match_weight = explicit_match_weight
        self.quality_weight = quality_weight

    @staticmethod
    def _evidence_match(evidence: Evidence, product: dict[str, Any], text: str) -> float:
        value = evidence.value.lower().strip()
        if not value:
            return 0.0
        if evidence.attribute == "budget":
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
        hits = sum(1 for term in terms if re.search(rf"\b{re.escape(term)}\b", text))
        return hits / len(terms)

    @staticmethod
    def _quality_prior(product: dict[str, Any]) -> float:
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

    def score(
        self,
        state: SessionState,
        candidates: dict[str, float],
    ) -> list[tuple[str, float]]:
        active = active_evidence(state)
        scored: list[tuple[str, float]] = []

        for asin, retrieval_score in candidates.items():
            product = self.catalog.get(asin)
            text = product_text(product)
            explicit_match = 0.0
            for evidence in active:
                weight = 1.35 if evidence.hard else 0.85
                explicit_match += weight * self._evidence_match(evidence, product, text)

            score = (
                self.semantic_weight * retrieval_score
                + self.explicit_match_weight * explicit_match
                + self.quality_weight * self._quality_prior(product)
            )
            scored.append((asin, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored
