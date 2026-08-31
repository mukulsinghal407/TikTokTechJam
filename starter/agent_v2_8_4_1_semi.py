"""Refactored v2.8.4.1 agent facade.

Behavior is intentionally kept equivalent to agent_v2_8_4_1 while responsibilities
are split across catalog, intent, retrieval, ranking, and dialogue modules.
"""
from pathlib import Path

from starter.catalog.repository import CatalogRepository
from starter.catalog.search_index import FTS5SearchIndex
from starter.dialogue.question_policy import QuestionPolicy
from starter.helper.dataclasses import SessionState
from starter.intent.evidence_extractor import EvidenceExtractor
from starter.intent.state_manager import StateManager
from starter.ranking.scorer import CandidateScorer
from starter.ranking.selector import RiskAwareTopKSelector
from starter.retrieval.candidate_retriever import CandidateRetriever


class Agent:
    """Public facade that orchestrates the recommendation pipeline."""

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog = CatalogRepository(catalog_path)
        self.search_index = FTS5SearchIndex(self.catalog, feature_multiplier=1.5)
        self.evidence_extractor = EvidenceExtractor()
        self.state_manager = StateManager(self.evidence_extractor)
        self.retriever = CandidateRetriever(
            self.catalog,
            self.search_index,
            candidate_limit=400,
            route_limit=200,
            exposure_decay=0.0,
        )
        self.scorer = CandidateScorer(
            self.catalog,
            semantic_weight=1.0,
            explicit_match_weight=1.35,
            quality_weight=0.025,
        )
        self.selector = RiskAwareTopKSelector(
            self.catalog,
            coverage_strength=0.12,
            candidate_window=80,
            uncertainty_threshold=0.28,
        )
        self.question_policy = QuestionPolicy(
            self.catalog,
            candidate_window=50,
            min_branch_fraction=0.08,
            min_discrimination=0.16,
        )
        self.sessions: dict[str, SessionState] = {}

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.sessions[session_id] = self.state_manager.create_state(user_profile)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        if session_id not in self.sessions:
            raise RuntimeError("reset must be called before respond")

        state = self.sessions[session_id]
        self.state_manager.update(state, user_message, turn)

        candidates = self.retriever.retrieve(state)
        scored = self.scorer.score(state, candidates)
        candidate_ids = [asin for asin, _ in scored]
        recommendations = self.selector.select(state, scored, top_k)

        self.state_manager.record_candidate_scores(
            state,
            scored,
            limit=self.retriever.candidate_limit,
        )

        ask_attribute = self.question_policy.choose(state, candidate_ids)
        message = self.question_policy.build_question(ask_attribute)
        self.state_manager.record_response(state, ask_attribute, recommendations)

        return {
            "message": message,
            "ask_attribute": ask_attribute,
            "recommendations": [{"parent_asin": asin} for asin in recommendations],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }
