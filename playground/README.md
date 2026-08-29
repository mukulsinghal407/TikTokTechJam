# playground

A local tool for **watching how a shopping agent behaves per session** — what it
retrieves, what it remembers, and how that changes as we iterate on the agent.

Not part of the competition score (UI is out of scope). Official numbers come only
from `python -m evaluator.local_evaluator` at the repo root.

## Layout

```
playground/
  server.py          Flask app  →  cd playground && python server.py  →  :5050
  runner.py          replays the official evaluate() loop one turn at a time
  agents/
    baseline.py      the repo-root official starter, instrumented (~12.5% Hit@10)
    damin_start.py   spare improved baseline: cumulative BM25 + attribute
                     question ladder + light profile re-ranking (~86.5%)
    <vN>.py          add your own hypotheses here
  static/index.html  the UI
  setup.sh           fetches data/catalog.jsonl into the repo root
```

`runner.py` / `server.py` add the **repo root** to `sys.path` and import the
participant kit that already lives there (`evaluator/`, `starter/`, `data/`) — no
copy, nothing duplicated.

## Run

```bash
cd playground
pip install -r requirements.txt
bash setup.sh                 # downloads data/catalog.jsonl once (~19MB)
python server.py              # http://127.0.0.1:5050
HOST=0.0.0.0 python server.py # share on the same Wi-Fi
```

Two ways to drive each turn:
- **Run the selected agent** — the agent produces `ask_attribute` + the top-10.
- **Ask as the agent** — you pick `ask_attribute` and ask; the top-10 is BM25 over
  the accumulated conversation. Mix the two turn by turn.

## The sidebar

1. **What user data is this?** — what the agent sees (anonymized profile + customer
   messages) vs. what only the evaluator sees (intent_card, target product).
2. **How is the agent behaving this session?** — recomputed every turn: query terms,
   exhausted attributes, target-title words never disclosed, full BM25 rank.
3. **About this playground.**

## Adding an agent version

Drop a file in `agents/` exposing an `Agent` class with the official API
(`__init__(catalog_path)`, `reset(session_id, user_profile)`,
`respond(session_id, user_message, turn, top_k)`). Optional:
- `LABEL = "nice-name"` — dropdown display name (the file name is the id).
- `debug_state(session_id) -> dict` — whatever the agent tracks; the runner forwards
  it to sidebar Part 2. Suggested keys: `memory_kind`, `query_scope`, `query_terms`,
  `exhausted_attributes`.

### Testing the repo-root agent

Once the team has a real agent at the repo root, add a shim, e.g. `agents/main.py`:

```python
from starter.agent import Agent   # or wherever the team's agent ends up
LABEL = "main"
```

It then shows up in the dropdown next to `baseline` and `damin-start`.

## Checks

```bash
python runner.py --list             # agent versions
python runner.py --agent baseline    # run one version over all 200 sessions → summary
python runner.py --check             # runner == official evaluate() on all 200 (hit/rank/score)
```

`--check` must pass whenever `runner.py` changes.
