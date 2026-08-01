# mistake entry-lint — record-skip category 수용

## 2026-08-01 17:45 (KST) — VIOLATION_CATS 에 record-skip 추가

- 대상: `VIOLATION_CATS` (`mistake/checks/entry-lint.sh:41-42`)
- 변경: rule-violation category enum 집합에 `record-skip` 1개 추가 (6종 → 7종). 로직 변경 없음.
- 사유: `mistake/mistake.md` §카테고리 정의에 `record-skip`(기존 기록 검토 의무 위반) 신설 — 규칙 enum 과 lint enum 의 정합 유지. 합성 entry 실사격으로 record-skip PASS·미지 category FAIL·전체 통과 exit 0 확인.
- 커밋: f10af9c
