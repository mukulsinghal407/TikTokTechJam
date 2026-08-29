# Decision Log — Conversational Shopping Agent

> 한/영 병기. 각 항목은 한국어 먼저, 그 아래 **EN**.
> Bilingual. Each entry is Korean first, **EN** below.

> PRD(`prd_draft.md`)의 Rule/가설이 구현·실측되며 내려진 결정. 각 항목: 맥락 → 결정 → 근거 → 재검토 조건.
> 실측은 모두 `evaluator/run_agent.py` public_set 200 기준.
>
> Decisions made while implementing and measuring the PRD's Rules/hypotheses. Each entry: context → decision →
> rationale → re-review trigger. All numbers are `evaluator/run_agent.py` on public_set 200.

---

## D1. 베이스라인 = 공식 `starter/agent.py`, `damin_start`는 참고 / Baseline = official `starter/agent.py`; `damin_start` is a reference

- **결정**: 점수 기준선은 starter(TS 0.107). `damin_start`(TS 0.724)는 검증된 구현 레퍼런스로만 사용, 새 코드는 starter 구조에서 재작성.
- **근거**: reasoning이 "왜 이 선택인지"를 처음부터 설명하려면 damin_start를 기정사실로 두면 안 됨.

**EN** — Decision: the scoring baseline is `starter` (TS 0.107); `damin_start` (TS 0.724) is used only as a
validated implementation reference, and the new code is rewritten from the `starter` structure. Rationale: for the
reasoning to explain "why this choice" from first principles, `damin_start` must not be treated as a given.

---

## D2. R2 "이전 선호 음의 가중치 감점" → 기본 OFF (`DEMOTE_COEF = 0`) / R2 "negative-weight demotion of the old preference" → OFF by default

- **맥락**: PRD R2 = intent override 시 이전 선호를 잊지 않되 감점.
- **결정**: 감점 메커니즘을 구현은 하되 계수 0. override 처리의 실질 = **seen-set 리셋 + 계속 누적**.
- **근거 (실측)**: blanket 감점 → IO HitRate 0.87→0.20. 수술적(old_value만) 감점 → 0.90, 여전히 무감점(0.97)보다 나쁨.
  원인은 **시뮬레이터 아티팩트**: `behavior_for()`에서 `old_value = soft_preferences[-1]`,
  `new_value = hard_constraints[0]` — **둘 다 타깃 상품 `intent_card`에서 파생** (30/30 IO 세션 확인).
  예: `"Buckle closure" → "leather"`는 같은 벨트(타깃)의 두 속성. 버려지는 선호도 여전히 타깃을 가리키는
  신호라, 감점하면 타깃이 같이 내려간다.
- **실제 설계 의도로는 감점이 옳다**: 현실의 "그거 무시하고 X"는 다른 상품을 가리킬 수 있음. private set도 같은
  시뮬레이터 설계이므로 이 evaluator 한정 판단이 아니라 이 시뮬레이터 계열 전체에 이관됨.
- **재검토**: private 시뮬레이터가 old/new value를 타깃과 무관하게 생성하면 즉시 `DEMOTE_COEF > 0` 복원.
  Innovation 심사용 서술에는 "감지→감점" 설계를 유지.

**EN** — Context: PRD R2 says keep (not forget) the old preference but demote it. Decision: implement the
demotion mechanism but with coefficient 0; the substance of override handling is **reset seen-set + keep
accumulating**. Rationale (measured): blanket demotion → IO HitRate 0.87→0.20; surgical (old_value only) demotion
→ 0.90, still worse than no demotion (0.97). Cause is a **simulator artifact**: in `behavior_for()`,
`old_value = soft_preferences[-1]` and `new_value = hard_constraints[0]` are **both derived from the target's own
`intent_card`** (verified 30/30 IO sessions). e.g. `"Buckle closure" → "leather"` are two attributes of the same
belt (the target). The abandoned preference still points at the target, so demoting it drags the target down. **In
real product terms, demotion is correct** — a real "ignore that, I want X" can point at a different product; the
private set uses the same simulator design, so this is not evaluator-specific — it carries to the whole simulator
family. Re-review: if the private simulator generates old/new value independently of the target, immediately
restore `DEMOTE_COEF > 0`. Keep the "detect → demote" design in the Innovation write-up.

