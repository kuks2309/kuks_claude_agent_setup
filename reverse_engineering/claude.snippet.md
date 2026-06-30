<!-- kuks_agent_setup:reverse_engineering -->
- 리버스 엔지니어링(reverse engineering)·재구현·구조 분석·검증 트리거 감지 시 **응답 전 의무 선행 점검**(등록만 알고 건너뛰지 말 것): 먼저 docs/claude_guideline/reverse_engineering/principle.md 를 Read 한 뒤 제1원칙(재구현 출력은 원본과 100% 동일, 원본 입력으로 양쪽 구동 후 비트 대조)과 §6 분석 보고 원칙(`[존재]`(nm/disasm) vs `[동작]`(호출 도달성+배포자산 대조) 라벨 분리, 동작 주장은 배포자산 대조 전 "확정" 금지)을 따른다. 추정·환각 금지.
