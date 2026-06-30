# 세션 격리 설계 — 다중 세션 명령 누수 차단

> 상태: 설계 승인 대기 · 작성 2026-07-01 · 대상 번들: `user_instruction`, `git_workflow`

## 1. 문제

`kuks_claude_skill_setup` 을 여러 프로젝트에 설치하고 **동시 다중 세션**을 운영할 때 세션 간 독립성이 깨진다. 사용자가 관찰한 증상 3가지:

1. **공유 지시 기록파일 혼선** — 한 세션이 기록한 지시가 다른 세션 기록에 섞임
2. **실제 프롬프트 전달(체감)** — 한 세션의 프롬프트가 다른 세션의 현재 작업으로 둔갑
3. **커밋/스테이징 휩쓸이** — 한 세션 커밋이 다른 세션의 미커밋 변경까지 staging

## 2. 근본 원인 (검증됨)

조사 결과 **프로세스 간 직접 채널은 없다**. 어떤 hook 도 프롬프트를 공유 경로/큐에 쓰지 않으며(리마인더는 stdout 으로 지시문만 출력), 절대경로·`~/.claude`·`/tmp` 등 프로젝트 간 채널도 없다(모두 `cwd`/`CLAUDE_PROJECT_DIR`/`.git` 상대). `.omc/sessions/*.json` 에 프롬프트는 저장되지 않는다.

세 증상은 **두 근본 원인**으로 수렴한다:

### 원인 A — 세션 키 없는 공유 기록파일
`docs/user_instructions/user_instructions.md` 가 프로젝트당 단일 파일이고, 모든 세션의 `user_instruction-reminder.py` 가 매 프롬프트마다 "이 파일 맨 위에 prepend 하라"고 모델에 지시한다. 세션 B 가 prepend 하려 파일을 열면 맨 위에 세션 A 가 방금 기록한 지시가 보이고, 모델이 이를 "현재 작업"으로 착각한다(증상 1·2). `code_review/review.md` §7, `issue_fix` 가 이 파일을 교차 참조하는 것도 오염을 키운다.

### 원인 B — 공유 working tree + 권고뿐인 staging
working tree(파일시스템)는 모든 세션이 공유한다. 번들에는 이미 세션 격리 인프라가 있으나(`git_workflow-track.py` 가 세션별 touched 기록, `git_workflow-reminder.py` 가 "이 세션 파일만 staging + `git diff --cached` 부분집합 검증" 주입) **⟦권고⟧ 주입일 뿐 강제 게이트가 아니라** 모델이 `git add -A` 로 무시할 수 있다(증상 3).

## 3. 목표 / 비목표

**목표**
- 동시 세션이 서로의 지시 기록을 보거나 그에 따라 행동하지 않음(읽기 격리)
- 의도 부채 방지용 **단일 누적 로그**(`user_instructions.md`)는 보존
- 한 세션의 커밋이 다른 세션의 미커밋 변경을 staging 하지 못하게 **강제 차단**
- self-contained 유지(OMC 등 외부 도구 비의존), graceful(규칙 파일/​git 없으면 no-op)

**비목표**
- claude-mem/OMC 의 SessionStart "recent context" 주입(별도 플러그인 소관, 본 설계 범위 밖)
- 프로세스 간 실시간 프롬프트 라우팅 변경(그런 채널은 존재하지 않음)
- 비밀정보 의미 마스킹(§6 트레이드오프 참조)

## 4. 설계 A — 세션별 독립 기록 + SessionEnd 병합

기존 "단일 공유 파일에 모델이 prepend" 를 **세션별 독립 기록 → 병합** 으로 전환한다.

```
docs/user_instructions/
  user_instructions.md       # 단일 누적 durable 로그 (커밋 대상, 병합 결과물)
  sessions/                  # .gitignore (세션별 독립 기록, 전이적)
    {session_id}.md          # 이 세션만 쓰고 이 세션만 읽음
```

### 4.1 쓰기 — UserPromptSubmit hook 이 직접 기록 (모델 비의존)
`user_instruction-reminder.py` 를 리마인더 주입형 → **결정적 기록형**으로 변경한다.
- 입력 JSON 의 `prompt` + `session_id` 를 받아 `docs/user_instructions/sessions/{session_id}.md` 에 prepend(newest-on-top):
  ```markdown
  ## YYYY-MM-DD HH:MM (KST) · sess:<short8>

  > "<사용자 원문 그대로>"

  ---
  ```
  헤더에 **제목·요약 슬롯을 두지 않는다** — 요약하려면 hook 이 원문을 가공해야 하므로 "원문만" 원칙과 충돌한다. 헤더는 시각 + 세션태그만, 본문은 verbatim 인용.
- 모델 준수에 의존하던 "작업 후 일괄 기록" 실패 모드가 원천 제거되고, **원문만** 박제됨이 보장된다(분석·요약 섞임 불가).
- **동시 세션이 각자 자기 파일에만 쓰므로 경합·race 없음** (현재 단일 파일 prepend 의 lost-write 소멸).
- graceful 게이트: `docs/claude_guideline/user_instruction/recording.md` 존재 시에만 활성(기존과 동일).

### 4.2 읽기 격리 — 자기 세션 기록만 주입
- hook 은 stdout 으로 **이 세션의 `sessions/{id}.md` 내용만** 참조용으로 주입한다(최근 N개 entry, 모델이 자기 세션의 누적 의도를 맥락으로 갖도록). 다른 세션 파일은 절대 노출하지 않는다 → 증상 1·2 차단. (주입 분량이 과하면 최근 N개로 절단하고 "이하 생략" 표기.)
- 모델은 `user_instructions.md` 를 **읽지 않는다**. recording.md 규칙을 "기록은 hook 이 수행, 모델은 이 파일을 현재 작업 소스로 취급 금지"로 갱신.