---

## D3. Intent Override 시나리오 설계 자체가 의도를 테스트하지 못함 (조직자 이슈) / The Intent Override scenario design does not test what it claims (organizer issue)

- **관찰**: IO는 "이전 선호를 3~4턴에 교체"한다지만, 실제로는 같은 타깃의 soft 속성 하나를 hard로 승격할 뿐.
  정답 상품은 안 바뀌고, 버린 선호조차 타깃 신호. **"intent override"라는 이름이 테스트하는 것과 다르다.**
- **함의**: 이 시나리오에서 점수를 올리는 정공법은 "override를 잘 처리"가 아니라 "override 이전에 쌓은 정보를
  유지"다. `override_applied` 게이트 때문에 override 전 히트가 무집계라, 사실상 "override 후 몇 턴 안에 재수렴"
  문제로 축소됨.
- **액션**: 우리 에이전트는 위 사실에 맞춰 동작(D2). 조직자 Q&A에서 IO 시나리오 설계 의도를 물어볼지는 DI 판단.

**EN** — Observation: IO claims to "replace an earlier preference on turn 3–4", but in practice it only promotes
one soft attribute of the same target to a hard constraint. The answer product does not change, and even the
abandoned preference is target signal. **The name "intent override" does not match what it tests.** Implication:
the way to score here is not "handle the override well" but "keep the information accumulated before the
override". Because of the `override_applied` gate, pre-override hits do not count, so it reduces to "re-converge
within a few turns after the override". Action: our agent behaves per this fact (D2). Whether to raise the IO
design with the organizers in Q&A is DI's call.

---

## D4. 질문 정책 — `open_first` (매 턴 `other` 아님) / Question policy — `open_first` (not every-turn `other`)

- **맥락**: PRD R5. 정성 트랙에서 4개 전략 A/B 테스트.
- **결정**: **`open_first`** — 턴 1에 열린 질문(`other`) 1회, 턴 2+ 는 F5 수율순 퍼널. 매 턴 `other`(`all_other`)는 안 씀.
- **근거 (실측)**:
  - damin_start 코어: `open_first` TS 0.752 ≥ `all_other` 0.750 ≥ 고정 퍼널 0.724. MTTC 4.20→3.57.
  - agent_v1 (R7 포함) 재측정: `open_first` ≈ `all_other`, 둘 다 TS ≈ 0.82. **점수 동일**.
  - `other`가 강한 이유: `customer_reply()`에서 `attribute == "other"` 는 `classify_constraint` 게이트를 우회
    → 미공개 제약을 클래스 무관 턴당 2개.
- **왜 `all_other`가 아니라 `open_first`**: 점수가 같은데 `open_first`가 실서비스에서 성립한다. "그 외 뭐
  있어요?"를 5번 묻는 에이전트는 실 UX·Presentation/Innovation 심사에서 감점.
  **evaluator-optimal(`all_other`) = 좋은 제품(`open_first`)일 때는 후자를 택한다.**
- **서사 분리 (필수)**: `open_first`의 점수 이득은 "시뮬레이터 대리지표"(와일드카드가 턴을 안 버림).
  "열린 질문이 확신 유저의 응답 정확도를 높인다"(가설 H1)는 **검증 미완** — 결정론 시뮬은 backtracking 모델이 없음.
- **재검토**: private 시뮬레이터가 `other`를 wildcard로 안 받으면 순수 퍼널로. 적응형 info-gain(D6)이 성숙하면
  `open_first` 뒤를 그걸로 교체.

