# 검증 결과 인덱스 (전체 요약)

> 단위(L1·L2, 각 번들) + 통합(L3, 상위) **모든 검증 결과의 요약·인덱스**.
> 상세는 각 `YYYY-MM-DD_<topic>/README.md` 에 두고 여기는 한 줄 요약 + 링크만 유지한다.
> 갱신 규칙·열 정의 → [README.md §5](README.md).
> 결과: ✅ PASS · ✗ FAIL · ◐ 부분 · ⏳ 계획됨
> **SIL 행**: 검증은 **다른(타깃) 프로젝트에서 수행 후 반영** — 상세 `README.md` 에 수행 프로젝트(repo·commit)·반영 일자 명시.

---

## 1. 통합 검증 (L3 — 상위 `experiments/`)

| 날짜 | 모드 | 주제 | 결과 | 경로 |
|------|------|------|------|------|
| — | — | _(아직 없음. `SIL/_template/` 또는 `HIL/_template/` 복사 후 추가)_ | ⏳ | — |

계획된 통합 시나리오 (→ [README.md §4.3](README.md)): INT-1 전 번들 설치 · INT-2 멱등 재설치 · INT-3 CI 게이트 일괄 · INT-4 훅 공존(HIL) · INT-5 CLAUDE.md 집계.

---

## 2. 단위 검증 (L1·L2 — 각 번들 `<bundle>/experiments/`)

### 코드 번들

| 번들 | 날짜 | 레벨 | 모드 | 주제 | 결과 | 경로 |
|------|------|------|------|------|------|------|
| acronym | — | — | — | _(없음)_ | ⏳ | [번들](../acronym/experiments/) |
| coding | — | — | — | _(없음)_ | ⏳ | [번들](../coding/experiments/) |
| debt | — | — | — | _(없음)_ | ⏳ | [번들](../debt/experiments/) |

### 설치 번들 (install.sh = L2)

| 번들 | 날짜 | 레벨 | 모드 | 주제 | 결과 | 경로 |
|------|------|------|------|------|------|------|
| code_review | — | — | — | _(없음)_ | ⏳ | [번들](../code_review/experiments/) |
| external_reference | — | — | — | _(없음)_ | ⏳ | [번들](../external_reference/experiments/) |
| git_workflow | — | — | — | _(없음)_ | ⏳ | [번들](../git_workflow/experiments/) |
| issue_fix | — | — | — | _(없음)_ | ⏳ | [번들](../issue_fix/experiments/) |
| sw_structure | — | — | — | _(없음)_ | ⏳ | [번들](../sw_structure/experiments/) |
| user_instruction | — | — | — | _(없음)_ | ⏳ | [번들](../user_instruction/experiments/) |

---

## 3. 커버리지 요약

| 지표 | 값 |
|------|-----|
| 번들 수 | 9 (코드 3 + 설치 6) |
| 단위 검증 완료 | 0 |
| 통합 검증 완료 | 0 |
| 마지막 갱신 | _(계획 수립 — 골격만)_ |
