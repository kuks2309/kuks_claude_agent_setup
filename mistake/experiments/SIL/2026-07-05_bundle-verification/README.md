# [mistake 단위 SIL] bundle-verification

> **SIL(Software-In-the-Loop) 수행 위치**: mktemp 샌드박스 타깃(비-git)에서 수행 후 결과 반영.

## 목적 / 레벨

- 레벨: L2 (`install.sh`) + L1 (`checks/entry-lint.sh`, `hooks/mistake-inject.py`)
- **수행 프로젝트 / commit**: 샌드박스 타깃 (scratchpad mktemp) · 번들 = `kuks_claude_skill_setup@작업본(커밋 전, v3 이식 세션)` · **반영 일자**: 2026-07-05

## 실행 절차

```bash
SB=$(mktemp -d)
mistake/install.sh "$SB"     # 1회
mistake/install.sh "$SB"     # 2회 (멱등)
grep -c 'kuks_agent_setup:mistake' "$SB/CLAUDE.md"                    # 1
(cd "$SB" && ./docs/claude_guideline/mistake/checks/entry-lint.sh)    # 0건 PASS → 정상 2건 PASS → 위반 주입 FAIL
CLAUDE_PROJECT_DIR="$SB" python3 .../hooks/mistake-inject.py </dev/null
```

정상 entry 는 v2 dogfooding 검증분 2건(재분류 시나리오 포함), 위반 entry 는 type↔category 불일치·closed+owner·TBD(To Be Determined)·5절 누락·open 7일 초과를 합성 주입.

## 결과

| 케이스 | 측정 | 기대 | 판정 |
| --- | --- | --- | --- |
| 규칙·이빨·훅 복사 | mistake.md + checks/ + hooks/ 생성 | 존재 | ✅ |
| entry 폴더 생성 | docs/claude-mistake/ 생성 | 존재 (비파괴) | ✅ |
| CLAUDE.md marker | grep -c = 1 (2회 설치 후) | 1회 | ✅ |
| SessionStart 훅 등록 | settings.json 그룹 1개, 2회째 "스킵" + `.bak` 백업 | 1회 | ✅ |
| entry-lint: 0건 | "검사 대상 entry 0 건 (PASS)" exit 0 | PASS | ✅ |
| entry-lint: 정상 2건 | 2건 PASS exit 0 | PASS | ✅ |
| entry-lint: 위반 검출 | 불일치·closed+owner·TBD·5절 누락 4건 동시 검출 exit 1 | FAIL 검출 | ✅ |
| entry-lint: 7일 초과 | "open 15일 경과" 검출 exit 1 | FAIL 검출 | ✅ |
| 훅: 주입 | INDEX §메타 패턴·§미해결 항목 + open entry 목록 출력, exit 0 | 주입 | ✅ |
| 훅: 무출력 | 기록 없는 프로젝트에서 출력 0 바이트, exit 0 | no-op | ✅ |

## 분석 / 결론

전 케이스 PASS. 경로 SSOT(Single Source of Truth) 준수(`docs/claude_guideline/mistake/` + `docs/claude-mistake/`), 비파괴(append/merge·`.bak` 백업), 판정 정확도(오탐 0·미탐 0) 확인. HIL(실 프로젝트·실 세션 SessionStart 발화) 은 후속 설치 시 수행.
