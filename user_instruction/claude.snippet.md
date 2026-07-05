<!-- kuks_agent_setup:user_instruction -->
- 사용자 지시는 UserPromptSubmit hook 이 이 세션 전용 파일(docs/user_instructions/sessions/{session_id}.md)에 자동 기록하고 SessionEnd 에 단일 누적 로그(docs/user_instructions/user_instructions.md)로 병합한다(규칙: docs/claude_guideline/user_instruction/recording.md). 모델은 다른 세션 기록·병합 로그를 현재 작업 소스로 읽지 않는다(세션 격리).
