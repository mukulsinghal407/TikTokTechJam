# TODO — H7 상향 + private robustness / H7 promotion + private robustness

> 2026-08-30 세션 결과. 배경은 이 문서 하단 "맥락" 참조.
> Outcome of the 2026-08-30 session. See "Context" at the bottom.

---

## 확정된 배경 / Established

- **테스트셋 감사 완료 (7개 파일)** / test-set audit done (7 files):
  - `synthetic_500_vivi.jsonl` — **폐기**. ground-truth ASIN 500개 전부 카탈로그에 없음 (랜덤 생성). / discard.
  - `jane_testdataset.jsonl`, `iffa_synthetic_500.jsonl` — **폐기**. damin 재생성 셋이 상위호환 (sample_id 격리, 상관구조 수정). / discard, superseded.
  - `regenerated_test_sets/synthetic_500_set_{1,2,3}_damin.jsonl` — tail 일반화 축. 단 아래 "private 분석"으로 **off-distribution** 판명 → 스트레스용으로만. / tail axis, but off private distribution — stress only.
  - `regenerated_test_sets/public_shuffle_{1,2}_damin.jsonl` — public_set 내용 동일, 행 순서만 셔플. **하네스 결정론 스모크 테스트용**. / determinism smoke test.
- **핵심 발견** / key finding: agent 라인업 전체(`agent_v1` ~ `agent_v2_8`)가 시뮬레이터 템플릿 문자열을 정규식으로 파싱 (`_OVERRIDE_RE`, `_EXHAUST_RE`, `_JUDGMENT_RE`, `"what matters is:"`). private 패러프레이즈 / organizer 작성 intent card 시 상태머신이 눈이 멂. 스펙 `competition_specification.md:40` + `dataset_format.md:70` 이 명시한 리스크 = 너희 PRD **H7 (현재 파킹)**.

---

## TODO (우선순위 순 / by priority)

### P0 — 측정 도구 / measurement first
- [ ] `evaluator/paraphrase_probe.py` — `local_evaluator.py` 안 건드리고 `bench.py` 레벨에서 `user_message` 후처리. 시뮬레이터 템플릿 각각에 손으로 쓴 변형 3–4개, `sample_id` 해시로 결정론적 선택. LLM 없이 시작.
- [ ] `agent_v1`, `agent_v2_8` 을 public + probe 로 실측 → **하락 폭 = 프로토콜 취약도** 기록.

### P1 — H7b 프로토콜 견고성 / protocol robustness
- [ ] override 감지: `_OVERRIDE_RE` → "턴 ∈ {3,4} + 메시지가 'what matters is' 형태 아님" 구조 신호.
- [ ] R7 완화: "전 세션 제외" → "직전 턴만 제외" (override 미감지해도 타깃 영구차단 방지). **IO HitRate 0.97 회귀 주의.**
- [ ] NO_NEW_INFO 3종: 텍스트 매칭 → "직전 2턴 추천 동일" / "새 content word 0개" 행동 신호.
- [ ] `REPLY_NOISE` 하드코딩 → "카탈로그에 존재하는 term 만 쿼리 채택".
- [ ] probe 로 회귀 검증 (IO, Boundary 필수).

### P2 — 검색 견고성 / retrieval (H1b + H7a 흡수)
- [ ] dense/hybrid 리랭킹 — 판별력(F2 rank-1 64% 천장) + 패러프레이즈 recall 헤지 겸용.
- [ ] public train/holdout 분할, holdout 개선까지 확인 (PRD §2 3원칙).
- [ ] probe 에서도 검증.

