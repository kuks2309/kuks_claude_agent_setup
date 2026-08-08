# session_workflow — 세션 종료 자동 커밋·push·병합(autocommit)

## 2026-07-31 22:10 (KST) — SessionEnd 자동 커밋 훅 추가 (세션 파일만 commit→push→병합)

- 대상:
  - `session_workflow/hooks/session_workflow-autocommit.py` — 신규 (`git(args, cwd, timeout=15)` `dirty_of(top, paths)` `note(root, sid, text)` `main()`, 전역 `EXCLUDE_PREFIXES` `PUSH_RETRIES=3`)
  - `session_workflow/install.sh` — autocommit 복사·드리프트 목록 추가, `ensure_end_before_merge` → `ensure_end_before(cmd, timeout, befores)` 일반화(SessionEnd 순서: autocommit → end → git_workflow-session-end), timeout 90s
  - `session_workflow/session_workflow.md` — §3 2단을 SessionEnd 훅 체인(자동 커밋→handoff→자동 병합)으로 개편, §5 "검증 없는 상태 박제" 한계 추가
- 변경: 세션 종료 시 이 세션 touched ∩ dirty 파일만 `git add` 후 `git commit --only -- <경로>` 로 부분 커밋(공유 index 의 타 세션 staged 불가침). 공유 트리 세션은 임시 worktree 에서 origin 최신 위 cherry-pick push(+fito, 재시도 3회) — 타 세션 미푸시 커밋 미동반. 혼입 파일·`docs/user_instructions/` 제외(handoff 소관), `session/<id>` 브랜치 세션은 커밋만(병합은 git 플로우 훅 소관), 실패·충돌 시 작업 보존 + `handoff/<sid>-autocommit.md` 사유 기록. 커밋 메시지 `chore(session): <목적> — 세션 종료 자동 커밋 (sess:<id>)`.
- 사유: 사용자 정책 결정(2026-07-31) "세션 종료 시 해당 작업 관련 파일만 커밋 푸쉬하고 머지". SIL(Software-In-the-Loop) 중 발견·수정한 결함 2건: git() 헬퍼의 stdout.strip() 이 porcelain 선행 공백을 제거해 경로 1글자 잘림(`cf.md`→`f.md`), 미추적 파일이 `commit --only` pathspec 에 미매칭 → add 선행으로 해결. 최종 SIL 6케이스(정상·staged 불가침·혼입 제외·공유 로그 제외·충돌 보류·비-git no-op·세션 브랜치) + 설치 순서 멱등 PASS.
- 커밋: feat(session_workflow): 세션 종료 자동 커밋·push·병합 autocommit 훅 (커밋 대기)
