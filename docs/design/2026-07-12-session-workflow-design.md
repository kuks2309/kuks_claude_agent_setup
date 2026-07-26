# 세션 워크플로 설계 — 다중 세션 진행·종료 생애주기 (session_workflow 번들)

> 상태: 설계 승인됨(2026-07-12) · 대상: 신규 번들 `session_workflow/` · 선행 설계: 2026-07-01 세션 격리(기록·staging 층)

## 1. 문제

한 워크스페이스(예: VSCode 한 창의 다중 탭)에서 **동시 다중 세션**을 운영할 때, 기록 격리(user_instruction)와 staging 격리(git_workflow)는 확보됐으나 **세션 생애주기 절차층이 없다**:

1. **목적 부재** — 세션이 무엇을 하는 세션인지 선언되지 않아, 세션 산출 문서 생성·진행 기준이 불명확하고 세션 간 역할 구분이 사후에야 드러난다.
2. **충돌 늦은 발견** — 두 세션이 같은 파일을 수정 중이어도 commit 시점(stage-gate)에야 걸린다. 진행 중 조기 경보가 없다.
3. **종료 절차 부재** — 세션을 닫을 때 미커밋 산출물·미완 작업이 점검 없이 증발한다. 다음 세션으로의 인수인계 채널이 없다.

## 2. 목표 / 비목표

**목표**

- 세션 시작 시 **목적 선언을 강제**(훅 결정적 게이트 — 모델 준수 비의존)하고, 목적을 레지스트리·충돌 경보·종료 handoff·세션 문서의 기준점으로 삼는다.
- 활성 세션 레지스트리로 새 세션이 **시작 시점에** 다른 세션의 존재·목적·작업 파일을 인지한다.
- 두 활성 세션의 수정 파일이 겹치면 **진행 중 조기 경보**한다.
- 종료 시 미커밋 산출물을 **결정적으로 감지**해 handoff 로 박제, 다음 세션이 인수인계받는다.
- 완전 자기완결 — 타 번들(user_instruction·git_workflow)·OMC 비의존, 자체 추적. graceful(git/python 부재 시 no-op).

**비목표**

- staging 강제(git_workflow stage-gate 소관 — 본 번들은 차단하지 않고 경보만).
- 지시 원문 기록(user_instruction 소관).
- 세션 간 실시간 통신·작업 분배 오케스트레이션.
- 라인 단위 충돌 감지(파일 단위만).

## 3. 번들 구조

```
session_workflow/
  session_workflow.md        # 생애주기 SOP 규칙 SSOT (지시용, self-contained — 자매 SSOT 링크 0)
  claude.snippet.md          # 타깃 CLAUDE.md 등록 스니펫
  install.sh                 # 복사 + snippet append + settings.json 훅 멱등 등록
  hooks/
    session_workflow-start.py   # SessionStart
    session_workflow-gate.py    # UserPromptSubmit
    session_workflow-track.py   # PostToolUse (Edit|Write|NotebookEdit)
    session_workflow-end.py     # SessionEnd
```

**상태 저장소** — `.git/session_workflow/` (git 내부라 비커밋·`.gitignore` 불요, git_workflow 와 같은 관례):

```
.git/session_workflow/
  active/<session_id>.json     # {purpose, started_at, last_seen, alerted[]}  (KST)
  active/<session_id>.touched  # 이 세션이 수정한 파일 (repo 상대경로, 줄당 1개, dedup)
  handoff/<session_id>.md      # 종료 시 미커밋 잔여 인수인계 (목적·파일 목록·시각)
```

각 세션은 **자기 이름의 파일에만 쓴다** → 공유 파일 rewrite 가 없어 flock 불요(경합 구조적 부재). 읽기는 타 세션 파일 허용(경보·레지스트리 조회 목적 — 지시 기록과 달리 메타데이터라 교차 누수 아님).

## 4. 훅 설계

### 4.1 session_workflow-start.py (SessionStart)

