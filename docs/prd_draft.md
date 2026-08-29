# PRD — Conversational Shopping Agent

> 한/영 병기 문서. 각 섹션은 **한국어 먼저, 그 아래 English**.
> Bilingual doc. Each section is **Korean first, English below**.

> 상태: **v0.3 (2026-08-29)** · 이터레이션 1 완료 (`starter/agent_v1.py`, TS 0.820) · 베이스라인: `starter/agent.py` (TS 0.107)
> 참고 구현: `playground/agents/damin_start.py` (TS 0.724, 개선 방향 레퍼런스)
> **이 문서가 정량·정성 두 트랙의 단일 소스**다. 정성 트랙 별도 PRD(`tiktokhackerthon2026_draft/docs/PRD.md`, v0.2)를 §4.5~4.7로 흡수 (decision_log D8).
> 선택의 이유·실측 로그는 `docs/decision_log.md` (D1~D8).
>
> Status: **v0.3 (2026-08-29)** · iteration 1 done (`starter/agent_v1.py`, TS 0.820) · baseline `starter/agent.py` (TS 0.107).
> Reference build: `playground/agents/damin_start.py` (TS 0.724, direction reference).
> **This is the single source for both the quantitative and qualitative tracks.** The separate
> qualitative-track PRD (`tiktokhackerthon2026_draft/docs/PRD.md`, v0.2) is absorbed into §4.5–4.7 (decision_log D8).
> Rationale and measurement log live in `docs/decision_log.md` (D1–D8).

---

## 1. 배경 & 문제 정의 / Background & problem

`local_evaluator.py`는 **결정론적 시뮬레이터**다. 숨은 타깃 상품 1개를 다중 턴 대화로 찾아내며,
빨리·높은 순위로 찾을수록 점수가 높다. 시뮬레이터의 특성:

- 정답은 `parent_asin` **exact match**. 의미 판정 없음.
- 고객 메시지는 타깃 상품의 메타데이터에서 규칙적으로 생성된다 (`intent_card`).
- 제약은 **에이전트가 맞는 속성을 물어봐야만** 조금씩 공개된다 (`customer_reply`).
- 시나리오 믹스 고정: Buying 40% / Browsing 40% / Intent Override 15% / Boundary 5%.

즉 개선의 초점은 "범용 검색 성능"이 아니라 **이 시뮬레이터의 정보 공개 규칙에 맞춘 질문·상태관리·랭킹 설계**다.

**부차 목표 (팀 서사)**: 이 에이전트의 질문 전략이 해커톤 채점용 편법이 아니라 **실제 커머스 서비스에서도
성립하는 clarification policy**여야 한다. 심사 가중치가 Technical Execution 35 / Innovation 20 / Impact 20 /
Feasibility 15 / Presentation 10 이므로, evaluator 점수만 올리는 선택은 나머지 65%에서 손해다 (decision_log D3·D4).

**EN**

`local_evaluator.py` is a **deterministic simulator**. The agent must find one hidden target product through
a multi-turn dialogue; scoring rewards finding it early and highly ranked. Simulator characteristics:

- The answer is an **exact `parent_asin` match**. No semantic judgement.
- Customer messages are generated deterministically from the target product's metadata (`intent_card`).
- Constraints are disclosed a little at a time, **only when the agent asks the matching attribute** (`customer_reply`).
- Fixed scenario mix: Buying 40% / Browsing 40% / Intent Override 15% / Boundary 5%.

So the focus is not "general search quality" but **question, state-management, and ranking design fitted to this
simulator's disclosure rules**.

**Secondary goal (team narrative)**: the questioning strategy must be a **clarification policy that also holds up
in a real commerce service**, not a scoring hack. Judging weights are Technical Execution 35 / Innovation 20 /
Impact 20 / Feasibility 15 / Presentation 10, so choices that only raise the evaluator score lose on the other 65% (decision_log D3·D4).

---

## 2. 현재 상태 / Current state (public_set 200, measured)

| 지표 / metric | `starter` (baseline) | `damin_start` (ref) | Oracle (현 가중치 / current weights)¹ |
|---|---|---|---|
| TechnicalScore | 0.107 | 0.724 | — |
| HitRate@10 | 0.125 | 0.865 | 0.870 |
| MRR | 0.068 | 0.520 | 0.726 |
| MTTC | 9.81 | 4.20 | — |
| Efficiency | 0.119 | 0.680 | — |

¹ Oracle = 모든 제약 + 카테고리를 1턴에 완벽 공개했다고 가정. **현재 BM25 가중치 기준이며 고정 상한이 아니다** —
BM25 가중치·랭킹은 evaluator가 아니라 우리 코드에 있고 H1에서 개선 대상. 이 0.87 / 0.73은 "오늘의 랭킹으로 완벽 추출했을 때"의 값.

> **주의 — public 200에 overfit 금지.** BM25 가중치·재랭킹을 이 200세션 점수에 맞춰 소수점까지 쥐어짜면
> private set에서 무너진다. H1은 (1) train/holdout 분할 검증, (2) 큰 폭의 견고한 개선만 채택,
> (3) 시나리오 4종 모두 회귀 없을 때만 반영 — 이 3원칙.

**시나리오별 (`damin_start`)**: Buying HR 0.86 / Browsing 0.86 / Intent Override 0.87 / Boundary 0.90 — 고름.

**EN**

