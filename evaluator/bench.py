"""bench — 임의 Agent 모듈을 임의 데이터셋(들)로 채점하고 전체 분해 결과를 출력.
bench — score an arbitrary Agent module against arbitrary dataset(s) and print a full breakdown.

공식 `evaluator.local_evaluator.evaluate` 를 그대로 호출한다 (포크 아님).
Calls `evaluator.local_evaluator.evaluate` verbatim (not a fork).

사용 / Usage:
  # 한 데이터셋 / one dataset
  python3 -m evaluator.bench starter.agent_v2_8

  # 여러 데이터셋 (public + 새로 만든 holdout) / several datasets
  python3 -m evaluator.bench starter.agent_v2_8 \
      --dataset data/public_set.jsonl --dataset data/holdout_set.jsonl

  # 두 에이전트 나란히 비교 / compare two agents side by side
  python3 -m evaluator.bench starter.agent_v2_8 --vs starter.agent_v1

출력 / Output:
  - 전체 TS / HitRate@10 / MRR / MTTC / Efficiency
    overall TS / HitRate@10 / MRR / MTTC / Efficiency
  - 시나리오별 (buying / browsing / intent_override / boundary) HR·MRR·MTTC
    per-scenario (buying / browsing / intent_override / boundary) HR / MRR / MTTC
  - rank 히스토그램 (1 / 2-3 / 4-5 / 6-10 / miss)
    rank histogram (1 / 2-3 / 4-5 / 6-10 / miss)
  - turn 히스토그램 (first_hit_turn)
    turn histogram (first_hit_turn)
  - miss 세션 목록
    the list of missed sessions

데이터셋 형식은 docs/dataset_format.md 참조.
See docs/dataset_format.md for the dataset format.
"""
from __future__ import annotations

import argparse
import collections
import importlib
import json
import statistics
from pathlib import Path

from evaluator.local_evaluator import MAX_TURNS, catalog_index, evaluate, load_jsonl

_SCENARIOS = ("buying", "browsing", "intent_override", "boundary")


def _load_agent(module_path: str, catalog_path: str):
    """모듈 경로에서 Agent 클래스를 만든다. / Instantiate the Agent class from a module path."""
    return importlib.import_module(module_path).Agent(catalog_path)


def _sanity_check(samples: list[dict], catalog_ids: set[str]) -> list[str]:
    """데이터셋이 이 카탈로그로 채점 가능한지 검사. 문제 목록을 돌려준다.
    Check the dataset is scoreable against this catalog. Returns a list of problems."""
    problems: list[str] = []
    missing = [s.get("sample_id", "?") for s in samples
              if str(s.get("ground_truth", {}).get("parent_asin", "")) not in catalog_ids]
    if missing:
        problems.append(
            f"{len(missing)}개 세션의 ground_truth parent_asin 이 카탈로그에 없음 (채점 불가/크래시). "
            f"예: {missing[:5]}  /  {len(missing)} sessions have a ground_truth parent_asin not in the "
            f"catalog (unscoreable / will crash). e.g. {missing[:5]}"
        )
    bad_scenario = sorted({str(s.get("scenario_type")) for s in samples} - set(_SCENARIOS))
    if bad_scenario:
        problems.append(
            f"알 수 없는 scenario_type: {bad_scenario} (허용: {list(_SCENARIOS)})  /  "
            f"unknown scenario_type: {bad_scenario} (allowed: {list(_SCENARIOS)})"
        )
    no_id = sum(1 for s in samples if not s.get("sample_id"))
    if no_id:
        problems.append(
            f"{no_id}개 세션에 sample_id 없음 (RNG 시드가 비결정적이 됨)  /  "
            f"{no_id} sessions have no sample_id (RNG seed becomes non-deterministic)"
        )
    return problems


