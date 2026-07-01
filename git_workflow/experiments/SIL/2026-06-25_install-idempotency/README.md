# [git_workflow 단위 SIL] install-idempotency

> `install.sh`(L2 단일 프로그램)의 **멱등 설치·비파괴·경로 SSOT** + **세션 격리 추적 훅** 단위 검증. 검증 대상은 코드(`install.sh`·훅)이며 문서(README 등) 산출물은 대상이 아니다.

## 목적 / 레벨

- 레벨: L2 단일 프로그램 (`install.sh` + `hooks/*.py`)
- **수행 환경 / commit**: `mktemp -d` 격리 샌드박스(+`git init`) · 소스 `kuks_claude_skill_setup` 본 세션 작업 트리(reminder+track 2훅 install) · **반영 일자**: 2026-06-25

## 실행 절차

```bash
SB=$(mktemp -d); git -C "$SB" init -q
git_workflow/install.sh "$SB"        # 1회
git_workflow/install.sh "$SB"        # 2회 (멱등)
grep -c 'kuks_agent_setup:git_workflow' "$SB/CLAUDE.md"            # 기대 1
ls "$SB/docs/claude_guideline/git_workflow/hooks/"                 # reminder + track + stage-gate 3종
# settings.json: UserPromptSubmit(reminder) + PostToolUse(track) + PreToolUse(stage-gate, Bash) 등록 확인
# 세션 격리: 세션 A 가 a.py / 세션 B 가 b.py 수정(track) → 커밋 트리거(reminder) 시
#   A 는 a.py 만, B 는 b.py 만 주입되는지 (.git/git_workflow/sessions/<id>/touched)
# staging 게이트: git add other.py / -A / commit -a → deny, git add mine.py → 통과
ls "$SB/docs/claude_guideline/git_workflow/install.sh"            # 기대: 없음(미복사)
```

## 결과

| 케이스 | 측정 | 기대 | 판정 |
|--------|------|------|------|
| 규칙 파일 복사 | `git_workflow.md` 존재 | docs/claude_guideline/git_workflow/ 존재 | ✅ |
| 훅 3종 복사 | `git_workflow-reminder.py` + `git_workflow-track.py` + `git_workflow-stage-gate.py` 존재 | 훅 복사됨 | ✅ |
| CLAUDE.md marker | `grep -c` = 1 | 1회 (중복 없음) | ✅ |
| settings.json 훅 등록 | UserPromptSubmit(reminder) + PostToolUse(track, matcher=`Write\|Edit\|MultiEdit\|NotebookEdit`) + PreToolUse(stage-gate, matcher=`Bash`) | 3 이벤트 각 1회 | ✅ |
| 재실행 멱등 (CLAUDE.md) | 2회째 "이미 존재 — 스킵" | 중복 append 안 함 | ✅ |
| 재실행 멱등 (settings.json) | 2회째 세 훅 모두 "이미 존재 — 스킵" + `.bak` 백업 | 중복 훅 안 함, 비파괴 | ✅ |
| **세션 격리 주입 (track→reminder)** | 세션 A 커밋 트리거→`a.py` 만, 세션 B→`b.py` 만 주입 | 세션별 분리(타 세션 미혼입) | ✅ |
| **staging 게이트 (stage-gate)** | `git add other.py`/`-A`/`.`/`commit -a`/glob → deny, `git add mine.py`·override → 통과 | 타 세션/광역 캡처 하드 차단 | ✅ |
| 추적 저장 위치 | `.git/git_workflow/sessions/<id>/touched` | `.git` 내부(비-커밋·세션별) | ✅ |
| install.sh/snippet 미복사 | 타깃에 `install.sh` 없음 | 산출물=규칙·훅뿐 | ✅ |

## 분석 / 결론

- **멱등**: 2회 실행에도 CLAUDE.md marker 1회·settings.json 세 훅 각 1회 — 중복 누적 없음. ✅
- **비파괴**: 2회째 기존 `settings.json` 을 `.bak` 으로 백업 후 갱신. 기존 사용자 설정 보존. ✅
- **경로 SSOT**: 규칙·훅은 `docs/claude_guideline/git_workflow/` 한 곳, `install.sh`·`claude.snippet.md` 는 타깃에 누출되지 않음(설치 산출물 = 규칙·훅뿐). ✅
- **세션 격리 주입**: working tree 를 두 세션이 공유해도(`a.py`+`b.py` 동시 dirty), 각 세션의 커밋 트리거는 `.git/git_workflow/sessions/<session_id>/touched` 기반으로 **자기 세션 파일만** 주입받음 → 타 세션 변경 휩쓸기 차단. ✅
- **staging 게이트**: `git add other.py`(타 세션)·`-A`·`.`·`commit -a`·glob 은 deny, `git add mine.py`(소유)·`# gw:allow-foreign` override 는 통과 → 캡처를 **능동 하드 차단**(주입의 advisory 를 강제로 승격). ✅
- **한계**: 격리 샌드박스 기준. track 훅은 Write/Edit 계열만 추적(Bash `mv`·codegen 누락→게이트 override 필요), 게이트 셸 파싱은 휴리스틱(`eval`·`xargs`·alias 우회 가능)·훅 미설치 세션 미보호, python 부재 환경 강등은 HIL 영역.

**판정: PASS** — install.sh 멱등·비파괴·경로 SSOT + 세션 격리 추적·주입·**staging 게이트** 충족.