¹ Oracle = assume every constraint + category is perfectly disclosed on turn 1. **This is measured with the
current BM25 weights and is not a fixed ceiling** — the weights and ranking live in our code, not the evaluator,
and are H1 targets. The 0.87 / 0.73 are just "what today's ranking gets with perfect extraction".

> **Warning — do not overfit to public 200.** Squeezing BM25 weights / rerank to the last decimal on these 200
> sessions collapses on the private set. H1 follows 3 rules: (1) validate on a train/holdout split, (2) accept
> only large, robust gains, (3) apply only when there is no regression across all 4 scenarios.

**By scenario (`damin_start`)**: Buying HR 0.86 / Browsing 0.86 / Intent Override 0.87 / Boundary 0.90 — even.

---

## 3. 측정된 사실 / Measured facts (design basis)

### F1. budget/price는 "제약으로는" 존재하지 않는다 / budget/price does not exist "as a constraint"

- 카탈로그: price 10,527 / 50,000 (21%). 200개 타깃 중 **178개에 price 존재**.
- 그러나 `intent_card`가 `"budget around $X"`를 후보 **맨 뒤**에 넣고, feature·details 후보가 늘 4개 이상이라
  hard/soft 제약(`cleaned[:4]`)에 **한 번도 들어가지 않는다** → 200세션 모두 budget 제약 0건.
- 시사점: `ask_attribute="budget"`은 매 턴 허탕. price는 재랭킹 신호로만 후보이며 타깃 가격 미공개라 근거 약함.

**EN** — Catalog: price on 10,527 / 50,000 (21%); 178 / 200 targets have a price. But `intent_card` appends
`"budget around $X"` **last**, and there are always ≥4 feature/details candidates, so it never reaches the
hard/soft constraints (`cleaned[:4]`) → 0 budget constraints across all 200 sessions. Implication:
`ask_attribute="budget"` always whiffs; price is only a possible rerank signal and weak (target price undisclosed).

### F2. 추출은 (현재 랭킹 기준) 천장에 가깝다 / extraction is near the ceiling (at the current ranking)

- 현재 BM25 가중치로 모든 제약을 완벽 공개하면: HitRate@10 = **0.870**, MRR = **0.726**, rank-1 = **64%**.
- **이 0.87은 고정 상한이 아니다.** 랭킹은 우리 코드에 있고 고칠 수 있다(H1).
- `damin_start` HitRate 0.865 ≈ 이 값 → **현재 랭킹 하에서는** 적응형 질문으로 HitRate를 더 못 올린다.
  질문 개선의 실익은 **MTTC 단축**(→ Efficiency·MRR).
- 두 갈래 헤드룸: **(a) 턴 비용 회수** — Oracle MRR 0.726 vs 현재 0.520. **(b) 랭킹 자체 개선** — rank-1 64%.
- **단 이 0.87은 "1회 top-10" 기준이다.** 세션은 10턴 돌고 매 턴 히트를 집계하므로, R7(매 턴 다른 후보 노출)을
  쓰면 "타깃이 어느 턴이든 top-10에 뜨는가"로 바뀐다 → 실효 상한이 올라간다. v1 HR 0.97이 그 결과.
  남은 진짜 헤드룸은 **MRR**(rank-1 비율).

**EN** — With current BM25 weights, perfect disclosure of all constraints gives HitRate@10 **0.870**, MRR
**0.726**, rank-1 **64%**. **This 0.87 is not a fixed ceiling** — the ranking is in our code (H1). `damin_start`
HitRate 0.865 ≈ this → **at the current ranking**, adaptive questioning cannot raise HitRate further; the payoff
of question tuning is **shorter MTTC** (→ Efficiency, MRR). Two headroom lanes: **(a) recover turn cost** (Oracle
MRR 0.726 vs 0.520), **(b) improve the ranking itself** (rank-1 64%). **But 0.87 is a "one-shot top-10" number.**
The session runs 10 turns and scores a hit on any turn, so with R7 (a different candidate set each turn) the game
becomes "does the target land in top-10 on *any* turn" → the effective ceiling rises. v1 HR 0.97 is the result.
The real remaining headroom is **MRR** (rank-1 rate).

### F3. 동의어 갭은 이 evaluator의 병목이 아니다 / the synonym gap is not the bottleneck here

- 쿼리 term의 **99%(중앙값 100%, 최소 86%)가 타깃 문서에 그대로 존재.** <50%인 세션 0개.
- 시뮬레이터가 타깃 메타데이터의 **원문 단어를 인용**하기 때문.
- 시사점: dense/semantic 검색의 목적은 `"sneakers"↔"athletic shoe"` 브리징이 **아니라** 같은 단어를 공유하는
  수천 개 문서 사이의 **판별력**이다.
- **주의**: 이 99%는 public + 현재 시뮬레이터 기준. 스펙은 조직자가 NL 패러프레이징을 추가할 수 있다고 명시 →
  **private set에서는 이 전제가 깨질 수 있다.** 대비책은 H7 (낮은 우선순위 파킹).

**EN** — **99% of query terms (median 100%, min 86%) appear verbatim in the target document**; 0 sessions below
50%. Because the simulator **quotes the target metadata's own words**. Implication: the purpose of dense/semantic
search here is **not** `"sneakers"↔"athletic shoe"` bridging but **discrimination** among the thousands of
documents that share the same words. **Caveat**: this 99% is on public + the current simulator; the spec says the
organizer may add NL paraphrasing → **this premise may break on the private set.** Hedge = H7 (low-priority parked).

### F4. Intent Override: override 턴 이전의 히트는 점수로 인정되지 않는다 / pre-override hits do not score