- `active/<session_id>.json` 을 `purpose: null` 로 등록.
- additionalContext 주입:
  1. **활성 세션 목록** — 타 세션의 short8 id·목적·last_seen. `last_seen` 이 오래된(>24h) 항목은 "잔류 의심(비정상 종료 가능)"으로 표시하고 그 touched 목록 노출.
  2. **대기 handoff 요약** — `handoff/*.md` 의 목적·미커밋 파일 목록(최근 순 최대 5개).
  3. **목적 게이트 예고** — "본 세션 목적 미선언. 첫 응답에서 사용자에게 목적을 묻고 `목적: …` 형식 입력을 안내하라."
- 부수 정리: handoff 14일 경과분 삭제, 잔류 active 항목은 삭제하지 않음(잔류 표시만 — touched 정보 보존).

### 4.2 session_workflow-gate.py (UserPromptSubmit)

- 프롬프트가 `목적:`(또는 `purpose:`, 대소문자 무관)으로 시작하면 그 뒤 원문을 **verbatim** 으로 `purpose` 에 등록하고 "목적 등록 완료: <원문>" 주입. 재선언 시 덮어쓰기(갱신 허용).
- `purpose == null` 이면 **매 프롬프트마다** 주입: "본 세션 목적 미등록 — 실질 작업 전에 사용자에게 목적 1줄을 요청하라(`목적: …`)." 프롬프트 자체는 차단하지 않는다(hard block 은 단발 질문 세션에 적대적 — 반복 주입이 강제 수단).
- **충돌 경보** — 이 세션 `.touched` 와 다른 활성 세션 `.touched` 의 교집합 검사. **신규 교집합만** 경보(경보한 파일은 `alerted[]` 에 기록해 중복 노이즈 방지): "파일 X 는 세션 Y(목적: Z)도 수정 중 — 사용자에게 계속/범위 조정 1줄 확인." 
- `last_seen` 갱신.

### 4.3 session_workflow-track.py (PostToolUse, matcher `Edit|Write|NotebookEdit`)

- `tool_input.file_path` 를 repo 상대경로로 `.touched` 에 append(dedup). git_workflow-track 과 독립(자체 데이터·자체 경로 — 번들 자기완결).

### 4.4 session_workflow-end.py (SessionEnd)

- 자기 `.touched` 를 읽어 `git status --porcelain -- <paths>` 로 **미커밋 파일** 감지.
- 미커밋 있으면 `handoff/<session_id>.md` 작성: 목적, 시작·종료 시각(KST), 미커밋 파일 목록, touched 전체 요약. 없으면 handoff 생략(노이즈 최소).
- 자기 `active/<id>.json`·`.touched` 삭제(레지스트리 해제). 타 세션 파일 불가침.

**공통 graceful 규약** — 모든 훅: (1) 활성화 게이트 = `docs/claude_guideline/session_workflow/session_workflow.md` 존재, (2) `.git` 디렉터리 부재 시 no-op, (3) 최상위 try/except 로 어떤 실패도 exit 0(세션 진행 방해 금지), (4) python3 부재 시 등록만 남고 미동작(규칙 텍스트 생존).

## 5. 생애주기 SOP (session_workflow.md 에 담을 절차)

| 단계 | 주체 | 내용 |
|------|------|------|
| **시작** | 훅 | 레지스트리 등록, 활성 세션·handoff·게이트 예고 주입 |
| | 모델 | 사용자에게 목적 질문 → `목적: …` 등록 확인 → 타 세션 목적·handoff 와 겹치면 시작 시점에 범위 조정 1줄 확인 |
| **진행** | 훅 | 수정 파일 추적, 신규 충돌 경보, last_seen 갱신 |
| | 모델 | 경보 수신 시 사용자 1줄 확인(계속/중단/범위 조정) 후 진행. 이 세션 산출물만 수정 원칙 |
| **종료(명시)** | 모델 | 사용자 "세션 종료" 선언 시: 미커밋 산출물 확인 → 커밋 여부 사용자 확인(이 세션 touched 만 명시 staging) → 결과 기록(worklog 등, 제목에 세션 목적 사용) → 닫기 안내 |
| **종료(결정적)** | 훅 | SessionEnd 가 미커밋 잔여를 handoff 로 박제 + 레지스트리 해제 — 명시 절차 생략돼도 유실 없음 |
| **인수인계** | 모델 | 다음 세션이 시작 주입에서 handoff 확인 → 사용자 동의 하에 픽업 → 처리 완료 후 handoff 파일 삭제 |

