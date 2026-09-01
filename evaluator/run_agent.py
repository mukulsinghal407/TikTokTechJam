"""Score an Agent from any module with the official evaluator.evaluate.

Lets you A/B a candidate implementation without editing `starter/agent.py`.

usage:  python3 -m evaluator.run_agent starter.agent --output results.json
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("module", help="module path holding the Agent class "
                                       "(e.g. starter.agent)")
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
