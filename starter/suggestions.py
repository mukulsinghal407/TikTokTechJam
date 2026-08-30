"""

ALL COMMENTS FROM THE VERSION HISTORY OF agent_v2_8 ARE PRESERVED BELOW. DO NOT DELETE.


"""




"""agent_v2_8 — 통합 단일 파일. agent_v2(통계 모델링) 계보를 v2_1~v2_7 개선분과 함께 평탄화.

agent_v2_8 — consolidated single file: the agent_v2 (statistical-modeling) lineage flattened
             together with the v2_1–v2_7 improvements.

한 줄 / One line:
  시뮬레이터를 최소한으로 이용하는 원칙적 설계 + agent_v1 에서 배운 두 레버(R7 / 열린 질문). LLM 미사용.
  A principled design that leans on the simulator minimally + the two levers learned from agent_v1
  (R7 exposure suppression / turn-1 open question). No LLM.

실측 / Measured (public_set 200): TS 0.855 / HitRate@10 1.000 / MRR 0.635 / MTTC 2.79 / 토큰 0.
  (agent_v1 0.820, damin_start 0.724, 원본 agent_v2 / original agent_v2 0.682)

가설 검증 이력은 파일 하단 주석 참조. 상세 설계 결정은 `docs/decision_log.md`.
Hypothesis-test history is in the bottom comment; design rationale in `docs/decision_log.md`.
"""






