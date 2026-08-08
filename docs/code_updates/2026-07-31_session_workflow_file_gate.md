# session_workflow — 동시 수정 차단(file-gate)

## 2026-07-31 20:55 (KST) — 타 활성 세션 파일 Write/Edit 실행 전 차단 추가

- 대상:
  - `session_workflow/hooks/session_workflow-file-gate.py` — 신규 (PreToolUse, `GATE_TOOLS`, `main()`)
  - `session_workflow/hooks/session_state.py` — `allow_path(root, sid)`·`read_allow(root, sid)` 추가
  - `session_workflow/hooks/session_workflow-end.py` — 레지스트리 해제 시 `.allow` 파일도 삭제
  - `session_workflow/install.sh` — file-gate 복사·드리프트 대조 목록 추가, `PreToolUse`(matcher `Write|Edit|MultiEdit|NotebookEdit`, timeout 5) 멱등 등록
  - `session_workflow/session_workflow.md` — §0 allow 행·모델 편집 예외, §2 차단 규칙, §5 race 창 한계, 룰 2 갱신
- 변경: Write/Edit/MultiEdit/NotebookEdit 대상 파일이 **잔류 아닌 다른 활성 세션의 touched** 에 있으면 도구 호출을 exit 2 로 차단하고 소유 세션 short-id·목적·override 절차를 stderr 로 안내. 사용자 승인 시 자기 `active/<sid>.allow` 에 경로를 추가하면 통과. 잔류 의심(last_seen 24h+)·혼입(양쪽 touched)·프로젝트 밖 파일·allow 등재 경로는 차단하지 않음. 세션 종료 시 allow 는 자동 정리.
- 사유: 두 세션이 같은 파일(`docs/debt/registry.md`)을 수정해 변경이 한 파일에 혼입된 실사례(사용자 보고, 2026-07-28) — 기존 충돌 경보(권고)로는 예방이 안 되어 수정 시점 강제 차단을 사용자가 요구(잔류 세션은 경보만 — 죽은 탭의 영구 잠금 방지 정책 선택). SIL(Software-In-the-Loop) 7케이스(차단·allow 통과·잔류 통과·혼입 통과·미접촉 통과·비대상 도구·종료 정리) PASS.
- 커밋: feat(session_workflow): 동시 수정 차단 file-gate (커밋 대기 — push 시 본 entry 와 동일 커밋)
