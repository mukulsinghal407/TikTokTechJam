from collections import Counter
from typing import Any

from starter.catalog.repository import CatalogRepository
from starter.helper.config import COLOR_RE, MATERIAL_RE
from starter.helper.dataclasses import SessionState
from starter.helper.utils import product_text
from starter.intent.belief import intent_uncertainty, unknown_attributes


class RiskAwareTopKSelector:
    """Risk-aware coverage portfolio for uncertain intent."""

    def __init__(
        self,
        catalog: CatalogRepository,
        *,
        coverage_strength: float = 0.12,
        candidate_window: int = 80,
        uncertainty_threshold: float = 0.28,
    ) -> None:
        self.catalog = catalog
        self.coverage_strength = coverage_strength
        self.candidate_window = candidate_window
        self.uncertainty_threshold = uncertainty_threshold

    @staticmethod
    def _signature(product: dict[str, Any], unresolved: list[str]) -> tuple[str, ...]:
        text = product_text(product)
        signature: list[str] = []
        if "material" in unresolved:
            material = MATERIAL_RE.search(text)
            signature.append(f"m:{material.group(1).lower() if material else '?'}")
        if "color" in unresolved:
            color = COLOR_RE.search(text)
            signature.append(f"c:{color.group(1).lower() if color else '?'}")
        return tuple(signature)

    def select(
        self,
        state: SessionState,
        scored: list[tuple[str, float]],
        top_k: int,
    ) -> list[str]:
        if not scored:
            return []

        uncertainty = intent_uncertainty(state)
        unresolved = unknown_attributes(state)
        if uncertainty < self.uncertainty_threshold or not unresolved:
            return [asin for asin, _ in scored[:top_k]]

        selected: list[str] = []
        signature_counts: Counter = Counter()
        remaining = scored[: min(len(scored), self.candidate_window)]

        while remaining and len(selected) < top_k:
            best_index, best_utility = 0, -float("inf")
            for index, (asin, base) in enumerate(remaining):
                signature = self._signature(self.catalog.get(asin), unresolved)
                novelty = (
                    sum(1.0 / (1.0 + signature_counts[item]) for item in signature) / len(signature)
                    if signature
                    else 0.0
                )
                utility = base + self.coverage_strength * uncertainty * novelty
                if utility > best_utility:
                    best_utility, best_index = utility, index

            asin, _ = remaining.pop(best_index)
            selected.append(asin)
            for item in self._signature(self.catalog.get(asin), unresolved):
                signature_counts[item] += 1

        return selected
