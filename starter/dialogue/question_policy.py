import math
from collections import Counter

from starter.catalog.repository import CatalogRepository
from starter.helper.config import ATTRIBUTE_PATTERNS, COLOR_RE, MATERIAL_RE, QUESTION_PROMPTS
from starter.helper.dataclasses import SessionState
from starter.helper.utils import _REAL_ATTRS, product_text


class QuestionPolicy:
    """v2.8.4 open-first, sticky, catalog-guarded question policy."""

    def __init__(
        self,
        catalog: CatalogRepository,
        *,
        candidate_window: int = 50,
        min_branch_fraction: float = 0.08,
        min_discrimination: float = 0.16,
    ) -> None:
        self.catalog = catalog
        self.candidate_window = candidate_window
        self.min_branch_fraction = min_branch_fraction
        # Retained for exact v2.8.4.1 configuration parity; original policy does not read it.
        self.min_discrimination = min_discrimination

    def _candidate_attribute_distribution(
        self, candidate_ids: list[str], attribute: str
    ) -> Counter:
        distribution: Counter = Counter()
        for asin in candidate_ids[: self.candidate_window]:
            product = self.catalog.get(asin)
            text = product_text(product)
            if attribute == "material":
                material = MATERIAL_RE.search(text)
                distribution[material.group(1).lower() if material else "?"] += 1
            elif attribute == "color":
                color = COLOR_RE.search(text)
                distribution[color.group(1).lower() if color else "?"] += 1
            elif attribute == "brand":
                store = str(product.get("store") or "").strip().lower()
                distribution[store or "?"] += 1
            elif attribute == "budget":
                price = product.get("price")
                try:
                    parsed = float(price) if price not in (None, "") else None
                except (TypeError, ValueError):
                    parsed = None
                if parsed is None:
                    distribution["?"] += 1
                else:
                    distribution[
                        "<25" if parsed < 25 else "25-50" if parsed < 50 else "50-100" if parsed < 100 else "100+"
                    ] += 1
            else:
                vocab = ATTRIBUTE_PATTERNS.get(attribute, ())
                hits = tuple(term for term in vocab if term in text)[:3]
                distribution[hits or ("?",)] += 1
        return distribution

    @staticmethod
    def _normalized_entropy(distribution: Counter) -> float:
        total = sum(distribution.values())
        if total <= 1 or len(distribution) <= 1:
            return 0.0
        entropy = -sum(
            (count / total) * math.log(count / total + 1e-12)
            for count in distribution.values()
        )
        return entropy / math.log(len(distribution))

    def _guarded_discrimination(self, distribution: Counter) -> tuple[float, float]:
        total = sum(distribution.values())
        if total <= 1:
            return 0.0, 0.0

        unknown = distribution.get("?", 0)
        answerability = max(0.0, 1.0 - unknown / total)
        observed = Counter({key: count for key, count in distribution.items() if key != "?"})
        observed_total = sum(observed.values())
        if observed_total <= 1:
            return 0.0, answerability

        min_support = max(2, math.ceil(self.min_branch_fraction * observed_total))
        collapsed: Counter = Counter()
        other = 0
        for value, count in observed.items():
            if count < min_support:
                other += count
            else:
                collapsed[value] += count
        if other:
            collapsed["__OTHER__"] += other

        if len(collapsed) <= 1:
            return 0.0, answerability

        denominator = sum(collapsed.values())
        discrimination = 1.0 - sum((count / denominator) ** 2 for count in collapsed.values())
        return discrimination, answerability

    def choose(self, state: SessionState, candidate_ids: list[str]) -> str | None:
        if not state.asked_open:
            state.asked_open = True
            return "other"

        if (
            state.last_yielded
            and state.last_ask in _REAL_ATTRS
            and state.last_ask not in state.no_preference
        ):
            return state.last_ask

        if not state.last_yielded and state.last_ask in _REAL_ATTRS:
            return "other"

        if not (state.last_yielded and state.last_ask == "other") or not candidate_ids:
            return "other"

        eligible = [
            attr
            for attr in state.last_grew
            if (
                attr in _REAL_ATTRS
                and attr not in state.no_preference
                and state.asked_counts[attr] == 0
                and state.last_growth_counts.get(attr, 0) >= 2
            )
        ]
        if not eligible:
            return "other"

        best_attr, best_value = None, -1.0
        for attr in eligible:
            distribution = self._candidate_attribute_distribution(candidate_ids, attr)
            discrimination, answerability = self._guarded_discrimination(distribution)
            value = (0.20 + 0.80 * discrimination) * (0.50 + 0.50 * answerability)
            if value > best_value:
                best_value, best_attr = value, attr

        return best_attr if best_attr is not None else "other"

    @staticmethod
    def build_question(attribute: str | None) -> str:
        if attribute:
            return QUESTION_PROMPTS.get(attribute, "What else matters most for this choice?")
        return "These are my best matches based on what you've told me so far."
