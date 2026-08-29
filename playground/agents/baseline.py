"""baseline = 공식 `starter/agent.py` 그대로. playground 용 계측만 얹은 얇은 서브클래스.

- `respond()` 는 공식 구현을 그대로 호출한다 → 채점 결과 동일 (`runner --check` 로 확인).
- `debug_state()` 만 추가: 이 agent 는 **상태가 없다**는 사실을 UI 에 정직하게 노출한다.
  누적 메모리가 없으므로 매 턴 "이번 메시지"에서만 검색어가 나오고, 다음 턴엔 사라진다.

개선 버전은 이 파일을 상속하지 말고 `playground/agents/<vN>.py` 로 새로 만든다.
"""
from __future__ import annotations

from starter.agent import Agent as _OfficialAgent
from starter.agent import _terms

LABEL = "baseline"


class Agent(_OfficialAgent):
    def __init__(self, catalog_path: str = "data/catalog.jsonl") -> None:
        super().__init__(catalog_path)
        self._last_query: dict[str, list[str]] = {}

    def reset(self, session_id: str, user_profile: dict) -> None:
        super().reset(session_id, user_profile)
        self._last_query.pop(session_id, None)

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        response = super().respond(session_id, user_message, turn, top_k)
        # 공식 구현이 이번 턴에 실제로 쓴 검색어를 그대로 재현 (respond 동작에는 영향 없음)
        self._last_query[session_id] = list(dict.fromkeys(_terms(user_message)))[:40]
        return response

    def debug_state(self, session_id: str) -> dict:
        return {
            "memory_kind": "none (stateless)",
            "query_scope": "current message only",
            "query_terms": self._last_query.get(session_id, []),
            "exhausted_attributes": [],
            "note": "no conversation memory · profile unused · ask_attribute always None",
        }