**EN** — Context: PRD R5; A/B-tested 4 strategies in the qualitative track. Decision: **`open_first`** — one open
question (`other`) on turn 1, then the F5 yield-ordered funnel on turn 2+. No every-turn `other` (`all_other`).
Rationale (measured): on the damin_start core, `open_first` TS 0.752 ≥ `all_other` 0.750 ≥ fixed funnel 0.724;
MTTC 4.20→3.57. Re-measured on agent_v1 (with R7): `open_first` ≈ `all_other`, both TS ≈ 0.82 — **same score**.
`other` is strong because in `customer_reply()`, `attribute == "other"` bypasses the `classify_constraint` gate →
2 undisclosed constraints of any class per turn. **Why `open_first` and not `all_other`**: same score, and
`open_first` holds up in a real service; an agent that asks "anything else?" 5 times loses on real UX and the
Presentation/Innovation axes. **When evaluator-optimal (`all_other`) = good product (`open_first`), pick the
latter.** Narrate separately (required): `open_first`'s score gain is a "simulator proxy metric" (the wildcard
does not waste a turn); "open questions improve a confident user's answer accuracy" (H1) is **unverified** — the
deterministic simulator has no backtracking model. Re-review: if the private simulator does not treat `other` as
a wildcard, drop to the pure funnel; once adaptive info-gain (D6) matures, replace the post-turn-1 funnel with it.

---

## D5. R7 — 이전 노출 상품 전량 제외 + override 경계 리셋 / R7 — full exclusion of shown products + reset at the override boundary

- **맥락**: PRD R7. DI 제안 = 상위 N개는 유지하고 나머지만 교체(안전 마진).
- **결정**: **전량 제외** (keep-top-0). override 감지 시 seen-set 클리어.
- **근거 (실측)**: keep-0 TS 0.813 / IO 0.97. keep-3 0.783. keep-5 0.768. keep-7 0.764. **유지할수록 나빠진다.**
  - 전량 제외가 안전한 이유: 세션은 타깃이 top-10에 뜨는 순간 종료 → 턴 2+에 도달 = 이전 노출분에 타깃 없음
    → 제외해도 타깃을 못 지운다.
  - **"override 경계 리셋"의 의미**: IO 세션은 `override_applied=False` 동안 타깃이 top-10에 떠도 무집계
    (F4, 실측 21/30). 이때 노출된 타깃을 seen-set이 영구 기억하면, override 후 점수가 집계될 때 "이미
    보여줬다"고 스스로 차단한다. → override 메시지를 감지하는 순간 seen-set을 비운다. DI가 keep-top-N으로
    막으려던 "좋은 후보가 R7 때문에 날아감"은 IO에서만 실재하고, 그건 이 리셋으로 이미 해결됨 (keep-0인데도 IO 0.97).
- **문헌 위치**: MMR(Maximal Marginal Relevance) 계열 result diversification의 hard-novelty 특수 케이스 —
  유사도 대신 "노출 이력"에 대해 λ를 최대로. 단 **cross-turn 노출 이력 처리는 대화형 추천 문헌에서
  under-addressed** → Innovation 서술 포인트.
- **재검토**: private에서 세션 종료 조건이 다르면(예: top-10 히트해도 계속) 전량 제외가 위험 → 재측정.

**EN** — Context: PRD R7. DI's proposal = keep the top N and only swap the rest (safety margin). Decision: **full
exclusion** (keep-top-0); clear the seen-set on override detection. Rationale (measured): keep-0 TS 0.813 / IO
0.97; keep-3 0.783; keep-5 0.768; keep-7 0.764 — **the more you keep, the worse.** Full exclusion is safe because
the session ends the moment the target hits top-10, so reaching turn 2+ means no target among the shown set →
excluding them cannot erase the target. **"Override-boundary reset" means**: in IO, while `override_applied=False`
a target in top-10 is uncounted (F4, measured 21/30). If the seen-set permanently remembers that target, the
agent blocks it after the override when it would score → so wipe the seen-set on detecting the override message.
The "R7 discards a good candidate" problem DI wanted keep-top-N for is real only in IO, and this reset already
solves it (IO 0.97 even at keep-0). Literature: a hard-novelty special case of MMR-family result diversification —
maximise λ against "exposure history" instead of similarity; **cross-turn exposure history is under-addressed in
the conversational-recommendation literature** → an Innovation talking point. Re-review: if the private session-end
condition differs (e.g. keep going after a top-10 hit), full exclusion becomes risky → re-measure.

---

## D6. R5 적응형 info-gain 질문 — 아직 퍼널을 못 이김, 백로그 (목표형) / R5 adaptive info-gain questioning — does not beat the funnel yet, backlog (target form)

