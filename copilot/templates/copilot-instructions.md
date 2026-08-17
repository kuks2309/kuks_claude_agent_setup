# 저장소 작업 원칙 (GitHub Copilot 전역 지침)

<!-- 이 파일은 kuks_claude_agent_setup/copilot/templates/ 의 시작 템플릿이다.
     타깃 저장소의 .github/copilot-instructions.md 로 복사한 뒤 프로젝트에 맞게 다듬는다.
     규칙 본문(번들)은 docs/claude_guideline/ 에 설치돼 있다고 전제한다. -->

## 핵심 원칙

- **사용자가 지시한 것만 수행한다.** 요청 밖의 리팩토링·정리·파일 추가를 임의로 하지 않는다.
- **검증 없이 완료를 선언하지 않는다.** 빌드·테스트·린트를 실제로 실행하고 결과를 인용한다.
  실행하지 못한 검증은 "미수행"으로 명시한다.
- **추정·환각 금지.** 외부 문서(매뉴얼·데이터시트·SDK)는 기억이 아니라 저장소 `references/`
  보관본 또는 공식 문서를 열어 출처·페이지·버전과 함께 인용한다.
- **기록이 완료의 일부다.** 버그 수정은 `docs/issues_and_fixes/`, 설계 결정은 `docs/adr/`,
  기술 부채는 `docs/debt/registry.md` 에 남긴다. 코드의 TODO/FIXME/HACK 은 반드시
  debt id 를 참조한다 (`# TODO(debt-042): ...`) — 맨 마커는 CI 가 차단한다.

## 규칙 파일 (트리거 시 반드시 먼저 읽을 것)

아래 작업을 시작하기 전에 해당 규칙 파일을 읽고 그 절차를 따른다. 등록만 알고 건너뛰지 않는다.

- 코드 작성/수정 → `docs/claude_guideline/coding/coding.md` (사전조사 → ADR → 구현 → 검증 → 이중기록)
- 코드 리뷰 → `docs/claude_guideline/code_review/review.md` (인벤토리 + severity 평가)
- 버그 수정/이슈 해결 → `docs/claude_guideline/issue_fix/issue_fix.md` (진단 → 제안 → 구현 → 검증 → 기록)
- `.drawio` 생성/수정 → `docs/claude_guideline/drawio/drawio.md` (2단 검증 루프)
- git commit/push → `docs/claude_guideline/git_workflow/git_workflow.md` (협업 모드 확인 · 명시 staging · `type(scope): subject`)
- 부채/TODO → `docs/claude_guideline/debt/debt.md` (registry 등록)

## 커밋 규약

- `type(scope): subject` — type 은 feat·fix·docs·refactor·style·chore·test. 한국어 본문 허용.
- 작업 단위 = 커밋 단위. `git add -A` / `git add .` 금지 — 명시 경로만 staging.
- push 전 secrets(.env·키·토큰) 미포함과 대상 저장소를 확인한다.

## 강제 수준 안내

이 지침은 권고(L1)다. 진짜 강제는 pre-commit/CI 의 `checks/*.sh`(L3)가 담당하며,
`⟦CI:<id>⟧` 마커가 붙은 규칙은 위반 시 커밋·머지가 기계적으로 차단된다.
