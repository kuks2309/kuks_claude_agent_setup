# [mistake 단위 HIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.
> HIL(Hardware-In-the-Loop 유비 — 실 프로젝트·실 세션) 은 실제 Claude Code 세션에서 수행한다.

## 목적 / 레벨

- 레벨: L2/L3 (실 프로젝트 설치 + 실 세션 동작)
- **수행 프로젝트 / commit**: `<repo>@<hash>` · **반영 일자**: `YYYY-MM-DD`

## 시나리오

1. 실 프로젝트에 `install.sh` 설치 → CLAUDE.md 스니펫·SessionStart 훅 활성 확인
2. 실제 실패 사건 발생 (또는 과거 사건 회고) → `docs/claude-mistake/YYYY-MM-DD-NNN.md` entry 작성
3. `entry-lint.sh` PASS 확인 → INDEX.md 갱신
4. **새 세션 시작** → SessionStart 주입 (INDEX §메타 패턴·§미해결 항목 + open entry) 확인

## 결과

| 케이스 | 측정 | 기대 | 판정 |
| --- | --- | --- | --- |
| 스니펫 트리거 | — | 실패 지적 시 mistake.md Read → entry 기록 유도 | ⏳ |
| entry 작성 형식 | — | entry-lint PASS | ⏳ |
| 세션 주입 | — | 새 세션에서 INDEX 요약·open 목록 노출 | ⏳ |
| closure 루프 | — | reflected_assets 반영 후 closed 전환 | ⏳ |

## 분석 / 결론

(advisory 한계 관찰 포함 — 기록 누락 사례가 있었는지)