다른 시나리오(Buying/Browsing/Boundary)는 타깃이 top-10에 뜨는 순간 evaluator가 `break` → 세션 종료.
하지만 **Intent Override는 예외다.**

```python
override_applied = sample["scenario_type"] != "intent_override"   # IO면 False로 시작 / False for IO
for turn in range(1, MAX_TURNS + 1):
    response = agent.respond(...)
    ranked = normalize_recommendations(...)
    if override_applied and target in ranked:   # IO는 override 전까지 False / False for IO until override
        hit_turn = turn; break                   # 타깃이 rank 1이어도 break 안 함 / no break even at rank 1
    ...
    if not override_applied and turn + 1 == override["turn"]:
        override_applied = True                  # override 턴(3~4)에 켜짐 / turns on at the override turn
```

- IO 세션은 `override_applied`가 **override 턴에야 True**. 그 전엔 타깃이 top-10에 있어도 무시하고 세션 계속.
- 정답 상품은 세션 내내 **동일**하다 — 바뀌는 건 "지금 보여주면 점수를 주는가"뿐.
- 실측: IO 30세션 중 **21세션(70%)**에서 override 이전에 타깃이 이미 top-10에 떴다.
  트레이스 예 (public_0003): `t2 rank=7` (무집계) → `t3 override` → `t4 rank=1` HIT.
- **시사점 → R7**: 이전 노출 상품을 세션 영구로 제외하면, IO에서 override 전 노출된 타깃이 seen-set에 남아
  **override 후 집계 시점에 스스로 차단**된다 (자책골). → 에이전트가 **override 메시지를 감지하는 순간
  seen-set을 통째로 리셋**해야 한다. 이 리셋 덕에 R7을 "전량 제외"로 걸어도 IO HitRate 유지 (0.97, D5).

**EN** — Buying/Browsing/Boundary sessions `break` the moment the target hits top-10 → session ends. **Intent
Override is the exception.** `override_applied` starts False for IO and turns True only at the override turn
(3–4); before that, a target in top-10 is ignored and the session continues. The target product is the **same**
throughout — only "does showing it now score" changes. Measured: in **21 / 30 (70%)** IO sessions the target was
already in top-10 before the override (trace, public_0003: `t2 rank=7` uncounted → `t3 override` → `t4 rank=1`
HIT). **Implication → R7**: a permanent seen-set makes the agent block its own target after the override (own
goal). → the agent must **wipe the seen-set the moment it detects the override message.** With that reset, R7 can
be "full exclusion" and IO HitRate still holds (0.97, D5).

### F5. 제약 클래스 분포 / constraint-class distribution (per `classify_constraint`, 200 targets)

- 전체 제약 중: feature 50% / material 38% / color 8% / style 2% / size 1% / use_case 0%.
- 카드당 평균 4개 제약 (feature ~2, material ~1.5, 가끔 color).
- `classify_constraint`는 `brand`/`budget`/`category`를 **절대 반환하지 않는다** (키워드 폭포수, 기본값 feature).

**EN** — Of all constraints: feature 50% / material 38% / color 8% / style 2% / size 1% / use_case 0%. ~4 distinct
constraints per card (feature ~2, material ~1.5, sometimes color). `classify_constraint` **never returns**
`brand`/`budget`/`category` (keyword waterfall, default = feature).

---

## 4. 목표 지표 / Target metrics

| 지표 / metric | 현재 / now (`damin_start`) | 목표 / target | 스트레치 / stretch |
|---|---|---|---|
| TechnicalScore | 0.724 | **≥ 0.78** | 0.82 |
| MRR | 0.520 | ≥ 0.65 | 0.70 |
| MTTC | 4.20 | ≤ 3.5 | 3.0 |
| HitRate@10 | 0.865 | 유지 / hold (≥ 0.86) | 0.90 |

근거: HitRate는 현재 랭킹 기준 Oracle(0.87)에 붙어 있어 랭킹 개선(H1a/H1b) 없이는 유지가 현실적.
점수는 MRR·Efficiency에서 확보. (단 v1이 이미 HR 0.97 — Oracle 0.87을 넘었다. seen-set(R7)이 "완벽 추출"
가정에 없던 탐색을 추가하기 때문. §10.)

**현재 지점 (`starter/agent_v1.py`, 이터레이션 1)**: TS **0.820** / HR 0.970 / MRR 0.578 / MTTC 2.90 / 토큰 0.
시나리오별: Buying 0.96 / Browsing 0.99 / Intent Override 0.97 / Boundary 0.90.
목표선을 이미 넘음 → 목표를 TS ≥ 0.85 (스트레치 0.88)로 상향 검토 (§8).

**EN** — Rationale: HitRate sits on the current-ranking Oracle (0.87), so holding it is realistic without ranking
work (H1a/H1b); score comes from MRR + Efficiency. (Though v1 already hits HR 0.97 — past Oracle 0.87 — because
seen-set (R7) adds exploration the "perfect extraction" assumption did not have; §10.)
**Current point (`starter/agent_v1.py`, iteration 1)**: TS **0.820** / HR 0.970 / MRR 0.578 / MTTC 2.90 / 0 tokens.
By scenario: Buying 0.96 / Browsing 0.99 / Intent Override 0.97 / Boundary 0.90. Already past the target line →
consider raising the target to TS ≥ 0.85 (stretch 0.88) (§8).

---

## 4.5 트랙 구조 / Track structure

