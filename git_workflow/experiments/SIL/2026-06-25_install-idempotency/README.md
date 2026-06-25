# [git_workflow 단위 SIL] install-idempotency

> `install.sh`(L2 단일 프로그램)의 **멱등 설치·비파괴·경로 SSOT** 단위 검증. 검증 대상은 코드(`install.sh`)이며 문서(README 등) 산출물은 대상이 아니다.

## 목적 / 레벨

- 레벨: L2 단일 프로그램 (`install.sh`)
- **수행 환경 / commit**: `mktemp -d` 격리 샌드박스 · 소스 `kuks_claude_skill_setup@36843a0` (검증 시점; `install.sh` 는 68c6dbf 까지 byte-identical — README 커밋이 install.sh 미변경) · **반영 일자**: 2026-06-25

## 실행 절차

```bash
SB=$(mktemp -d)
git_workflow/install.sh "$SB"        # 1회
git_workflow/install.sh "$SB"        # 2회 (멱등)
grep -c 'kuks_agent_setup:git_workflow' "$SB/CLAUDE.md"      # 기대 1
ls "$SB/docs/claude_guideline/git_workflow/"                 # 규칙 + hooks
grep -c 'git_workflow-reminder.py' "$SB/.claude/settings.json"  # 기대 1
ls "$SB/docs/claude_guideline/git_workflow/install.sh"       # 기대: 없음(미복사)
```

## 결과

| 케이스 | 측정 | 기대 | 판정 |
|--------|------|------|------|
| 규칙 파일 복사 | `git_workflow.md` + `hooks/` 존재 | docs/claude_guideline/git_workflow/ 존재 | ✅ |
| 훅 복사 | `hooks/git_workflow-reminder.py` 존재 | 훅 복사됨 | ✅ |
| CLAUDE.md marker | `grep -c` = 1 | 1회 (중복 없음) | ✅ |
| settings.json 훅 등록 | `grep -c` = 1 | 1회 등록 | ✅ |
| 재실행 멱등 (CLAUDE.md) | 2회째 "이미 존재 — 스킵" | 중복 append 안 함 | ✅ |
| 재실행 멱등 (settings.json) | 2회째 "이미 존재 — 스킵" + `.bak` 백업 | 중복 훅 안 함, 비파괴 | ✅ |
| install.sh/snippet 미복사 | 타깃에 `install.sh` 없음 | 산출물=규칙·훅뿐 | ✅ |

## 분석 / 결론

- **멱등**: 2회 실행에도 CLAUDE.md marker 1회·settings.json 훅 1회 — 중복 누적 없음. ✅
- **비파괴**: 2회째 기존 `settings.json` 을 `.bak` 으로 백업 후 갱신. 기존 사용자 설정 보존. ✅
- **경로 SSOT**: 규칙은 `docs/claude_guideline/git_workflow/` 한 곳, `install.sh`·`claude.snippet.md` 는 타깃에 누출되지 않음(설치 산출물 = 규칙·훅뿐). ✅
- **한계**: 격리 샌드박스 기준. 실제 멀티-훅 공존(다른 번들과 settings.json 동시 등록)·python 부재 환경 강등은 HIL 영역.

**판정: PASS** — install.sh 멱등·비파괴·경로 SSOT 충족.