### P2 — 데이터셋 / datasets
- [x] **`data/holdout_mirror.jsonl` (300) 생성** — candidate-target 풀 재현 (rn 상위 ~3%, disjoint, has-features), public 카테고리·rn 버킷 분포 맞춤, 프로필은 가짜 visible-history 집계. intent_card omit. `tools/gen_holdout_sets.py` (SEED 20260830).
- [x] **`data/holdout_natural_cards.jsonl` (200) 생성** — organizer 스타일 intent_card verbatim 동봉 + 슬라이드 3 스타일 자연어 override. 시나리오 IO 120 / buying 50 / browsing 30.
- [x] **agent_v1 실측 완료** — 아래 "실측 결과" 참조.
- [ ] tail 축(damin s1/s2/s3)은 신규 생성 안 함, off-distribution 스트레스로만 유지.
- [ ] `bench.py agent_v2_8 --vs agent_v1` 를 public + holdout_mirror + holdout_natural_cards + probe 전체에 돌려 대시보드.

### 실측 결과 (agent_v1, 2026-08-30) / measured

| 데이터셋 | TS | HR@10 | 비고 |
|---|---|---|---|
| public_set (기준) | 0.820 | 0.970 | |
| **holdout_mirror** | **0.809** | 0.933 | ≈ public → **특정 200개에 과최적화 아님** ✓ |
| **holdout_natural_cards** | **0.361** | 0.430 | IO HR **0.083** (MTTC 10.44). buying 0.96 / browsing 0.93 은 정상 |
| holdout_natural_cards *(override 문구만 템플릿으로 교체)* | 0.802 | 0.930 | IO HR **0.917** 회복 |

**결론**: 자연어 intent_card 자체는 무해. **override 메시지 패러프레이즈 하나가 IO(15%)를 통째로 날린다.** `_OVERRIDE_RE` 미스 → R2/R7 seen-set 리셋 안 됨 → F4 자책골. 실 private(40/40/15/5) 환산 **≈ −0.05~0.07 TS**.
→ **P1 (R7 완화 + 구조적 override 감지)이 최우선.** probe 없이도 D2 가 증거.

### P3 — 문서 / docs
- [ ] `prd_draft.md` H-table 재배치: **H7b 신설 우선순위 1**, H1a → 2, H7 → H7a 로 개명 후 H1b 병합.
- [ ] `decision_log.md` 에 "H7 상향" 기록 (맥락 → 결정 → 근거 → 재검토 조건).

---

## 아직 결정 필요 / open decisions

1. **P1 R7 완화** — IO HitRate 0.97 건드릴 수 있음. probe 먼저 만들고 함께 볼지 / 지금 별도 실측할지.
2. **probe 수준** — 템플릿 스왑(결정론적)으로 충분한지 / 작은 LLM 패러프레이저까지.
3. **P2 데이터셋** — holdout_mirror 1개로 충분한지 / `stress_thin` 추가.
4. **P0 착수 승인**.

---

## 맥락 / Context — private set 파이프라인 (webinar 슬라이드)

"A reproducible pipeline creates the public and private sets":
- Clothing 5-core **leave-last-out** split 에서 출발 → 각 유저의 마지막 구매 = 타깃, 나머지 = visible history.
- 2,524,981 records → 10,187 catalog-joined → **1,406 distinct candidate targets** → 200 public + 800 private + 50,000 frozen products.
- **organizer-only intent cards** — intent card 는 조직자가 미리 만들어 두고 private 만 비공개로 동봉 (public 은 omit → `intent_card()` 재합성).
- public/private 는 **user 와 target 모두 disjoint**, 결정론적 선택, checksum freeze.

### 시사점 / implications
1. **private 타깃 인기도 ≈ public.** 1,406 풀 ≈ 카탈로그 `rating_number ≳ 1000` 상위 ~3% (1,533개와 근사). → **damin tail 셋(rn 중앙값 12)은 private 분포 밖.**
2. **private 프로필 = 실제 유저 history 집계** (랜덤 태그 아님). 합성 holdout 도 이 방식이어야.
3. **private intent card = 조직자 작성, verbatim 전달** (`materialize_hidden_fields` 가 card 있으면 그대로 사용) → 제약 phrasing·override 메시지가 `intent_card()` 정규식 출력과 다름 → **H7b 가 최고 가치 작업.**
4. user·target 완전 disjoint → 깨끗한 holdout, 동시에 public 200 에 BM25 가중치 튜닝(H1a)은 실제 과최적화 리스크.