- **시도 1 (agent_v1, greedy mining)**: "드러난 material/color 후순위 + yielded 속성 계속 캐기". 정적 순서보다 TS −0.015. 폐기.
- **시도 2 (정성 트랙, dispersion info-gain)**: `value(A) = dispersion(A|top-50 후보)^α × yield_prior(A)^β ×
  novelty(A)`, mode별 지수. 턴 1부터 적용 시 고정 퍼널과 **동률** (TS ≈ 0.72). browsing만 +0.006.
- **진단**: dispersion 신호가 거침 — 후보 텍스트에서 키워드 정규식으로 속성 값 추출 → `feature`는 계열어가 없어
  고정값(0.55). yield순 퍼널 대비 우위를 만들 만큼 정밀하지 않음.
- **채택된 절충**: `open_first`(D4) — 열린 질문의 "공짜 턴" 효과만 취하고 나머지는 퍼널.
- **백로그 (개선 방향)**:
  - dispersion 정밀화: `details` dict의 구조화 필드(department/material 등) 직접 파싱, 또는 카탈로그 50k 전체 통계 기반.
  - stage-aware: 초반 attribute → 후반 item 제시 (When and How to Ask, SIGIR 2026).
  - decision-tree 정보이득: 후보 공간 최대 분할 (Wizard of Shopping, arxiv 2502.00969).
- **상태**: 정성 트랙(`tiktokhackerthon2026_draft`)에서 계속. `open_first` + 턴2부터 info-gain vs 퍼널 분리 측정이 다음 실험.

**EN** — Attempt 1 (agent_v1, greedy mining): "de-prioritise disclosed material/color + keep mining a yielding
attribute" — TS −0.015 vs the static order. Dropped. Attempt 2 (qualitative track, dispersion info-gain):
`value(A) = dispersion(A|top-50)^α × yield_prior(A)^β × novelty(A)`, per-mode exponents. Applied from turn 1 it
only **ties** the fixed funnel (TS ≈ 0.72); browsing +0.006. Diagnosis: the dispersion signal is coarse —
attribute values extracted from candidate text via keyword regex, and `feature` has no keyword family so it uses a
fixed 0.55; not precise enough to beat the yield-ordered funnel. Adopted compromise: `open_first` (D4) — take only
the "free turn" effect of the open question, funnel for the rest. Backlog: sharpen dispersion (parse `details`
dict structured fields, or full 50k catalog stats); stage-aware (attributes early → items later, When and How to
Ask, SIGIR 2026); decision-tree info gain (max candidate-space split, Wizard of Shopping, arxiv 2502.00969).
Status: continues in the qualitative track. Next experiment: `open_first` + funnel-from-turn-2 vs
info-gain-from-turn-2, isolated.

---

## D7. BM25 필드 가중치 (H1a) — 이번 이터레이션 미변경 / BM25 field weights (H1a) — unchanged this iteration

- **결정**: 현재값 `title 6 / cat 4 / feat·det 2.5 / store 1.5 / desc 1` 유지. 다음 이터레이션.
- **주의**: public 200에 overfit 금지 — train/holdout 분할, 큰 폭 개선만, 시나리오 4종 회귀 없을 때만 (PRD §2 3원칙).

**EN** — Decision: keep the current `title 6 / cat 4 / feat·det 2.5 / store 1.5 / desc 1`; next iteration.
Caution: do not overfit to public 200 — train/holdout split, large gains only, no regression across the 4
scenarios (PRD §2, the 3 rules).

---

## D8. 2트랙 분리 + PRD 단일화 / Two-track split + PRD consolidation

- **맥락**: retrieval 개선(정량)과 clarification 정책(정성)을 병렬 진행. 한때 PRD가 2개 —
  `TikTokTechJam/docs/prd_draft.md` (정량 중심) + `tiktokhackerthon2026_draft/docs/PRD.md` v0.2 (정성 트랙).
- **결정 (2026-08-29)**:
  1. **인터페이스 고정, 트랙 분리** — 정성 트랙은 retrieval 결과(랭킹된 후보)를 입력으로 받아 `ask_attribute` 만 결정. 코어 로직 불변.
  2. **PRD 단일화** — 팀 레포 `prd_draft.md`가 유일한 소스. DI 드래프트 PRD의 §3(mode 라우팅)·§5(실험 설계)·
     §6(후속)·§8(리스크)을 `prd_draft.md` §4.5~4.7 / §8로 흡수. DI 드래프트 `docs/PRD.md`는 상단에
     "SUPERSEDED → 팀 레포" 표기 후 히스토리로만 보존.
