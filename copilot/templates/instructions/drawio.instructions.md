---
applyTo: "**/*.drawio"
---

# .drawio 다이어그램 작업 규칙

`.drawio` 파일을 만들거나 고치기 전에 `docs/claude_guideline/drawio/drawio.md` 를 읽고
2단 검증 루프를 통과시킨다:

1. **기하 린트** — `python3 docs/claude_guideline/drawio/checks/drawio_lint.py <파일>.drawio`
   결함 0 (L1~L11: 사선 화살표·글자 벗어남·박스/엣지 겹침·축 어긋남·html 태그로 먹힌 글자)
2. **렌더 시각 검토** — `docs/claude_guideline/drawio/checks/drawio_capture.sh <파일>.drawio`
   로 캡처한 PNG 를 열어 `references/visual-checklist.md` 기준으로 검토

루프 통과 전에는 "완료"를 선언하지 않는다. 렌더 검토를 수행할 수 없는 환경이면
미수행 사실을 산출물에 명시한다. pre-commit 의 `⟦CI:drawio-lint⟧` 가 1번을 강제한다.