작업을 두 트랙으로 나눈다. **인터페이스는 고정** — retrieval 코어와 질문 정책이 서로를 안 건드린다.

| 트랙 / track | 소유 / owner | 범위 / scope | Rule/가설 |
|---|---|---|---|
| **A. 정량 / quantitative (retrieval)** | 별도 세션 / separate session | 누적 쿼리 구성, BM25 랭킹, profile 재랭킹, seen-set, dense | R1 R3 R4 R7 / H1 H4 H6 H7 |
| **B. 정성 / qualitative (clarification)** | 이 문서 §4.6 | intent mode 판별, 무엇을 언제 물을지, override 감지, 중단 조건 | R2 R5 / H3 H5 |

인터페이스 계약: `Agent.respond(session_id, user_message, turn, top_k) -> {message, ask_attribute, recommendations, usage}`.
정성 트랙은 retrieval 결과(랭킹된 후보)를 입력으로 받아 `ask_attribute`만 결정, 코어 로직 불변.
`agent_v1.py`는 두 트랙 병합본. 정성 실험은 DI 드래프트(`tiktokhackerthon2026_draft/playground/agents/damin_v1.py`)에서
먼저 돌리고 검증되면 이관.

**EN** — Two tracks, **fixed interface** — the retrieval core and the question policy do not touch each other.
Track A (quantitative / retrieval) owns cumulative query building, BM25 ranking, profile rerank, seen-set, dense;
Rules R1 R3 R4 R7, hypotheses H1 H4 H6 H7. Track B (qualitative / clarification) owns intent-mode detection, what
to ask when, override detection, stopping conditions; Rules R2 R5, hypotheses H3 H5. Interface contract:
`Agent.respond(session_id, user_message, turn, top_k) -> {message, ask_attribute, recommendations, usage}`. The
qualitative track takes the retrieval result (ranked candidates) as input and only decides `ask_attribute`; core
logic unchanged. `agent_v1.py` is the merged build. Qualitative experiments run first in the DI draft
(`tiktokhackerthon2026_draft/playground/agents/damin_v1.py`) and are ported once validated.

## 4.6 정성 트랙 — clarification policy 모델 / Qualitative track — clarification policy model

### 4.6.1 Intent mode 라우팅 / Intent-mode routing

| mode | 판별 / detection | gap 성격 / gap type | 질문 방향 / question direction |
|---|---|---|---|
| **buying** | 첫 메시지 `A key requirement is: …` | 정밀도 / precision — 키워드는 맞는데 제약을 놓친 후보 | 이미 밝힌 제약에 인접한 속성을 물어 조인다 (yield 우선) |
| **browsing** | 첫 메시지 `… but I'm still exploring` | 커버리지 / coverage — 제약 차원 자체를 모름 | 후보군에서 값이 가장 흩어진 속성을 물어 발견을 돕는다 (dispersion 우선) |
| **intent_override** | 턴 3~4 `ignore my earlier preference` | stale state — 취소된 옛 선호가 문맥에 남음 | 취소 감지 → 질문 소진상태 리셋 + seen-set 리셋(F4), 재-clarify |
| **boundary** | 특정 속성에 `use your judgment` | 그 속성엔 선호 없음 | 그 속성 영구 kill |

> buying vs intent_override는 턴 1에서 구분 불가 (둘 다 선호 진술로 시작). override는 턴 3~4 취소 메시지로만
> 드러난다 → 그전까지는 buying으로 취급.
> buying vs intent_override cannot be told apart on turn 1 (both start with a preference statement); the override
> only shows up in the turn 3–4 cancel message → treat as buying until then.

### 4.6.2 채택: `open_first` / Adopted: `open_first`

**턴 1 = 열린 질문 (`other`) 1회 → 턴 2+ = 수율순 퍼널.**
**Turn 1 = one open question (`other`) → turn 2+ = yield-ordered funnel.**

- 근거 (정성 트랙, damin_start 코어 실측): `open_first` TS 0.752 ≥ `all_other`(매 턴 other, 편법) 0.750 ≥
  고정 퍼널 0.724. MTTC 4.20→3.57.
- `agent_v1` (정량 코어 R7 포함) 재측정: `open_first` ≈ `other`-반복, 둘 다 TS ≈ 0.82. **점수는 같고
  `open_first`가 실서비스에서 성립** → `open_first` 채택.
- **왜 `other`를 매 턴 안 쓰나**: 시뮬레이터에서 `other`는 `classify_constraint` 게이트를 우회해 미공개 제약을
  종류 불문 2개씩 주는 와일드카드. 매 턴 쓰면 항상 이기지만("other 스팸") "그 외 뭐 있어요?"를 5번 묻는
  에이전트는 실 UX·심사(Presentation/Innovation)에서 안 통함. evaluator-optimal ≠ 좋은 제품 (D4).