- **레포 역할**: 실험 코드는 DI 드래프트 `playground/agents/damin_v1.py`(전략 스위치 `DAMIN_V1_STRATEGY`)에서
  빠르게, 검증되면 팀 레포 `starter/agent_v1.py`로 이관. PRD/decision_log는 팀 레포에만.
- **현재 병합 상태**: `agent_v1.py` = 정량(R1/R3/R4/R7) + 정성(R2 감지·리셋, R5 open_first, H5). TS 0.820.
- **재검토**: 정성 트랙 info-gain(D6)이 성숙하거나 mode-split이 유의미하면 `agent_v1` 질문 정책 교체.

**EN** — Context: retrieval work (quantitative) and clarification policy (qualitative) ran in parallel. At one
point there were 2 PRDs — `TikTokTechJam/docs/prd_draft.md` (quant-centric) and
`tiktokhackerthon2026_draft/docs/PRD.md` v0.2 (qualitative track). Decision (2026-08-29): (1) **fixed interface,
split tracks** — the qualitative track takes the ranked candidates as input and only decides `ask_attribute`;
core logic unchanged. (2) **PRD consolidation** — the team repo `prd_draft.md` is the single source; the DI
draft's §3 (mode routing), §5 (experiment design), §6 (follow-ups), §8 (risks) are absorbed into `prd_draft.md`
§4.5–4.7 / §8; the DI draft `docs/PRD.md` is marked "SUPERSEDED → team repo" at the top and kept only as history.
Repo roles: experiment code moves fast in the DI draft `playground/agents/damin_v1.py` (strategy switch
`DAMIN_V1_STRATEGY`), then ports to the team repo `starter/agent_v1.py` once validated; PRD/decision_log live only
in the team repo. Current merged state: `agent_v1.py` = quantitative (R1/R3/R4/R7) + qualitative (R2
detect/reset, R5 open_first, H5). TS 0.820. Re-review: swap `agent_v1`'s question policy once the qualitative
track's info-gain (D6) matures or mode-split proves significant.

---

## 참고자료 (외부) / External references

| 주제 / topic | 자료 / source |
|---|---|
| 질문 순서 = 후보 공간 최대 분할 (decision-tree) / question order = max candidate-space split | Wizard of Shopping: Target-Oriented E-commerce Dialogue with Decision Tree Branching — arxiv 2502.00969 |
| 동적 vs 정적 elicitation 전략, stage-aware / dynamic vs static elicitation, stage-aware | When and How to Ask: Dynamic Preference Elicitation Strategies for Conversational Recommendation — SIGIR 2026, arxiv 2607.06765 |
| clarification question 벤치마크 (product search) | ProductAgent: Benchmarking Conversational Product Search Agent with Asking Clarification Questions — arxiv 2407.00942 |
| information-gain 질문 선택 / info-gain question selection | Learning a Strategy for Preference Elicitation in Conversational Recommender Systems — IEEE 2024 (CentAUR 116044) |
| result diversification / MMR (R7의 문헌 위치 / where R7 sits) | Result Diversification in Search and Recommendation: A Survey — arxiv 2212.14464; Carbonell & Goldstein MMR (1998) |
| 대화 이력 누적이 retrieval 정확도에 핵심 (R1) / cumulative dialogue history matters for retrieval (R1) | Learning to Relate to Previous Turns in Conversational Search — arxiv 2306.02553 |

**공통 관찰 / common observation**: 두 preference-elicitation 논문 모두 "여러 턴에 걸쳐 이미 보여준 아이템을
추적·회피하는 것"은 **명시적으로 다루지 않는 gap**이라고 언급. R7은 이 gap을 겨냥 → Innovation & Problem
Insight 심사축 서술 소재. / Both preference-elicitation papers note that tracking and avoiding
already-shown items across turns is an **explicitly unaddressed gap**. R7 targets that gap → material for the
Innovation & Problem Insight axis.
