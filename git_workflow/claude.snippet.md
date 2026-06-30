<!-- kuks_agent_setup:git_workflow -->
- git 작업(commit/push/merge/PR/branch) 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것): 먼저 docs/claude_guideline/git_workflow/git_workflow.md 를 Read 한 뒤 협업 모드 확인(README `git 협업 모드: solo|team` 선언 우선, 미선언 시 사용자 문의·README 기록 — 자동 default 금지)·커밋 규약·세션 격리 staging(이번 세션 수정 파일만)·다중 원격 push·PR 리뷰 게이트를 따른다. 임의 커밋/푸시 직행 금지.
