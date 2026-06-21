<!-- kuks_agent_setup:debt -->
## 부채 관리 (debt)

기술·이해·의도 부채는 [docs/claude_guideline/debt/debt.md](docs/claude_guideline/debt/debt.md) 절차로 **등록·추적·상환**한다 — 식별된 부채는 `docs/debt/registry.md` 에 등록(id·유형·위치·사유·상태·상환계획), 코드의 `TODO`/`FIXME`/`HACK` 은 debt id 를 참조(`# TODO(debt-042): ...`, 맨 마커는 `⟦CI:debt-marker⟧` 차단). 식별은 작업 SOP(coding §2/§4/§5/§6)가, 등록·추적은 debt 가 소유. 미설치 시 식별만 주석/ADR 에 남김(graceful).
