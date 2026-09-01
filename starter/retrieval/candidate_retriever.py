from starter.catalog.repository import CatalogRepository
from starter.catalog.search_index import FTS5SearchIndex
from starter.helper.dataclasses import SessionState
from starter.helper.utils import _dedupe
from starter.intent.belief import active_terms


class CandidateRetriever:
    """Two-route BM25 retrieval plus carry-over and R7 exposure suppression."""

    def __init__(
        self,
        catalog: CatalogRepository,
        search_index: FTS5SearchIndex,
        *,
        candidate_limit: int = 400,
        route_limit: int = 200,
        exposure_decay: float = 0.0,
    ) -> None:
        self.catalog = catalog
        self.search_index = search_index
        self.candidate_limit = candidate_limit
        self.route_limit = route_limit
        self.exposure_decay = exposure_decay

    @staticmethod
    def _merge_route(
        scores: dict[str, float],
        rows: list[tuple[str, float]],
        route_weight: float,
    ) -> None:
        if not rows:
            return
        maximum = max(score for _, score in rows) or 1.0
        for asin, score in rows:
            scores[asin] = max(scores.get(asin, 0.0), route_weight * score / maximum)

    def _merge_previous_candidates(self, scores: dict[str, float], state: SessionState) -> None:
        for asin, previous in state.last_candidate_scores.items():
            if self.catalog.contains(asin):
                scores[asin] = max(scores.get(asin, 0.0), previous * 0.78)

    def _truncate(self, scores: dict[str, float]) -> dict[str, float]:
        return dict(
            sorted(scores.items(), key=lambda item: item[1], reverse=True)[: self.candidate_limit]
        )

    def _apply_exposure_policy(
        self, ranked: dict[str, float], state: SessionState
    ) -> dict[str, float]:
        if not state.exposure:
            return ranked
        decay = self.exposure_decay
        if decay <= 0.0:
            return {asin: score for asin, score in ranked.items() if asin not in state.exposure}
        return {
            asin: score * (decay ** state.exposure[asin]) if asin in state.exposure else score
            for asin, score in ranked.items()
        }

    def retrieve(self, state: SessionState) -> dict[str, float]:
        scores: dict[str, float] = {}
        category_terms = state.category_terms
        constraint_terms = active_terms(state)
        intent_terms = _dedupe(category_terms + constraint_terms)

        self._merge_route(
            scores,
            self.search_index.search(
                intent_terms,
                self.route_limit,
                (0.0, 6.0, 4.2, 2.8, 2.6, 1.2, 1.5),
            ),
            1.00,
        )

        if constraint_terms:
            self._merge_route(
                scores,
                self.search_index.search(
                    _dedupe(category_terms + constraint_terms),
                    self.route_limit,
                    (0.0, 5.5, 3.5, 4.0, 3.8, 1.0, 2.2),
                ),
                1.05,
            )

        self._merge_previous_candidates(scores, state)
        return self._apply_exposure_policy(self._truncate(scores), state)
