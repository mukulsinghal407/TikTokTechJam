#!/usr/bin/env bash
# 레포 루트 data/ 에 catalog.jsonl 을 내려받는다 (~19MB). 최초 1회만.
# public_set.jsonl 은 이미 레포에 있고, catalog.jsonl 은 .gitignore 대상.
set -euo pipefail
cd "$(dirname "$0")/.."   # 레포 루트
mkdir -p data

KIT_REL="https://github.com/TechJam2026/techjam-conversational-search/releases/download/participant-kit"

if [ ! -f data/catalog.jsonl ]; then
  echo "catalog.jsonl.gz 내려받는 중 (~19MB)..."
  curl -fL -o data/catalog.jsonl.gz "$KIT_REL/catalog.jsonl.gz"
  gzip -dk data/catalog.jsonl.gz
  rm -f data/catalog.jsonl.gz
fi

echo "완료: catalog $(wc -l < data/catalog.jsonl) 행, sessions $(wc -l < data/public_set.jsonl) 개"
echo
echo "공식 평가:  python -m evaluator.local_evaluator      # 레포 루트에서. Hit@10 12.5%"
echo "회귀 가드:  python playground/runner.py --check"
