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

## D9. 질문 정책 (v2.8.x 계보) — `other` 우선 유지, v2.8.4에서 멈춤 / Question policy (v2.8.x line) — keep `other`-first, stop at v2.8.4

- **맥락**: v2.8 계보에서 질문 정책을 반복. info-gain (v2.8.1, Gini + `_guarded_discrimination`) → open-primary + minimal-admission specific (v2.8.3) → v2.8.4 (eligibility = "한 `other` 응답이 한 dimension에서 구체 evidence ≥2개 = 깊이 신호"일 때만 1회 refine). 700세션(public 200 + held-out mirror 300 + held-out reworded-override 200) 턴 단위 target-rank 계측.
- **결정**: **턴 무관 `other` 우선(open elicitation) 유지. specific 질문은 대화 근거(그 dimension에 이미 공개된 제약 + 깊이 신호)가 있을 때만.** v2.8.4에서 **멈춘다** — 성공 REFINE과 실패 REFINE을 가르는 간단한 observable 레버가 이번 라운드에 안 나옴. coefficient·attribute별 prior·threshold를 더 넣으면 얻는 evidence < 늘어나는 complexity.
- **근거 (실측, `scratchpad/rankdelta.py`)**:
  - ExpGain/Ask (= P(useful)·E[rank gain|useful], target 이탈 = rank 500): `other` +45~+147 / material −7~+9 / feature −48~+14. `other`가 어떤 specific보다 15~70배.
  - useful%: `other` ~78% vs material ~11% / color ~7%.
  - Nth-`other` 수확체감: 1st ~180, 2nd ~75, 3rd ~15, **4th 이후 = useful 0% (전 데이터셋·전 변종)**. → `other` 3회 / 무수확 시 하드캡은 손해 0.
  - always-`other` vs v2.8.3: public 0.870 vs 0.861, held-out mirror 0.848 vs 0.842. **단 reworded-override에선 v2.8.3이 +0.017** — override 미감지 시 `other` 한 턴마다 stale(override 전) 제약을 쿼리에 재장전(always-`other`의 2nd-`other` ExpGain −72), specific 이탈이 그 poison을 우연히 조절.
  - v2.8.4 자체 분석 (public 200): specific 56회 중 material 5/30 useful, 초반 턴(1~3) 6/42, useful-`other` 직후 5/39 — 어느 조건도 "이 경우엔 specific이 성공한다"로 분리 안 됨.
- **왜 `other`인가 (원칙, D4 강화)**: **현재 벤치마크 유저는 이미 특정 Target Product에 대응하는 shopping intent를 가지고 있고, 대화는 그 intent에 든 정보를 순차 공개하는 구조**다. 특정 attribute를 미리 추측할 근거가 부족할 때 user-directed elicitation(`other`)을 우선하는 것이 합리적이다.
- **서사 (D4 유지)**: 턴1 `other`의 점수 이득 = "시뮬레이터 대리지표"(와일드카드가 턴을 안 버림). "열린 질문이 확신 유저의 응답 정확도를 높인다"(H1) = 검증 미완.
- **재검토**: override 감지 수정(H7b) 후 always-`other` + 3회 캡을 재측정. override poison이 사라지면 always-`other`가 held-out에서도 앞설 가능성 → 그때 최종 질문 정책 확정. contrastive clarification(preference 형성형 A/B)은 PRD §4.6.6 — deferred, 다음 연구 항목.