2단 방어: 명시 종료 SOP(모델)가 1차, SessionEnd 훅(결정적)이 2차 — 모델·사용자가 절차를 잊어도 훅이 잔여를 박제한다.

## 6. 엣지 케이스 & 트레이드오프

| 항목 | 처리 |
|------|------|
| 비정상 종료(탭 강제 종료 등 SessionEnd 미발화) | active 잔류 → 다음 SessionStart 가 "잔류 의심" 표시 + touched 노출로 수동 회수. 자동 handoff 승격은 하지 않음(살아있는 세션 오판 위험) |
| 단발 질문 세션의 목적 마찰 | `목적: 단발 질문` 한 줄이면 게이트 해제 — 마찰 1회로 수용 |
| 두 세션 동시 종료 | 각자 자기 파일만 쓰므로 경합 없음(flock 불요) |
| Bash 로만 생성한 파일 | track 미추적(도구 matcher 한계, git_workflow 와 동일) — SOP 에 정직하게 명시 |
| 충돌 경보 무시 | 경보는 권고 — 강제 차단은 git_workflow stage-gate 소관(계층 분리). 본 번들이 중복 차단하지 않음 |
| 목적 verbatim 등록 | 민감정보 의미 마스킹 불가(user_instruction 과 동일 한계) — 목적에 비밀 미기재 안내 |
| 비-git 프로젝트 | 상태 저장소(.git 내부) 부재 → 전체 no-op. 규칙 텍스트(SOP)만 생존 |
| worktree 병행(git_workflow §2-1) | 링크드 worktree 도 자체 `.git` 파일이 메인 gitdir 을 가리킴 → `git rev-parse --git-common-dir` 기준으로 상태 저장소 통일(세션 레지스트리는 저장소 단위 공유) |

## 7. 변경 인벤토리 (전부 신규)

**session_workflow 번들** (`kuks_claude_skill_setup/session_workflow/`)

- `session_workflow.md` — 생애주기 SOP SSOT (§5 절차 + §6 한계 정직 명시, self-contained)
- `claude.snippet.md` — CLAUDE.md 등록 스니펫
- `hooks/session_workflow-start.py` · `-gate.py` · `-track.py` · `-end.py` — §4
- `install.sh` — `docs/claude_guideline/session_workflow/` 복사, snippet append, `.claude/settings.json` 에 SessionStart·UserPromptSubmit·PostToolUse(Edit|Write|NotebookEdit)·SessionEnd 멱등 등록

**저장소 문서**

- 루트 README 번들 목록에 session_workflow 추가(존재 시)

## 8. 검증 (SIL)

- **목적 게이트**: 새 세션 → 목적 질문 주입 확인 → 일반 프롬프트 반복 시 게이트 재주입 확인 → `목적: X` → 등록·해제 확인.
- **레지스트리·충돌**: 세션 2개 기동, 양쪽 목적 등록 → 서로의 목록 주입 확인 → 같은 파일 Edit → 후행 세션에 경보 1회(중복 없음) 확인.
- **종료·handoff**: 세션 A 가 파일 수정 후 미커밋 종료 → `handoff/<id>.md` 생성 확인 → 새 세션 시작 주입에 handoff 표시 확인 → 픽업·삭제 흐름 확인. 전부 커밋 후 종료 → handoff 미생성 확인.
- **graceful**: 비-git 디렉터리·규칙 파일 부재에서 4개 훅 전부 exit 0 no-op 확인.
- dogfooding/ 에서 SIL 회고 entry 로 형식 결함 점검(로컬 전용, sync 제외).

## 9. 범위 밖

- staging/commit 강제 차단(git_workflow 소관), 지시 기록(user_instruction 소관)
- 세션 간 작업 큐·분배 오케스트레이션(필요 시 별도 트랙)
- claude-mem/OMC 등 외부 플러그인의 SessionStart 주입과의 통합
