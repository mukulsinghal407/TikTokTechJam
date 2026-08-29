"""임의 모듈의 Agent 를 공식 evaluator.evaluate 로 채점하는 러너.
Runner that scores an Agent from any module with the official evaluator.evaluate.

`starter/agent.py` 를 덮어쓰지 않고 후보 버전(agent_v1 등)을 A/B 하려고 둔다.
Lets us A/B a candidate version (agent_v1, ...) without overwriting `starter/agent.py`.

사용 / usage:  python3 -m evaluator.run_agent starter.agent_v1 --output results_v1.json
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", help="Agent 를 담은 모듈 경로 / module path holding the Agent class "
                                       "(예 / e.g. starter.agent_v1)")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output", default="results.json")
    args = parser.parse_args()

    agent_cls = importlib.import_module(args.module).Agent
    samples = load_jsonl(args.dataset)
    catalog_ids, categories, products = catalog_index(args.catalog)
    result = evaluate(agent_cls(args.catalog), samples, catalog_ids, categories, products)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "sessions"}, indent=2))


if __name__ == "__main__":
    main()
