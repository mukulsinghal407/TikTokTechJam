# 데이터셋 형식 / Dataset format

`evaluator/bench.py` (및 공식 `evaluator/local_evaluator.py`) 가 읽는 세션 데이터셋의 형식.
The format of the session dataset read by `evaluator/bench.py` (and the official `evaluator/local_evaluator.py`).

---

## 파일 / File

JSON Lines — 한 줄에 세션 하나. `data/public_set.jsonl` 와 동일.
JSON Lines — one session per line. Same as `data/public_set.jsonl`.

새로 만든 세트는 `data/` 아래 아무 이름으로 두고 `--dataset` 으로 지정.
Put a new set anywhere under `data/` and pass it with `--dataset`.

```bash
python3 -m evaluator.bench starter.agent_v2_8 --dataset data/holdout_set.jsonl
python3 -m evaluator.bench starter.agent_v2_8 \
    --dataset data/public_set.jsonl --dataset data/holdout_set.jsonl   # 둘 다 / both
```

---

## 세션 한 줄의 필드 / Fields of one session line

### 필수 / Required

| 필드 / field | 설명 / meaning |
|---|---|
| `ground_truth.parent_asin` | 정답 상품 ID. **`data/catalog.jsonl` 에 반드시 존재해야 함** (없으면 채점 불가/크래시). / The answer product ID. **Must exist in `data/catalog.jsonl`** (otherwise unscoreable / crash). |
| `scenario_type` | `buying` / `browsing` / `intent_override` / `boundary` 중 하나. 시나리오별 지표 분리에 쓰임. / one of these four. Used to split the per-scenario metrics. |
| `sample_id` | 세션 고유 문자열. 시뮬레이터 RNG 시드로 쓰이므로 결정론적 재현을 위해 필요. / a unique string. Used as the simulator RNG seed, so it is needed for deterministic reproduction. |
| `user_profile` | dict. `Agent.reset` 에 그대로 전달. 익명 집계만 (직접 식별자·리뷰·타임스탬프 없음). / a dict, passed straight to `Agent.reset`. Anonymized aggregates only (no direct identifiers, reviews, or timestamps). |

### 선택 / Optional

| 필드 / field | 설명 / meaning |
|---|---|
| `intent_card` + `behavior` | 둘 다 있으면 시뮬레이터가 이걸 그대로 씀. 없으면 카탈로그의 타깃 메타데이터에서 자동 합성 (`intent_card(product)` + `behavior_for`). 보통은 넣지 않는다. / if both are present the simulator uses them verbatim; otherwise it synthesizes them from the target's catalog metadata. Usually omitted. |
| `category_bucket`, `difficulty_bucket` | 메타데이터. 채점에 안 쓰임. / metadata, not used in scoring. |

### `user_profile` 안 (공식 세트 기준) / Inside `user_profile` (per the official set)

`preference_tags` (list), `summary` (str), `purchase_frequency` (str), `average_prior_rating` (num), `rating_style` (str).
에이전트가 실제로 읽는 건 `preference_tags` 와 `summary` 뿐. `user_profile` 을 `{}` 로 둬도 크래시는 안 나지만 개인화 신호가 사라짐.
The agent only actually reads `preference_tags` and `summary`. `user_profile` may be `{}` (no crash) but then there is no personalization signal.

---

## 시나리오 믹스 / Scenario mix

공식 스펙: Buying 40% / Browsing 40% / Intent Override 15% / Boundary 5% (양쪽 split 동일).
Official spec: Buying 40% / Browsing 40% / Intent Override 15% / Boundary 5% (same for both splits).

새 세트가 다른 믹스여도 `bench` 는 돈다 — 다만 시나리오별 N 이 작으면 그 지표는 노이즈.
`bench` runs with any mix — but if a scenario's N is small, its metrics are noisy.

---

## 시뮬레이터가 세션에서 하는 일 (요약) / What the simulator does with a session (summary)

1. `reset(session_id, user_profile)` 호출. / calls `reset(session_id, user_profile)`.
2. 시나리오별 첫 메시지 생성. buying 은 하드 제약 1개를 조기 공개, browsing 은 모호하게 시작. / builds a scenario-dependent first message. Buying discloses one hard constraint early; Browsing starts vague.
3. 매 턴 `respond(...)` 호출 → `recommendations` 의 첫 10개 유효·유니크 `parent_asin` 을 채점. / calls `respond(...)` each turn → scores the first 10 valid unique `parent_asin` values.
4. `ask_attribute` enum 에 맞춰서만 제약을 조금씩 공개 (자연어 `message` 는 무시). / discloses constraints only when `ask_attribute` matches, a little at a time (the natural-language `message` is ignored).
5. Intent Override 는 3~4턴에 새 intent 를 보내고, 그 전에는 타깃이 top-10 이어도 히트로 안 침. / Intent Override sends a new intent on turn 3–4; before that, a target in top-10 does not count as a hit.
6. 타깃이 top-10 에 뜨거나 턴 10 에 도달하면 세션 종료. / the session ends on a top-10 hit or at turn 10.

제약은 타깃 상품의 `features` / `details` 필드에서 뽑힌다 (그래서 BM25 features 가중이 중요). 조직자가 자연어 패러프레이징을 추가할 수 있으나 정답 판정은 항상 exact code match.
Constraints are drawn from the target product's `features` / `details` fields (hence BM25 features weighting matters). The organizer may add NL paraphrasing, but correctness is always an exact code match.

---

## 지표 / Metrics

```
HitRate@10 = 성공 세션 / N
MRR        = mean(1 / target_rank), miss = 0
MTTC       = mean(first_hit_turn), miss = 11
Efficiency = clip((11 - MTTC) / 10, 0, 1)
TechnicalScore = 0.50·HitRate@10 + 0.30·MRR + 0.20·Efficiency
```

`TechnicalScore` 는 심사 Technical Execution(35%) 의 objective input 1개일 뿐, 심사 전체가 아님.
`TechnicalScore` is only one objective input into the Technical Execution axis (35% of judging), not the whole thing.

---

## overfit 체크 용도 / Using this for an overfit check

새로 만든 세트를 holdout 으로 쓰면:
Using a new set as a holdout:

```bash
python3 -m evaluator.bench starter.agent_v2_8 \
    --dataset data/public_set.jsonl --dataset data/holdout_set.jsonl
```

두 데이터셋의 지표 차이를 본다. `agent_v2_8` 의 `feat_mult`, sticky 임계, yield 관련 상수는 전부 public 200 실측 기반이므로, holdout 에서 크게 떨어지면 그만큼 overfit.
Compare the metrics across the two datasets. `agent_v2_8`'s `feat_mult`, the sticky threshold, and the yield-related constants are all derived from the public 200, so a large drop on the holdout is that much overfit.