### 4.3 병합 — SessionEnd hook (자기 파일만)
신규 `user_instruction-merge.py` (SessionEnd):
- 입력 `session_id` 로 **자기** `sessions/{id}.md` 만 읽어 `user_instructions.md` 에 시간순(newest-on-top)·세션태그로 병합.
- 병합 후 자기 `sessions/{id}.md` 삭제.
- **남의 live 기록은 절대 건드리지 않음** → 동시 세션 완전 안전.
- 병합은 `user_instructions.md`(공유 파일) 를 rewrite 하므로 **`fcntl.flock` 으로 read-modify-write 임계구역 보호** (두 세션이 동시 종료해도 lost-write 없음). 임계구역은 세션당 1회·짧음.
- 크래시로 SessionEnd 미발화 시 orphan `sessions/{id}.md` 잔존 → **age 기반 GC**(mtime > 7일)를 SessionEnd 말미에 보수적으로 수행(live 세션 파일은 7일 내라 안전).

## 5. 설계 B — 커밋 격리 하드 게이트

신규 `git_workflow-staging-guard.py` (PreToolUse, matcher: `Bash`):
- `tool_input.command` 를 토큰 검사. 다음 **blanket-add 패턴 차단**:
  - `git add -A`, `git add --all`, `git add .`, `git add -u`
  - `git commit -a`, `git commit --all`, `-a` 결합 단축플래그(예 `-am`)
  - **차단 제외**: `git commit --amend`(auto-stage 아님), `git add -p`/`-i`(대화형 부분 staging) — blanket 아님
- **차단 = exit 2 + stderr 메시지**(PreToolUse 계약: exit 2 → 도구 호출 차단, stderr 가 모델에 피드백).
- 명시 경로 staging(`git add <path>`)은 통과.
- 차단 메시지에 `git_workflow-track.py` 가 기록한 **이 세션 touched 목록**을 실어 "이것만 명시 add 하라" grounding.
- graceful: git 저장소 + `docs/claude_guideline/git_workflow/git_workflow.md` 존재 시에만 활성. 그 외 no-op(exit 0).
- 파싱 보수성: `&&`/`;`/서브셸 체인 안의 `git add -A` 도 매칭 시도하되, 난독화는 일부 false negative 허용(흔한 footgun 우선 차단). false positive 0 을 우선(명시 경로는 항상 통과).

## 6. 엣지 케이스 & 트레이드오프

| 항목 | 처리 |
|------|------|
| 동시 세션 SessionEnd 동시 발화 | `user_instructions.md` flock 으로 직렬화 |
| 세션 크래시(SessionEnd 미발화) | orphan 파일 잔존 → age>7d GC 로 회수, 데이터 손실 없음 |
| 비-git 프로젝트 | A 는 git 무관(정상 동작), B 는 no-op |
| 비밀정보 마스킹 | hook 자동 기록은 verbatim → 의미 마스킹 불가. 기존 모델 마스킹도 비신뢰였음. **알려진 한계**로 명시, 필요 시 단순 정규식 denylist 후속 |
| `git add -u`/부분집합 정당한 케이스 | blanket 으로 차단 → 명시 경로로 우회(의도된 마찰) |
| `sessions/` 커밋 오염 | install.sh 가 `.gitignore` 에 `docs/user_instructions/sessions/` 추가 |

## 7. 변경 인벤토리

**user_instruction 번들**
- `hooks/user_instruction-reminder.py` — 리마인더형 → 결정적 기록 + 자기세션 주입형으로 재작성
- `hooks/user_instruction-merge.py` — **신규** SessionEnd 병합(flock + age GC)
- `recording.md` — 규칙 갱신(hook 이 기록, 모델은 read-as-task 금지, sessions/ 구조)
- `install.sh` — SessionEnd 훅 등록 추가, `.gitignore` 에 `sessions/` 추가
- `claude.snippet.md` — 등록 문구 갱신

**git_workflow 번들**
- `hooks/git_workflow-staging-guard.py` — **신규** PreToolUse blanket-add 차단
- `install.sh` — PreToolUse(Bash matcher) 훅 등록 추가

**교차참조 정리**
- `code_review/review.md` §7, `issue_fix/issue_fix.md` — `user_instructions.md` 교차참조를 "병합된 누적 로그" 기준으로 문구 점검(동작 변경 없음, 문서 정합만)

## 8. 검증 (SIL)

- A: 두 세션(서로 다른 session_id)으로 각각 프롬프트 제출 → `sessions/{id}.md` 2개 독립 생성, 상호 비노출 확인. 각 SessionEnd 후 `user_instructions.md` 에 세션태그로 병합·`sessions/` 정리 확인. 동시 종료 시 flock 으로 양쪽 entry 보존 확인.
- B: `git add -A` / `git add .` / `git commit -am` → exit 2 차단 + touched 목록 안내 확인. `git add <명시경로>` → 통과 확인. 비-git 디렉터리 → no-op 확인.
- dogfooding/ 에 SIL 회고 entry 로 형식 결함 점검(로컬 전용, sync 제외).

## 9. 범위 밖
- claude-mem/OMC SessionStart recent-context 주입 격리(별도 트랙)
- 비밀정보 의미 마스킹 자동화
- 프로젝트 간(cross-project) 격리 — 본 번들에 채널 없음(설치가 프로젝트별이라 구조적으로 격리됨)
