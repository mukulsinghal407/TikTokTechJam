"""playground 러너 — 공식 evaluator의 턴 루프를 턴 단위로 재생한다.

로직은 `evaluator.local_evaluator` 에서 전부 import 한다 (복사 금지).
여기 있는 건 `evaluate()` 의 세션 루프를, 턴마다 상태를 내놓도록 분해한 것뿐이다.
러너가 뽑은 세션별 hit/rank 는 공식 `evaluate()` 와 일치해야 한다 (`regression_check`).

실행 (playground/ 안에서):
    python runner.py --check              # 회귀 가드 — 레포 루트의 공식 evaluate() 와 대조
    python runner.py --agent baseline     # 한 버전 전체 실행, 요약 출력

agent 가 노출하는 상태 (`debug_state(session_id) -> dict | None`) 권장 키:
    memory_kind          "none (stateless)" | "cumulative" | ...  — 사람이 읽는 한 줄
    query_terms          이번 턴 retrieval 에 실제로 쓴 검색어 (누적하면 누적된 것)
    query_scope          "current message" | "full conversation"
    exhausted_attributes list[str]
그 외 임의 키는 UI 가 generic 하게 렌더한다. 없으면 러너가 `_sessions[session_id]` 를
best-effort 로 직렬화한다 (공식 baseline 은 set 이라 거의 안 나옴).
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any

# 레포 루트의 evaluator/·starter/ 를 import (팀이 참가자 키트를 루트에 둠).
# playground/ 도 올려서 agents/ 를 import 할 수 있게 한다.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from evaluator.local_evaluator import (
    ALLOWED_ATTRIBUTES,
    MAX_TURNS,
    TOP_K,
    catalog_index,
    coarse_category,
    customer_reply,
    initial_message,
    load_jsonl,
    materialize_hidden_fields,
    metric_summary,
    normalize_recommendations,
)
from starter.agent import _terms

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CATALOG = ROOT / "data" / "catalog.jsonl"
DATASET = ROOT / "data" / "public_set.jsonl"
AGENTS_DIR = HERE / "agents"

# BM25 필드 가중치 — 공식 starter/agent.py 와 동일. "전체 BM25 순위" 진단의 고정 렌즈.
_BM25_WEIGHTS = "bm25(products, 0.0, 6.0, 4.0, 2.5, 2.5, 1.5, 1.0)"


# ---------------------------------------------------------------------------
# agent 버전 로딩
# ---------------------------------------------------------------------------
def available_agents() -> list[str]:
    return sorted(p.stem for p in AGENTS_DIR.glob("*.py") if p.stem != "__init__")


def load_agent_class(name: str):
    module = importlib.import_module(f"agents.{name}")
    return module.Agent


def agent_label(name: str) -> str:
    try:
        return getattr(importlib.import_module(f"agents.{name}"), "LABEL", name)
    except Exception:
        return name


# ---------------------------------------------------------------------------
# agent 내부 상태 introspection
# ---------------------------------------------------------------------------
def _describe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_describe(x) for x in obj]
    if isinstance(obj, set):
        return sorted(_describe(x) for x in obj)
    if isinstance(obj, dict):
        return {str(k): _describe(v) for k, v in obj.items()}
    slots = getattr(type(obj), "__slots__", None)
    if slots:
        return {s: _describe(getattr(obj, s, None)) for s in slots}
    d = getattr(obj, "__dict__", None)
    if d is not None:
        return {k: _describe(v) for k, v in d.items()}
    return repr(obj)


def agent_debug_state(agent: Any, session_id: str) -> Any:
    if hasattr(agent, "debug_state"):
        try:
            return agent.debug_state(session_id)
        except Exception:
            return None
    sessions = getattr(agent, "_sessions", None)
    if isinstance(sessions, dict):
        return _describe(sessions.get(session_id))
    if isinstance(sessions, set):
        return {"memory_kind": "none (stateless)", "tracked": session_id in sessions}
    return None


def product_brief(products: dict, asin: str) -> dict:
    p = products.get(asin, {})
    return {
        "parent_asin": asin,
        "title": p.get("title") or "(unknown)",
        "store": p.get("store"),
        "price": p.get("price"),
        "average_rating": p.get("average_rating"),
        "rating_number": p.get("rating_number"),
    }


# ---------------------------------------------------------------------------
# 진단용 카탈로그 인덱스 — 공식 starter Agent 의 FTS 인덱스를 그대로 재사용
# ("전체 BM25 순위" 는 agent 구현과 무관한 고정 렌즈라 러너가 소유한다.)
# ---------------------------------------------------------------------------
_diag_agent: Any = None


def _diag():
    global _diag_agent
    if _diag_agent is None:
        from starter.agent import Agent as _OfficialAgent

        _diag_agent = _OfficialAgent(str(CATALOG))
    return _diag_agent


def deep_rank(query_terms: list[str], target: str, cap: int = 2000) -> tuple[int | None, int]:
    terms = list(dict.fromkeys(query_terms))[:60]
    expression = " OR ".join(f'"{t}"' for t in terms if t)
    if not expression:
        return None, 0
    rows = _diag().connection.execute(
        f"SELECT parent_asin FROM products WHERE products MATCH ? ORDER BY {_BM25_WEIGHTS} LIMIT ?",
        (expression, cap),
    ).fetchall()
    ids = [str(r[0]) for r in rows]
    return (ids.index(target) + 1 if target in ids else None), len(ids)


# ---------------------------------------------------------------------------
# 세션 1개 — evaluate() 의 세션 루프와 동일한 순서로 한 턴씩 진행
# ---------------------------------------------------------------------------
class SessionRunner:
    def __init__(self, agent, sample, catalog_ids, categories, products,
                 diagnostics: bool = False, agent_name: str = "?") -> None:
        self.agent = agent
        self.agent_name = agent_name
        self.sample = sample
        self.catalog_ids = catalog_ids
        self.products = products
        self.diagnostics = diagnostics

        self.session_id = f"pg_{uuid.uuid4().hex}"
        agent.reset(self.session_id, sample["user_profile"])
        self.target = str(sample["ground_truth"]["parent_asin"])
        self.card, self.behavior = materialize_hidden_fields(sample, products)
        self.esample = {**sample, "intent_card": self.card, "behavior": self.behavior}
        self.disclosed: set[str] = set()
        self.boundary_used = False
        self.override_applied = sample["scenario_type"] != "intent_override"
        self.category = coarse_category(categories.get(self.target, []))
        self.user_message = initial_message(self.esample, self.category, self.disclosed)
        self.turn = 0
        self.done = False
        self.hit_turn: int | None = None
        self.best_rank: int | None = None
        self.turns: list[dict] = []
        # "내가 agent" 턴 기록 (수동 모드)
        self.manual_asks: list[dict] = []
        self.manual_exhausted: set[str] = set()

    # -- 수동(내가 agent) 모드용 헬퍼 -------------------------------------------
    def _customer_terms(self) -> list[str]:
        """지금까지의 고객 발화 전체 + 아직 안 보낸 다음 발화 = agent 가 들은 것."""
        convo = " ".join(t["user_message"] for t in self.turns)
        convo = f"{convo} {self.user_message}"
        return list(dict.fromkeys(_terms(convo)))

    def _bm25_top(self, terms: list[str], k: int) -> list[dict]:
        expression = " OR ".join(f'"{t}"' for t in terms[:60] if t)
        if not expression:
            return []
        rows = _diag().connection.execute(
            f"SELECT parent_asin FROM products WHERE products MATCH ? ORDER BY {_BM25_WEIGHTS} LIMIT ?",
            (expression, k),
        ).fetchall()
        return [{"parent_asin": str(r[0])} for r in rows]

    def advance(self, as_agent: dict | None = None) -> dict | None:
        """한 턴 진행.

        as_agent=None      → 선택된 agent 가 자동으로 respond (auto).
        as_agent={ask_attribute, message}
                           → 내가 agent 가 되어 이 질문을 던진다. ask_attribute 만 시뮬레이터에
                             전달되고(자연어 message 는 무시됨), 추천 top10 은 누적 대화 BM25 로 자동.
                             agent 객체는 상태 유지를 위해 계속 respond 호출하되 결과는 버린다.
        """
        if self.done:
            return None

        self.turn += 1
        try:
            response = self.agent.respond(self.session_id, self.user_message, self.turn, TOP_K)
        except Exception:
            response = {"message": "", "ask_attribute": None, "recommendations": []}
        if not isinstance(response, dict) or not isinstance(response.get("message"), str):
            response = {"message": "", "ask_attribute": None, "recommendations": []}

        manual = as_agent is not None
        if manual:
            ask_attribute = as_agent.get("ask_attribute") or None
            if isinstance(ask_attribute, str) and ask_attribute not in ALLOWED_ATTRIBUTES:
                ask_attribute = "other"
            typed = str(as_agent.get("message") or "").strip()
            agent_message = typed or f"(asked as agent — {ask_attribute or 'no question'})"
            state = self._manual_state(ask_attribute)
            terms = state["query_terms"]
            recos = self._bm25_top(terms, TOP_K)
            self.manual_asks.append({"turn": self.turn, "ask_attribute": ask_attribute, "message": typed})
        else:
            ask_attribute = response.get("ask_attribute")
            agent_message = response.get("message")
            state = agent_debug_state(self.agent, self.session_id)
            recos = response.get("recommendations")

        ranked = normalize_recommendations(recos, self.catalog_ids)
        target_rank = ranked.index(self.target) + 1 if self.target in ranked else None
        entry: dict = {
            "turn": self.turn,
            "user_message": self.user_message,
            "driver": "manual" if manual else self.agent_name,
            "agent_message": agent_message,
            "ask_attribute": ask_attribute,
            "recommendations": [product_brief(self.products, a) for a in ranked],
            "target_rank": target_rank,
            "revealed_so_far": sorted(self.disclosed),
            "agent_state": state,
        }
        if self.diagnostics:
            entry["diagnostics"] = self._diagnose(state)
        self.turns.append(entry)

        # hit / 종료 판정 — evaluate() 와 동일 순서
        if self.override_applied and self.target in ranked:
            self.best_rank = target_rank
            self.hit_turn = self.turn
            self.done = True
            return entry
        if self.turn >= MAX_TURNS:
            self.done = True
            return entry

        override = self.esample.get("behavior", {}).get("override") or {}
        if not self.override_applied and self.turn + 1 == int(override.get("turn", 3)):
            self.override_applied = True
            new_value = str(override.get("new_value", ""))
            if new_value:
                self.disclosed.add(new_value)
            self.user_message = str(override.get("message", "Actually, please ignore my earlier preference."))
            entry["next_is_override"] = True
        else:
            before = set(self.disclosed)
            self.user_message, self.boundary_used = customer_reply(
                self.esample, ask_attribute, self.disclosed, self.boundary_used
            )
            # 수동 모드: 물어봤는데 새 정보가 안 나온 속성 = 소진으로 기록
            if manual and ask_attribute and self.disclosed == before:
                self.manual_exhausted.add(ask_attribute)
        return entry

    def _manual_state(self, ask_attribute: str | None) -> dict:
        terms = self._customer_terms()
        return {
            "memory_kind": "manual — you are the agent (BM25 over the running conversation)",
            "query_scope": "full conversation",
            "query_terms": terms,
            "exhausted_attributes": sorted(self.manual_exhausted),
            "asked_so_far": [
                f"T{a['turn']}:{a['ask_attribute'] or '—'}" for a in self.manual_asks
            ] + [f"T{self.turn}:{ask_attribute or '—'}"],
        }

    def _diagnose(self, state: Any) -> dict:
        qterms: list[str] = []
        if isinstance(state, dict) and isinstance(state.get("query_terms"), list):
            qterms = [str(t) for t in state["query_terms"]]
        rank, pool = deep_rank(qterms, self.target) if qterms else (None, 0)

        tgt = self.products.get(self.target, {})
        title_terms = set(_terms(str(tgt.get("title") or "")))
        disclosed_terms: set[str] = set()
        for c in self.disclosed:
            disclosed_terms |= set(_terms(str(c)))
        cat_terms = set(_terms(self.category))
        title_only = sorted(title_terms - disclosed_terms - set(qterms) - cat_terms)
        return {
            "query_terms_used": qterms,
            "deep_target_rank": rank,
            "deep_pool_size": pool,
            "title_only_undisclosed": title_only,
        }

    def target_full(self) -> dict:
        p = self.products.get(self.target, {})
        return {
            k: p.get(k)
            for k in (
                "title", "features", "details", "description",
                "store", "price", "categories", "average_rating", "rating_number",
            )
        }

    def result(self) -> dict:
        return {
            "sample_id": self.sample["sample_id"],
            "scenario_type": self.sample["scenario_type"],
            "difficulty_bucket": self.sample.get("difficulty_bucket"),
            "category_bucket": self.sample.get("category_bucket"),
            "category": self.category,
            "target": product_brief(self.products, self.target),
            "target_full": self.target_full(),
            "intent_card": self.card,
            "behavior": self.behavior,
            "user_profile": self.sample.get("user_profile"),
            "turns": self.turns,
            "hit": self.hit_turn is not None,
            "first_hit_turn": self.hit_turn,
            "best_rank": self.best_rank,
            "reciprocal_rank": 0.0 if self.best_rank is None else 1.0 / self.best_rank,
        }


def trace_session(agent, sample, catalog_ids, categories, products, diagnostics: bool = False) -> dict:
    runner = SessionRunner(agent, sample, catalog_ids, categories, products, diagnostics)
    while not runner.done:
        runner.advance()
    return runner.result()


_SCORE_KEYS = ("sample_id", "scenario_type", "hit", "first_hit_turn", "best_rank", "reciprocal_rank")


def summarize(traces: list[dict]) -> dict:
    sessions = [{k: t[k] for k in _SCORE_KEYS} for t in traces]
    overall = metric_summary(sessions)
    efficiency = max(0.0, min(1.0, (11.0 - float(overall["mttc"])) / 10.0))
    technical_score = 0.50 * overall["hit_rate_at_10"] + 0.30 * overall["mrr"] + 0.20 * efficiency
    return {
        **overall,
        "efficiency": round(efficiency, 6),
        "technical_score": round(technical_score, 6),
    }


# ---------------------------------------------------------------------------
# 캐시된 카탈로그 인덱스 + agent 인스턴스 (server.py 가 재사용)
# ---------------------------------------------------------------------------
_catalog_cache: tuple | None = None
_agent_cache: dict[str, Any] = {}


def catalog() -> tuple[set, dict, dict]:
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = catalog_index(CATALOG)
    return _catalog_cache


def get_agent(name: str):
    if name not in _agent_cache:
        _agent_cache[name] = load_agent_class(name)(str(CATALOG))
    return _agent_cache[name]


def run_agent(name: str, samples: list[dict] | None = None, diagnostics: bool = False) -> dict:
    catalog_ids, categories, products = catalog()
    if samples is None:
        samples = load_jsonl(DATASET)
    agent = get_agent(name)
    traces = [trace_session(agent, s, catalog_ids, categories, products, diagnostics) for s in samples]
    return {"agent": name, "summary": summarize(traces), "traces": traces}


# ---------------------------------------------------------------------------
# 회귀 가드 — 우리 러너 == 공식 evaluate()
# ---------------------------------------------------------------------------
def regression_check() -> bool:
    from evaluator.local_evaluator import evaluate
    from starter.agent import Agent as OfficialAgent

    samples = load_jsonl(DATASET)
    catalog_ids, categories, products = catalog()
    official = evaluate(OfficialAgent(str(CATALOG)), samples, catalog_ids, categories, products)
    ours = run_agent("baseline", samples)

    by_id = {s["sample_id"]: s for s in official["sessions"]}
    mismatches = []
    for t in ours["traces"]:
        o = by_id[t["sample_id"]]
        if (o["hit"], o["first_hit_turn"], o["best_rank"]) != (t["hit"], t["first_hit_turn"], t["best_rank"]):
            mismatches.append((t["sample_id"], o, {k: t[k] for k in ("hit", "first_hit_turn", "best_rank")}))

    off_score = {
        "hit_rate_at_10": official["hit_rate_at_10"],
        "mrr": official["mrr"],
        "mttc": official["mttc"],
        "technical_score": official["recommended_technical_score"],
    }
    our_score = {k: ours["summary"][k] for k in ("hit_rate_at_10", "mrr", "mttc", "technical_score")}
    print("공식 :", json.dumps(off_score))
    print("러너 :", json.dumps(our_score))
    if mismatches:
        print(f"\n❌ 세션 불일치 {len(mismatches)}건:")
        for sid, o, ours_ in mismatches[:10]:
            print(f"  {sid}  공식={o['hit'], o['first_hit_turn'], o['best_rank']}  러너={tuple(ours_.values())}")
        return False
    if off_score != our_score:
        print("\n❌ 집계 점수 불일치")
        return False
    print("\n✅ 200세션 전부 일치")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="playground 러너")
    parser.add_argument("--check", action="store_true", help="공식 evaluate() 와 회귀 대조")
    parser.add_argument("--agent", help="한 버전 전체 실행 후 요약 출력")
    parser.add_argument("--list", action="store_true", help="사용 가능한 agent 버전 나열")
    args = parser.parse_args()

    if args.list:
        print("\n".join(available_agents()))
        return
    if args.check:
        raise SystemExit(0 if regression_check() else 1)
    if args.agent:
        result = run_agent(args.agent)
        print(json.dumps({"agent": args.agent, **result["summary"]}, indent=2))
        return
    parser.print_help()


if __name__ == "__main__":
    main()