**EN** — Evidence (qualitative track, damin_start core): `open_first` TS 0.752 ≥ `all_other` (every-turn other, a
hack) 0.750 ≥ fixed funnel 0.724; MTTC 4.20→3.57. Re-measured on `agent_v1` (with quantitative core R7):
`open_first` ≈ every-turn other, both TS ≈ 0.82. **Same score, and `open_first` holds up in a real service** →
adopt `open_first`. **Why not `other` every turn**: in the simulator `other` bypasses the `classify_constraint`
gate and returns 2 undisclosed constraints of any class — a wildcard. Asking it every turn always wins ("other
spam") but an agent that asks "anything else?" 5 times fails on real UX and on the Presentation/Innovation axes.
evaluator-optimal ≠ good product (D4).

### 4.6.3 info-gain 3축 모델 (R5 목표형, 아직 미채택) / 3-axis info-gain model (R5 target form, not yet adopted)

고정 퍼널 대신 **지금 후보군을 가장 크게 가를 속성**을 고른다:
Instead of a fixed funnel, pick **the attribute that best splits the current candidate set**:

```
value(A) = dispersion(A | 현재 top-50 후보 / current top-50) ^ α  ×  yield_prior(A) ^ β  ×  novelty(A)
```

- **dispersion(A)**: 후보 중 A의 값이 갈리는 정도 (50:50에서 최대 + 값 엔트로피). 후보가 A에서 이미 일치하면
  0 → **유저가 A를 이미 말했으면 자연히 0으로 수렴, 하드 제외 규칙 불필요.** / how split the candidates are on
  A (max at 50:50 + value entropy); 0 if candidates already agree on A → converges to 0 once the user has stated
  A, so no hard exclusion rule needed.
- **yield_prior(A)**: 유저가 A에 선호를 가질 사전확률 (F5 실측). `brand`/`budget`/`category` ≈ 0 → 로직이 알아서
  피함. / prior that the user has a preference on A (F5); `brand`/`budget`/`category` ≈ 0 → naturally avoided.
- **novelty(A)**: 소진(boundary / 반복 무응답)이면 0. / 0 if exhausted (boundary / repeated no-info).
- **mode별 지수 / per-mode exponents**: browsing = dispersion 우선 (α>β), buying = yield 우선 (β>α).

**현재 상태 / status**: info-gain 단독은 고정 퍼널과 **동률** (TS ≈ 0.72). 원인 = dispersion 신호가 거침
(후보 텍스트 키워드 추출 기반, `feature`는 계열어가 없어 고정값 0.55). 개선 방향 → decision_log D6.
Info-gain alone only **ties** the fixed funnel (TS ≈ 0.72). Cause = the dispersion signal is coarse (keyword
extraction from candidate text; `feature` has no keyword family so it uses a fixed 0.55). Improvement path → D6.

### 4.6.4 Answerability / 중단 조건 / stopping conditions

- **boundary**: `use your judgment` → 그 속성 kill (1회성) / kill that attribute (one-off).
- **반복 무응답 / repeated no-info**: 같은 속성 2회 물어 새 정보 없음 → kill.
- **`ask_attribute=None` 뒤 `"not quite right yet"`**: 질문을 안 한 것 → 다음 턴 반드시 질문 (H5) /
  we asked nothing → must ask next turn (H5).
- `ASK_UNTIL_TURN`(기본 10)까지만 질문, 이후엔 추천만 / ask only until `ASK_UNTIL_TURN` (default 10), then recommend-only.

### 4.6.5 H1 — "이른 열린 질문 ≥ 좁은 퍼널" (검증 미완, 서사 분리 필수) / "early open question ≥ narrow funnel" (unverified, must be narrated separately)

- **직관**: 목적이 뚜렷한 유저에게 `category→color` 식 좁은 퍼널은 번복을 유발하고, 초반 열린 질문 1회가 더 정확한
  신호를 준다.
- **검증 한계**: 공식 시뮬레이터 customer는 결정론적이고 backtracking·혼란 모델이 없다 — 물어본 속성의 제약을
  기계적으로 공개할 뿐. 시뮬에서 `open_first`가 지표를 올리는 건 **와일드카드가 턴을 안 버려서**이지 H1이
  참이어서가 아니다.
- **리포트 서술**: `open_first` 점수 개선 = "시뮬레이터 대리지표". H1(열린 질문이 확신 유저의 응답 정확도를
  높인다) = "검증 미완 + 실서비스 가설". 두 개를 **분리 서술**. 진짜 검증은 사람 피험자 or backtracking
  모델링한 LLM-시뮬 유저 필요 → 대회 범위 밖.

**EN** — **Intuition**: for a purpose-driven user, a narrow `category→color` funnel invites contradiction, and one
early open question gives a cleaner signal. **Verification limit**: the official simulated customer is
deterministic with no backtracking/confusion model — it just mechanically discloses the asked attribute's
constraints. `open_first` raising metrics in the simulator is **because the wildcard doesn't waste a turn**, not
because H1 is true. **Report wording**: `open_first`'s score gain = "simulator proxy metric"; H1 (open questions
improve a confident user's answer accuracy) = "unverified + real-service hypothesis". Narrate the two
**separately**. Real verification needs human subjects or an LLM-simulated user with a backtracking model → out of
contest scope.

## 4.7 정성 트랙 실험 설계 / Qualitative-track experiment design

### 매트릭스 / matrix (`damin_v1.py`, env `DAMIN_V1_STRATEGY`) — damin_start 코어 기준 / on the damin_start core

| variant | 질문 정책 / policy | TS | HitRate | MRR | MTTC | 상태 / status |
|---|---|---|---|---|---|---|
| `damin_start` | 고정 퍼널 (대조군) / fixed funnel (control) | 0.724 | 0.865 | 0.520 | 4.20 | 완료 / done |
| `funnel` | v1 코드로 퍼널 재현 / funnel re-impl (regression check) | 0.723 | 0.865 | 0.516 | 4.22 | 회귀 없음 / no regression |
| `info_gain` | 턴 1부터 info-gain / info-gain from turn 1 | 0.721 | 0.860 | 0.522 | 4.25 | 퍼널과 동률 / ties funnel |
| **`open_first`** | 턴 1 `other` → info-gain | **0.752** | 0.885 | 0.535 | **3.57** | **채택 / adopted** |
| `all_other` | 매 턴 `other` (편법 상한선) / every turn (hack ceiling) | 0.750 | 0.875 | 0.538 | 3.46 | open_first가 상회 / open_first wins |

각 variant를 4 시나리오별로 채점하고 전체 점수뿐 아니라 시나리오별 델타를 본다.
Score every variant per scenario and look at per-scenario deltas, not just the aggregate.

### info-gain dispersion 범위 / dispersion scope

- **1차 (현재) / phase 1 (now)**: 현재 BM25 후보 top-50에서만 dispersion 계산 — 가볍고 실시간 / compute
  dispersion only over the current BM25 top-50 — light, real-time.
- **2차 (후속) / phase 2 (later)**: `details` dict 구조화 필드 파싱 or 카탈로그 50k 전체 통계. 1차 대비
  시나리오별 델타로 "근사로 충분한가" 판단 / parse `details` dict structured fields or use full 50k catalog
  statistics; decide "is the approximation enough" from the per-scenario delta vs phase 1.

### 파라미터 노출 원칙 / parameter-exposure rule

`ASK_UNTIL_TURN`, 후보 pool 크기, profile 재랭킹 가중치, dispersion/yield/novelty 결합 방식, `DEMOTE_COEF` —
모두 모듈 상단 상수 or 생성자 인자로. **상수로 하드코딩하지 않는다** (private set 대비 튜닝 여지).
All of the above go as module-top constants or constructor args. **Do not hardcode as literals** (leave tuning
room for the private set).

---

## 5. Rules — 확정 요구사항 / Confirmed requirements

각 Rule은 "왜 필요한가"를 evaluator 메커니즘으로 정당화한다. / Each Rule is justified by an evaluator mechanism.

| ID | 트랙 | 요구사항 / requirement | 근거 / rationale | v1 상태 / status |
|---|---|---|---|---|
| **R1** | A | 선호 + 지난 응답을 세션 내내 기억, history 삭제 금지 / keep preferences + prior replies for the whole session, never clear history | 시뮬레이터가 제약을 매 턴 1~2개씩 흘림(F5). 마지막 메시지만 보면 평균 4개 중 1~2개로만 검색 / simulator leaks 1–2 constraints per turn; last-message-only searches on 1–2 of ~4 | ✅ 구현 (flat term bag) — 고도화는 **H6** |
| **R2** | B | Intent Override(3~4턴) 감지 → override 우선, 이전 선호는 삭제 안 하되 고려 / detect override, prioritize it, keep (not delete) the old preference | old_value = `soft_preferences[-1]`, 완전 삭제하면 카테고리·타 제약 손실. **음의 가중치 감점은 이 시뮬레이터에서 역효과 → 기본 off (D2).** R2 실질 = "감지 → seen-set 리셋(R7) + 계속 누적" / demotion is counterproductive here → off; R2 = "detect → reset seen-set + keep accumulating" | ✅ 감지+리셋만, 감점 off |
| **R3** | A | profile term 0.2배 약한 재랭킹 / weak 0.2x profile-term rerank | profile은 정답을 안 가리키는 안전 집계 → tiebreaker로만 / profile does not point at the answer → tiebreaker only | ✅ 구현 (계수는 H4) |
| **R4** | A | R1 누적으로 카탈로그 쿼리 구성 / build the catalog query from the R1 accumulation | R1의 귀결 / follows from R1 | ✅ 구현 (누적 BM25) |
| **R5** | B | 질문 정책 **`open_first`** — 턴1 열린질문 → 턴2+ 수율순 퍼널 / question policy `open_first` | §4.6. 매 턴 other는 편법(D4). 적응형 info-gain은 아직 퍼널 못 이김 → 백로그(D6) | ✅ open_first 구현 |
| **R7** | A | 이전 턴 노출 상품 재노출 금지 — **전량 제외 + override 경계 seen-set 리셋** / never re-show a shown product — full exclusion + reset at the override boundary | 세션은 타깃 히트 시 종료 → 턴 2+ = 이전 노출분에 타깃 없음. 상위 오답 밀어내면 rank 11~50 타깃 진입(F2). **override 예외: F4.** keep-top-N은 −0.05(D5). MMR novelty 계열 / session ends on hit → past turn 1, no target among shown; pushing wrong top answers out surfaces a rank 11–50 target. override exception: F4. keep-top-N is −0.05 (D5). MMR-novelty family | ✅ 구현 (+0.061 기여) |

R2·R7은 override 로직으로 함께 설계한다. R2·R7 are designed together as the override logic.
(v1: TS 0.820 / HR 0.970 / MRR 0.578 / MTTC 2.90)

---

## 6. 가설 / Hypotheses — accept after validation

| ID | 트랙 | 가설 / hypothesis | 기대 효과 / expected | 근거 / rationale | 우선순위 / prio |
|---|---|---|---|---|---|
| **H1a** | A | BM25 필드 가중치 재튜닝 / re-tune BM25 field weights (title 6 / cat 4 / feat 2.5 / det 2.5 / store 1.5 / desc 1) | rank-1 ↑ | F3 — term은 다 매칭됨, 문제는 가중치 배분 / terms all match; the issue is weight allocation | **1** |
| **H1b** | A | dense/hybrid 재랭킹 (로컬 임베딩, in-memory) — **판별력 목적** / dense/hybrid rerank (local embedding) — for discrimination | rank-1 천장 돌파 / break the rank-1 ceiling | F2 — lexical rank-1 천장 64% | 2 |
| H1c | A | 쿼리 재작성/확장 (H1a와 묶어서) / query rewrite/expansion (bundle with H1a) | recall ↑ | — | 3 |
| **H3** | B | 적응형 info-gain 질문 순서 (§4.6.3, R5 목표형) / adaptive info-gain ordering | MTTC ↓, 실서비스 정합 / real-service fit | 현재 dispersion 신호 거침 → 퍼널과 동률(D6), 개선 여지 | 2 |
| **H4** | A | profile 재랭킹 0.2배 계수·term 선별 최적화 / tune the 0.2x coefficient + term selection | MRR 소폭 ↑ | 계수 스윕으로 저비용 검증 / cheap to sweep | 3 |
| **H5** | B | `NO_NEW_INFO_RE` 3패턴 분리 (§8) / split the 3 NO_NEW_INFO patterns | 적응형 도입 시 회귀 방지 / prevents regression when H3 lands | 시뮬레이터 응답 3종의 의미가 다름 / the 3 replies mean different things | ✅ v1 구현 |
| **H6** | A | 대화 상태 표현 고도화: flat term bag → 속성별 constraint slot, recency 가중, 부정 처리 / richer state: per-attribute slots, recency, negation | 쿼리 정밀도 ↑ | R1은 "기억"만 요구, 저장·가공 방식은 열려 있음 / R1 requires only "remember" | 2 |
| **H7** | A | 동의어·패러프레이즈 대응 dense 검색 / dense search for synonyms/paraphrase | recall ↑ (F3가 깨질 때 / if F3 breaks) | **F3 헤지** — private set 조직자 패러프레이징 대비 | 낮음 (파킹) / low (parked) |

> ~~H2 (override 감점 메커니즘)~~ — D2에서 폐기. 감점은 이 시뮬레이터에서 역효과.
> ~~H2 (override demotion mechanism)~~ — dropped in D2. Demotion is counterproductive here.

**검증 절차 / validation**: 각 가설은 `evaluator/run_agent.py`로 200세션 실측 → TechnicalScore·시나리오별
비교. Rule 회귀(특히 IO, Boundary) 없을 때만 채택. / Measure each hypothesis on 200 sessions via
`evaluator/run_agent.py`; accept only with no Rule regression (esp. IO, Boundary).
**overfit 방지 / overfit guard**: 파라미터를 학습하는 가설(H1a, H1b, H4)은 public 200을 train/holdout으로 나눠
holdout 개선까지 확인 — §2의 3원칙. / Hypotheses that learn parameters (H1a, H1b, H4) must show improvement on a
held-out split — the 3 rules in §2.

---

## 7. 안 하는 것 / Out of scope (and why)

| 항목 / item | 안 하는 이유 / why not |
|---|---|
| **Buying vs Browsing 별도 retrieval 파이프라인 / separate retrieval pipelines** | 브라우징이 도중에 구매 의사를 밝힐 수 있어 하드 라우팅은 경직. 단 mode를 info-gain 지수(α/β) 조절에는 사용 (§4.6.1) — 파이프라인 분기가 아닌 약한 신호. / browsing can turn into buying mid-session, so hard routing is brittle; mode is used only to tune the α/β exponents, not to branch the pipeline. |
| **Cross-encoder 등 무거운 리랭커 / heavy rerankers** | H1b(로컬 dense)로 먼저 판별력 헤드룸 검증. "infra-heavy vector DB"는 스펙상 out of scope, cross-encoder는 지연·복잡도 대비 근거 부족. / validate the discrimination headroom with H1b first; infra-heavy vector DBs are out of spec scope and a cross-encoder is not justified vs its latency/complexity. |
| **순수 동의어 목적 dense 검색 (지금은) / pure synonym-oriented dense search (for now)** | F3 — 현재 시뮬레이터는 카탈로그 원문 단어를 인용 → 동의어 갭이 병목 아님. 판별력 목적(H1b)이 먼저. private 대비 헤지로 **H7 파킹** (완전 배제 아님). / F3 — the current simulator quotes catalog wording, so the synonym gap is not the bottleneck; discrimination (H1b) comes first; parked in H7 as a private-set hedge (not fully excluded). |
| **LLM 파이프라인 전체 사용 / LLM for the whole pipeline** | evaluator가 키워드·exact-match 기반이라 검색 향상 근거 불확실. 모델 비용·지연·fallback disclosure 부담. 필요 시 쿼리 재작성 등 국소 사용만 재검토(H1c). / the evaluator is keyword/exact-match, so a search gain is unclear; cost/latency/fallback-disclosure burden. Revisit only local uses like query rewrite (H1c). |
| **price / rating 재랭킹 / price / rating rerank** | F1 — 타깃 가격이 공개되지 않아 신호 근거 약함. 낮은 우선순위 가설로만 (미채택). / target price is undisclosed → weak signal; low-priority hypothesis only (not adopted). |
| **brand / budget / category 속성 질문 / asking those attributes** | F1 + F5 — `classify_constraint`가 이 클래스를 절대 반환 안 함. 물어도 제약 공개 안 됨. / `classify_constraint` never returns these; asking discloses nothing. |
| **catalog 수정, full-model training, multimodal, 실거래 / catalog edits, full training, multimodal, real transactions** | 대회 스펙상 명시적 out of scope. / explicitly out of scope in the spec. |

---

## 8. 미해결 결정 & 리스크 / Open decisions & risks

### 결정됨 (→ decision_log) / Decided

- **R2 감점 / R2 demotion** → 음의 가중치는 이 시뮬레이터에서 역효과, **기본 off** (D2). R2 = "감지 → seen-set
  리셋 + 계속 누적". / negative weight is counterproductive here, off by default (D2); R2 = "detect → reset
  seen-set + keep accumulating".
- **R5 질문 정책 / R5 policy** → `open_first` 채택, 매 턴 `other`(편법)는 안 씀 (D4). / adopt `open_first`, no every-turn `other` (D4).
- **R7 seen-set** → 세션 영구 제외 + override 경계 리셋, keep-top-N 폐기 (D5). / permanent exclusion + override-boundary reset; keep-top-N dropped (D5).
- **H5** → `"not quite right yet"`(= `ask_attribute=None` 신호)는 소진 아님, 다음 턴 강제 질문. 나머지 2패턴은
  소진 (구현됨). / "not quite right yet" (= ask_attribute=None) is not exhaustion → force a question next turn; the other 2 patterns exhaust (implemented).

### 남은 결정 / Still open

1. **목표 지표 상향 / raise the target**: v1이 0.820 → TS ≥ 0.85 / 스트레치 0.88 (§4). 팀 합의 / team decision.
2. **H1b 임베딩 모델 / embedding model**: 로컬 소형(e5-small 류). 크기·지연 예산 미정 / local small model; size/latency budget TBD.
3. **H6 상태 표현 범위 / state-representation scope**: 속성별 슬롯만 vs recency/부정까지 / slots only vs recency/negation too.
4. **정성 트랙 다음 실험 / next qualitative experiment**: `open_first` + 턴2부터 퍼널 vs + 턴2부터 info-gain —
   `other` 공짜 효과를 뺀 뒤 info-gain 실기여 분리 측정 / isolate info-gain's real contribution after removing the free `other` turn.

### 리스크 / Risks

- **시뮬레이터 오버핏 / simulator overfit**: `yield_prior`가 public 200 실측 → private 800에서 분포 다를 수
  있음. dispersion(후보 기반, 데이터 독립)에 더 무게. BM25 튜닝은 §2 3원칙. / `yield_prior` is measured on
  public 200; the private 800 may differ. Lean on dispersion (candidate-based, data-independent). BM25 tuning
  follows the §2 rules.
- **`other` wildcard 의존 / dependence on the `other` wildcard**: private 시뮬레이터가 `other`를 wildcard로
  안 받으면 `open_first` 턴1 효과가 사라짐 → 순수 퍼널로 fallback (코드에서 상수 교체). / if the private
  simulator does not treat `other` as a wildcard, the turn-1 effect disappears → fall back to a pure funnel (swap
  a constant).
- **intent_override 조기 노출 / early exposure in intent_override**: `open_first`가 곧 취소될 soft 선호를
  일찍 문맥에 넣음. 단 그 선호는 턴 1 프롬프트에 이미 있어 영향 작음 — 시나리오별 지표로 확인 (현재 IO HR
  0.97, 문제 없음). / `open_first` puts a soon-to-be-cancelled soft preference into context early, but it is
  already in the turn-1 prompt, so the effect is small — watch the per-scenario metric (currently IO HR 0.97, fine).
- **2트랙 병합 충돌 / merge conflict between tracks**: retrieval 코어를 정성 트랙이 안 건드림. 공용
  인터페이스로만 결합 (§4.5). / the qualitative track never touches the retrieval core; they join only through the shared interface (§4.5).

---

## 9. 다음 단계 / Next steps

1. **v1 코드 + decision_log 통독 리뷰** ← 현재 여기. / read-through review of the v1 code + decision_log ← here now.
2. `agent_v1.py` → `starter/agent.py` 정식 배선 (현재 `evaluator/run_agent.py`로 채점, baseline 보존 중). /
   wire `agent_v1.py` in as `starter/agent.py` (currently scored via `evaluator/run_agent.py`, baseline preserved).
3. 착수 순서 / order:
   - **H1a** (BM25 가중치 스윕) — 저비용, Oracle 재측정으로 랭킹 천장 갱신. overfit 3원칙.
   - **H1b** (dense 재랭킹) — rank-1 64% 천장 돌파.
   - **H6** (constraint slot 구조) — 쿼리 정밀도.
   - **H3** (정성 트랙 info-gain 성숙) — DI 드래프트에서 진행, 성숙하면 이관.
4. 각 단계 `evaluator/run_agent.py` 실측 비교표를 §10에 누적. Rule 회귀(IO·Boundary) 체크 필수. /
   append each step's measured comparison to §10; always check IO/Boundary regression.

## 10. 이터레이션 로그 / Iteration log

| 이터 / iter | 변경 / change | TS | HR | MRR | MTTC | 비고 / note |
|---|---|---|---|---|---|---|
| 0 | baseline `starter/agent.py` | 0.107 | 0.125 | 0.068 | 9.81 | 재현 확인 / reproduced |
| — | `damin_start` (참고 / ref) | 0.724 | 0.865 | 0.520 | 4.20 | — |
| **1** | **R1·R3·R4·R7 + R2 감지·리셋 + R5 open_first + H5** | **0.820** | 0.970 | 0.578 | 2.90 | `agent_v1.py`. 감점·keep-top-N·greedy적응형 폐기 / demotion, keep-top-N, greedy-adaptive dropped |
