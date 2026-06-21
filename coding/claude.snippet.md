<!-- kuks_agent_setup:coding -->
## 코드 작성 SOP (coding)

코드 작성 시 [docs/claude_guideline/coding/coding.md](docs/claude_guideline/coding/coding.md) 절차를 따른다 — 입구 작업분류(trivial fast-path) → 사전조사(함수표·전역변수표 read) → 사전승인(ADR) → 구현 → 검증(테스트·보안, never-self-approve) → 후속갱신(이중 기록). 강제는 `⟦CI:<id>⟧` ↔ `checks/<id>.sh`(pre-commit·CI)만 진짜, 그 외는 `⟦권고⟧`. 명명·스타일은 `conventions.md`, 언어/포맷터는 `stack.md`, 도메인(ros2/embedded/numeric/concurrency/memory)은 트리거 시 `docs/claude_guideline/coding/domains/` 적용.