# ===========================================================================
# agent_v2 대비 개선 이력 (가설 → 검증 → 판정). 상세: docs/decision_log.md
# Improvements over agent_v2 (hypothesis → test → verdict). Detail: docs/decision_log.md
# ===========================================================================
#
#  v2   (baseline) 멀티라우트 retrieval + typed evidence + risk-gated 스코어링          TS 0.682
#       + coverage portfolio + info-gain 질문. R7·open_first 없음이 치명적 (agent_v1 0.820).
#       (baseline) multi-route retrieval + typed evidence + risk-gated scoring
#       + coverage portfolio + info-gain questioning. No R7 / open_first — fatal.
#
#  v2.1 + R7 (이전 노출 상품 억제, exposure_decay 노브) + open_first + candidate_limit 400.  TS 0.828
#       bm25 bound-param → SQL 리터럴 수정. v2 는 추천 슬롯의 57% 를 재노출하고 있었다.
#       + R7 (exposure suppression, exposure_decay knob) + open_first + candidate_limit 400.
#       bm25 bound-param → SQL literal fix. v2 was re-showing 57% of its rec slots.
#
#  v2.2 override 시 이전 evidence SUPERSEDE 취소 (누적 유지). IO .87 → 1.00.               TS 0.849
#       시뮬레이터 old_value 는 타깃 파생이라 죽이면 손해 (decision_log D2).
#       Undo the SUPERSEDE of old evidence on an override (keep accumulating). IO .87 → 1.00.
#       The simulator's old_value is target-derived, so dropping it backfires (D2).
#
#  v2.3 (폐기 / dead) info-gain × yield_prior — brand 쏠림을 못 고침. D6 재확인.           TS 0.847
#       (dead) info-gain × yield_prior — did not fix the brand skew. Re-confirms D6.
#
#  v2.4 H5 소진 감지 ("no additional preference for X" / "use your judgment")             TS 0.848
#       → 같은 속성 반복 질문 정지.
#       H5 exhaustion detection → stop re-asking the same attribute.
#
#  v2.5 sticky mining — 수율 나는 속성을 소진 전까지 계속 캔다 (v1 퍼널의 depth-first     TS 0.854
#       채굴 복원). breadth-first → depth-first. boundary .80 → .90.
#       sticky mining — keep mining a yielding attribute until dry (restores v1's
#       depth-first funnel). breadth-first → depth-first. boundary .80 → .90.
#
#  v2.6 (폐기 / dead) split-quality 댐프너 — brand 쏠림을 budget 쏠림으로 바꿨을 뿐.      TS 0.843
#       (dead) split-quality dampener — merely traded the brand skew for a budget skew.
#
#  v2.7 BM25 features 가중 ×1.5 (title ÷√1.5). 시뮬레이터가 제약을 features/details       TS 0.857
#       에서 뽑기 때문 (구조적, public-fit 아님). HR .995 → 1.000. ⚠️ 배수는 holdout 재검증.
#       BM25 features weight ×1.5 (title ÷√1.5) — the simulator draws constraints from
#       features/details (structural, not public-fit). HR .995 → 1.000. ⚠️ re-validate the multiplier.
#
#  v2.8 ablation 으로 기여 0 성분 제거: _history_rank_boost (Δ 0), broad-category route   TS 0.855
#       (Δ −0.0006), verified_violation_penalty (Δ −0.0014), + 순수 dead 코드 (_sigmoid,
#       *_history 필드, Evidence.confidence/source_turn, NEGATIVE status 분기, NEGATION_MARKERS).
#       −0.002 (노이즈). 코드·과최적화 표면적 축소. 그리고 8단 서브클래스 체인을 이 단일 파일로 통합.
#       Ablation-driven removal of zero-contribution parts: _history_rank_boost (Δ 0),
#       broad-category route (Δ −0.0006), verified_violation_penalty (Δ −0.0014), + pure dead code
#       (_sigmoid, *_history fields, Evidence.confidence/source_turn, the NEGATIVE branch,
#       NEGATION_MARKERS). −0.002 (noise). Shrinks code + overfit surface. Also flattens the
#       8-level subclass chain into this one file.
#
#  유지된 성분 (ablation 상 제거하면 손해) / Kept (removal hurts, per ablation):
#    _quality_prior (−0.008), coverage portfolio (−0.005 — DI 가설과 달리 도움 / helps, contra DI's
#    hypothesis), explicit route (−0.007), carryover ×0.78 (−0.007), profile_importance (−0.006).
#    −ALL 을 한꺼번에 제거하면 −0.022 (성분들이 compound). / Removing −ALL at once = −0.022 (they compound).
#
#  현재 지표 (public 200) / Current metrics (public 200):
#    TS 0.855 / HR 1.000 (200/200) / MRR 0.635 / MTTC 2.79 / 토큰 0 / tokens 0.
#    시나리오별 MRR / MRR by scenario: buying .653 / browsing .624 / intent_override .568 / boundary .777.
#    rank 분포 / rank distribution: rank1 52% / 2-3 15% / 4-5 14% / 6-10 19% / miss 0%.
#
#  ⚠️ public 200 에만 튜닝·검증됨. private 800 미확인. HR 1.000 이 private 에서 유지될 가능성은 낮다
#     (yield 분포·BM25 배수·sticky 임계 전부 public 실측 기반).
#     Tuned and validated on public 200 only. The private 800 is unseen. HR 1.000 is unlikely to hold
#     on private (the yield distribution, BM25 multiplier, and sticky threshold are all from public data).
#
#  개선 후보 / Improvement candidates:
#    1. MRR — rank 4+ 그룹(33%). semantic rerank / 리랭킹 정밀도.
#       MRR — the rank-4+ group (33%). semantic rerank / reranking precision.
#    2. 질문 순서 — info-gain 이 material 보다 brand/style 을 먼저 본다 (HR 1.000 이라 이제 MTTC 만 깎음).
#       문헌 순서(use_case/style/feature/color/material > brand/budget) 약한 tint 는 미검증.
#       Question order — info-gain ranks brand/style ahead of material (only costs MTTC now that HR is
#       1.000). A weak tint toward the literature order (use_case/style/feature/color/material >
#       brand/budget) is untested.
#    3. IO MRR 0.568 (평균 rank 3.27). MTTC 4.63 은 override_applied 게이트상 하한.
#       IO MRR 0.568 (avg rank 3.27). MTTC 4.63 is a floor imposed by the override_applied gate.