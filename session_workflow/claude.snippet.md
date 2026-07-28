<!-- kuks_agent_setup:session_workflow -->
- 세션 생애주기(시작→진행→종료)는 session_workflow 훅이 관리한다: 세션 목적 선언 게이트(`목적: …` 입력 시 훅이 자동 등록), 활성 세션 레지스트리·파일 충돌 경보, 종료 시 미커밋 잔여 handoff 박제(규칙: docs/claude_guideline/session_workflow/session_workflow.md). 모델은 목적 미등록 상태에서 실질 작업 전에 사용자에게 목적을 확인하고, 종료·커밋 보고는 이 세션 작업만 담되 타 세션·공유 트리 상태는 사용자 결정이 필요한 경보 1줄로 제한한다.