def _summary(result: dict) -> str:
    lines = [
        f"  TS {result['recommended_technical_score']:.4f}   "
        f"HR@10 {result['hit_rate_at_10']:.3f}   "
        f"MRR {result['mrr']:.4f}   "
        f"MTTC {result['mttc']:.2f}   "
        f"Eff {result['efficiency']:.3f}",
        "",
        "  시나리오 / scenario   N     HR     MRR    MTTC",
    ]
    by = result["scenario_metrics"]
    for name in _SCENARIOS:
        m = by.get(name)
        if not m:
            continue
        lines.append(f"  {name:18s} {m['sample_count']:3d}  {m['hit_rate_at_10']:.3f}  "
                     f"{m['mrr']:.3f}  {m['mttc']:.2f}")

    sessions = result["sessions"]
    n = len(sessions)
    rank = collections.Counter()
    for s in sessions:
        if not s["hit"]:
            rank["miss"] += 1
        else:
            r = s["best_rank"]
            rank["1" if r == 1 else "2-3" if r <= 3 else "4-5" if r <= 5 else "6-10"] += 1
    lines.append("")
    lines.append("  rank 분포 / rank distribution:")
    for k in ("1", "2-3", "4-5", "6-10", "miss"):
        lines.append(f"    rank {k:5s} {rank[k]:4d}  ({rank[k] / n * 100:.0f}%)")

    turn = collections.Counter()
    for s in sessions:
        t = s["first_hit_turn"]
        turn["miss" if t is None else str(t) if t <= 3 else "4-5" if t <= 5 else "6-10"] += 1
    lines.append("")
    lines.append("  turn 분포 / turn distribution (first_hit_turn):")
    for k in ("1", "2", "3", "4-5", "6-10", "miss"):
        lines.append(f"    turn {k:5s} {turn[k]:4d}  ({turn[k] / n * 100:.0f}%)")

    misses = [(s["sample_id"], s["scenario_type"]) for s in sessions if not s["hit"]]
    lines.append("")
    if misses:
        lines.append(f"  miss {len(misses)}건 / {len(misses)} misses:")
        for sid, sc in misses:
            lines.append(f"    {sid}  ({sc})")
    else:
        lines.append("  miss 0건 — HitRate@10 = 100% / 0 misses — HitRate@10 = 100%")
    return "\n".join(lines)


def _run_one(module_path: str, dataset_path: str, catalog_path: str,
             catalog_index_cache: tuple) -> dict:
    catalog_ids, categories, products = catalog_index_cache
    samples = load_jsonl(dataset_path)
    problems = _sanity_check(samples, catalog_ids)
    for p in problems:
        print(f"  ⚠️  {p}")
    mix = collections.Counter(s.get("scenario_type") for s in samples)
    print(f"  세션 {len(samples)}개 / {len(samples)} sessions   "
          f"mix: {dict(mix)}")
    agent = _load_agent(module_path, catalog_path)
    return evaluate(agent, samples, catalog_ids, categories, products)


def main() -> None:
    parser = argparse.ArgumentParser(description="score an Agent module against dataset(s)")
    parser.add_argument("module", help="Agent 를 담은 모듈 / module holding the Agent (e.g. starter.agent_v2_8)")
    parser.add_argument("--dataset", action="append", default=None,
                        help="데이터셋 파일 (반복 가능) / dataset file (repeatable). "
                             "기본 / default: data/public_set.jsonl")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--vs", default=None,
                        help="나란히 비교할 두 번째 Agent 모듈 / second Agent module to compare against")
    parser.add_argument("--output", default=None, help="첫 데이터셋 결과 JSON 저장 경로 / path to save the first dataset's result JSON")
    args = parser.parse_args()

    datasets = args.dataset or ["data/public_set.jsonl"]
    for d in datasets:
        if not Path(d).exists():
            raise SystemExit(f"데이터셋 없음 / dataset not found: {d}")

    print(f"카탈로그 색인 중 / indexing catalog: {args.catalog}")
    cache = catalog_index(args.catalog)

    modules = [args.module] + ([args.vs] if args.vs else [])
    first_result: dict | None = None

    for dataset_path in datasets:
        print("\n" + "=" * 74)
        print(f"데이터셋 / dataset: {dataset_path}")
        print("=" * 74)
        for module_path in modules:
            print(f"\n── {module_path} ──")
            result = _run_one(module_path, dataset_path, args.catalog, cache)
            print(_summary(result))
            if first_result is None:
                first_result = result

    if args.output and first_result is not None:
        Path(args.output).write_text(json.dumps(first_result, indent=2) + "\n", encoding="utf-8")
        print(f"\n저장 / saved: {args.output}")


if __name__ == "__main__":
    main()
