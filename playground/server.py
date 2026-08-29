"""playground 로컬 서버.

선택한 agent 버전(`agents/*.py`)을 실제로 돌리고, 공식 시뮬레이터를 한 턴씩 재생한다.
카탈로그 인덱스는 기동 시 1회 빌드하고 재사용.

실행 (playground/ 안에서):
    pip install -r requirements.txt
    bash setup.sh                  # 레포 루트 data/catalog.jsonl 내려받기 (최초 1회)
    python server.py               # http://127.0.0.1:5050
    HOST=0.0.0.0 python server.py   # 같은 WiFi 의 다른 사람과 공유
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))  # 레포 루트: evaluator/, starter/

from flask import Flask, jsonify, request, send_from_directory

import runner
from evaluator.local_evaluator import load_jsonl

HERE = Path(__file__).resolve().parent
SAMPLES: dict[str, dict] = {}
SESSIONS: dict[str, runner.SessionRunner] = {}

app = Flask(__name__, static_folder=str(HERE / "static"))


def boot() -> None:
    if not runner.CATALOG.exists():
        sys.exit(f"카탈로그가 없습니다: {runner.CATALOG}\n먼저 `bash setup.sh` 를 실행하세요.")
    print("카탈로그 인덱스 빌드 중... (~25초, agent + 진단용)")
    runner.catalog()
    runner.get_agent("baseline")
    runner._diag()
    for s in load_jsonl(runner.DATASET):
        SAMPLES[s["sample_id"]] = s
    print(f"준비 완료: 세션 {len(SAMPLES)}개, agent 버전 {runner.available_agents()}")


def part1(sr: runner.SessionRunner) -> dict:
    """Part 1 — 어떤 유저 데이터인가. agent 가 보는 것 / evaluator 만 보는 것."""
    override = (sr.behavior or {}).get("override")
    return {
        "agent_visible": {
            "user_profile": sr.sample.get("user_profile"),
            "note": "The agent sees only this profile plus the customer messages so far.",
        },
        "evaluator_only": {
            "scenario_type": sr.sample["scenario_type"],
            "difficulty_bucket": sr.sample.get("difficulty_bucket"),
            "intent_card": sr.card,
            "override": override,
            "target": {**sr.target_full(), "parent_asin": sr.target},
            "note": "intent_card is regex-mined from the target product's features/details. The agent never sees it.",
        },
    }


def payload(token: str) -> dict:
    sr = SESSIONS[token]
    return {
        "token": token,
        "agent": sr.agent_name,
        "sample_id": sr.sample["sample_id"],
        "scenario": sr.sample["scenario_type"],
        "difficulty": sr.sample.get("difficulty_bucket"),
        "category": sr.category,
        "done": sr.done,
        "hit_turn": sr.hit_turn,
        "best_rank": sr.best_rank,
        "turns": sr.turns,
        "pending_user_message": None if sr.done else sr.user_message,
        "part1": part1(sr),
    }


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/agents")
def api_agents():
    return jsonify([{"id": n, "label": runner.agent_label(n)} for n in runner.available_agents()])


@app.get("/api/sessions")
def api_sessions():
    _, categories, products = runner.catalog()
    out = []
    for sid, s in SAMPLES.items():
        target = str(s["ground_truth"]["parent_asin"])
        out.append({
            "sample_id": sid,
            "scenario": s["scenario_type"],
            "difficulty": s.get("difficulty_bucket"),
            "category": runner.coarse_category(categories.get(target, [])),
            "target_title": (products.get(target, {}).get("title") or "")[:90],
        })
    return jsonify(out)


@app.post("/api/start")
def api_start():
    body = request.json or {}
    sample_id = body.get("sample_id")
    agent_name = body.get("agent") or "baseline"
    if sample_id not in SAMPLES:
        return jsonify({"error": "unknown sample_id"}), 400
    if agent_name not in runner.available_agents():
        return jsonify({"error": "unknown agent"}), 400

    catalog_ids, categories, products = runner.catalog()
    agent = runner.get_agent(agent_name)
    sr = runner.SessionRunner(
        agent, SAMPLES[sample_id], catalog_ids, categories, products,
        diagnostics=True, agent_name=runner.agent_label(agent_name),
    )
    token = secrets.token_hex(8)
    SESSIONS[token] = sr
    sr.advance()  # 턴 1 자동
    return jsonify(payload(token))


@app.post("/api/next")
def api_next():
    body = request.json or {}
    token = body.get("token")
    if token not in SESSIONS:
        return jsonify({"error": "unknown token"}), 400
    sr = SESSIONS[token]
    if sr.done:
        return jsonify(payload(token))
    if body.get("mode") == "agent":
        sr.advance(as_agent={
            "ask_attribute": body.get("ask_attribute"),
            "message": body.get("message") or "",
        })
    else:
        sr.advance()
    return jsonify(payload(token))


boot()

if __name__ == "__main__":
    # Agent 의 SQLite 인메모리 연결은 스레드 고정 → 단일 스레드 서빙 (요청은 순차 처리).
    # 같은 WiFi 의 다른 사람과 공유하려면 HOST=0.0.0.0 으로 실행.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5050))
    if host == "0.0.0.0":
        print(f"⚠️  같은 네트워크의 누구나 접속 가능: http://<이 컴퓨터 IP>:{port}")
    app.run(host=host, port=port, debug=False, threaded=False)