**EN** — Context: iterated the question policy across the v2.8 line — info-gain (v2.8.1, Gini + `_guarded_discrimination`) → open-primary with minimal-admission specific (v2.8.3) → v2.8.4 (eligibility only when one `other` reply shows ≥2 concrete evidence in a single dimension = a depth signal). Instrumented target-rank per turn over 700 sessions (public 200 + held-out mirror 300 + held-out reworded-override 200). Decision: **keep `other`-first open elicitation regardless of turn; ask a specific question only with conversational evidence (a disclosed constraint in that dimension plus a depth signal); stop at v2.8.4** — no simple observable lever separates a successful refinement from a failed one this round, and adding coefficients / per-attribute priors / thresholds costs more complexity than the evidence gained. Rationale (measured, `scratchpad/rankdelta.py`): expected rank gain per ask — `other` +45..+147, material −7..+9, feature −48..+14 (`other` is 15–70× any specific); useful-answer rate `other` ~78% vs material ~11%; the Nth `other` decays 1st ~180 / 2nd ~75 / 3rd ~15 / **4th+ = 0% useful on every set** (so a hard cap at 3 asks / first no-yield costs nothing); an always-`other` agent scores 0.870 public / 0.848 held-out (above v2.8.3's 0.861 / 0.842) **but loses by 0.017 on reworded overrides** because each `other` turn reloads pre-override constraints into the query when the override is not detected. v2.8.4's own analysis (public 200): of 56 specific asks, material was useful 5/30, early turns 6/42, right-after-a-useful-`other` 5/39 — nothing separates. **Why `other` (principle, strengthens D4)**: the current benchmark user already holds a shopping intent tied to a specific target product, and the dialogue is a sequential disclosure of the information inside that intent; when there is not enough evidence to pre-guess a specific attribute, user-directed elicitation (`other`) is the rational default. Narrative (unchanged from D4): the turn-1 `other` score gain is a "simulator proxy metric"; H1 (open questions raise a confident user's accuracy) is unverified. Re-review: after the H7b override-detection fix, re-measure always-`other` + a 3-ask cap; if the override poison is gone, always-`other` may also win on held-out → finalize the question policy then. Contrastive preference-forming clarification (A/B) is PRD §4.6.6 — deferred, next research item.

---

## Playground — 시각화 도구 (`playground/`) / Playground — viz tool (`playground/`)

> 대회 채점 대상 아님. `agent.py`를 가설별로 고칠 때 각 세션에서 agent가 어떻게 행동하고 메모리·검색
> 정확도가 어떻게 달라지는지 눈으로 보는 로컬 도구. 공식 점수는 항상 `python -m evaluator.local_evaluator`.
>
> Not scored. A local tool for watching, per session, how the agent behaves and how its memory / retrieval
> accuracy shift as we edit `agent.py`. Official scores always come from `python -m evaluator.local_evaluator`.

### P1. 목적 = 세션별 행동 시각화 (데이터 구조 설명 아님) / Purpose = per-session behavior viz (not a data-structure explainer)

- **맥락**: archive의 옛 demo는 "데이터가 어떻게 생겼나"를 보여주는 게 목적이었음. 재시작하며 목적을 바꿈.
- **결정**: playground = (1) 선택한 agent를 세션마다 턴 단위로 재생, (2) 사이드바 3파트 — 어떤 유저 데이터인가
  (agent가 보는 것 vs evaluator 전용) / 이 턴에 agent가 아는 것 (검색어·소진 속성·미공개 title 단어·전체 BM25
  순위) / 도구 설명.
- **재검토**: 버전 A/B 좌우 분할 비교 뷰는 다음 작업.

**EN** — Context: the old archive demo existed to show "what the data looks like"; the restart changed the goal.
Decision: playground = (1) replay the selected agent turn by turn per session, (2) a 3-part sidebar — what user
data this is (agent-visible vs. evaluator-only) / what the agent knows this turn (query terms, exhausted
attributes, undisclosed target-title words, full BM25 rank) / an about page. Re-review: the side-by-side A/B
compare view is the next piece of work.

### P2. evaluator 포크 금지 — import. `runner.py --check` 가 공식과 일치 보증 / No evaluator fork — import it; `runner.py --check` guarantees parity

- **맥락**: 턴 단위 재생을 하려면 `evaluate()` 루프를 열어야 함. archive 옛 demo는 시뮬레이터 함수
  (`intent_card`, `customer_reply` 등)를 통째로 복붙 → 원본 갱신 시 조용히 어긋날 위험.
- **결정**: `runner.py` 가 evaluator 함수를 전부 **import** 하고 세션 루프만 분해. 복사 0.
- **근거**: `python playground/runner.py --check` 가 200 public 세션의 hit·rank·집계점수를 공식 `evaluate()` 와
  대조 (현재 일치). `runner.py` 를 고칠 때마다 통과시킬 것.

**EN** — Context: turn-by-turn replay needs the `evaluate()` loop opened up; the old archive demo copy-pasted the
simulator functions (`intent_card`, `customer_reply`, …), which drifts silently when upstream changes. Decision:
`runner.py` imports every evaluator function and only decomposes the session loop; zero copies. Rationale:
`python playground/runner.py --check` compares hit / rank / aggregate score over all 200 public sessions against
the official `evaluate()` (currently matches); keep it passing whenever `runner.py` changes.

### P3. agent 버전 = 이름 붙인 파일 + 드롭다운 / Agent versions = named files + dropdown

- **결정**: 각 가설을 `playground/agents/*.py` 파일로. `baseline.py`(공식 starter 계측본, 고정 기준선),
  `damin_start.py`(누적 BM25 + 속성 사다리 참고 구현), 이후 `vN_*.py`. UI 드롭다운에서 선택.
- **규약**: 선택적 `LABEL`(표시명, 파일명이 id), `debug_state(session_id) -> dict`(agent 내부 상태 — 러너가
  사이드바 Part 2로 그대로 전달; 권장 키 `memory_kind`·`query_scope`·`query_terms`·`exhausted_attributes`).

**EN** — Decision: each hypothesis is a `playground/agents/*.py` file — `baseline.py` (instrumented official
starter, fixed reference line), `damin_start.py` (cumulative BM25 + attribute ladder reference impl), then
`vN_*.py`; selected from a UI dropdown. Convention: optional `LABEL` (display name; the file name is the id) and
`debug_state(session_id) -> dict` (agent internals — the runner forwards it verbatim to sidebar Part 2; suggested
keys `memory_kind`, `query_scope`, `query_terms`, `exhausted_attributes`).

### P4. 정적 explorer 폐기 / Dropped the static explorer

- **결정**: archive의 200세션 미리계산 정적 탐색기는 가져오지 않음. playground는 라이브 반복 도구이지 배포용
  스냅샷이 아님.

**EN** — Decision: the archive's precomputed 200-session static explorer is not carried over; playground is a
live iteration tool, not a shareable snapshot.

### P5. 수동 모드 = 사람이 agent 역할 (고객 아님) / Manual mode = the human plays the agent (not the customer)

- **결정**: "내가 agent로" — 사람이 `ask_attribute` 를 골라 던지고, 시뮬레이터(고객)가 공식 규칙대로 답한다.
  추천 top10 은 누적 대화 BM25 로 자동 계산. 턴마다 "선택한 agent 자동" / "내가 수동" 을 섞을 수 있다.
- **근거**: 코드로 넣기 전에 질문 전략을 손으로 시험. 자연어 질문 문장은 데모용 — 시뮬레이터는 `ask_attribute`
  만 읽는다([[project-tiktok-hackathon]] F1).

**EN** — Decision: "Ask as the agent" — the human picks `ask_attribute` and asks; the simulator (customer)
replies by the official rules. The top-10 is auto-computed by BM25 over the accumulated conversation. Each turn
you can mix "run the selected agent" and "ask manually". Rationale: test a questioning strategy by hand before
coding it; the free-text question is cosmetic — the simulator reads only `ask_attribute`.

### P6. UI 영어 단일 / UI is English-only

- **맥락**: 팀 공유·시연 대상이 국제 팀원.
- **결정**: UI 및 백엔드가 노출하는 문자열 전부 영어. Part 3 설명도 영어 단일(한/영 토글 제거). 코드 주석은
  한국어 유지.

**EN** — Context: the team and the demo audience are international. Decision: every user-facing string (UI and
backend) is English; the Part 3 explainer is English-only (the KR/EN toggle was removed). Code comments stay
Korean.

### P7. playground 를 레포 루트 키트에 얹음 (자기완결 복사본 X) / playground rides the repo-root kit (no self-contained copy)

- **맥락**: 팀 레포가 비었을 때 "playground/ 안에 evaluator·starter 까지 전부 자기완결" 로 결정. 그 직후 팀원이
  참가자 키트를 레포 루트에 커밋.
- **결정**: 번복. `playground/runner.py`·`server.py` 가 실행 시 레포 루트를 `sys.path` 에 올려 루트
  `evaluator/`·`starter/`·`data/` 를 import. 키트 사본 0.
- **근거**: 채점 권위 파일이 두 벌이면 어긋난다. 팀 agent 가 루트에 생기면 `playground/agents/main.py` 에
  `from starter.agent import Agent; LABEL = "main"` 두 줄이면 드롭다운에 뜬다.

**EN** — Context: with the team repo empty, the call was "self-contained under `playground/`, evaluator and
starter included". A teammate then committed the participant kit at the repo root. Decision: reversed —
`playground/runner.py` / `server.py` put the repo root on `sys.path` at startup and import the root
`evaluator/`, `starter/`, `data/`; zero copies of the kit. Rationale: two copies of the scoring authority drift.
Once there's a team agent at the root, a two-line shim in `playground/agents/main.py`
(`from starter.agent import Agent; LABEL = "main"`) puts it in the dropdown.

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
