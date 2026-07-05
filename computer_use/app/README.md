# 2단계: 독립 OOTB 앱 (stub)

Claude Code 없이 동작하는 독립 실행 앱. 본 폴더는 골격이며 실제 구현은 차기.

## 설계

- Anthropic Messages API + `computer_20250124` 도구로 자체 agentic loop 실행.
- 실행기는 1단계의 `../computer_action.py` 를 **그대로 재사용**(action 어휘 일치).
- 캡처는 `../capture_screen.py` 재사용.
- 루프: `anthropic.messages.create(tools=[computer_20250124 ...])` → 모델이
  tool_use(action) 반환 → `computer_action.py` 로 실행 → 스크린샷 반환 → 반복.
- 선택적 Gradio UI.

## 의존성(설치 시)

`install.sh --with-app` 확장으로 `pip install anthropic`(+ Gradio) 추가 예정.

## 참고

- Anthropic computer use 도구 문서
- showlab/computer_use_ootb (loop·UI 참고)
