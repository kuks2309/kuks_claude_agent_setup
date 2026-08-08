# 코드 인벤토리 (수정 파일 범위)

번들 코드의 파일·함수·전역 목록. 현재 등재 범위: `session_workflow/`·`mistake/` (다른 번들은 수정 시 추가).

## session_workflow/hooks/

| 파일 | 역할 | 함수 (시그니처) | 전역 |
| --- | --- | --- | --- |
| `session_state.py` | 4+1 훅 공유 상태 로직 | `kst_now()` `kst_now_str()` `rule_active(cwd)` `git_common_dir(cwd)` `repo_top(cwd)` `state_root(cwd)` `active_dir(root)` `handoff_dir(root)` `session_json(root, sid)` `touched_path(root, sid)` `allow_path(root, sid)` `load_session(root, sid)` `save_session(root, sid, meta)` `ensure_session(root, sid)` `read_touched(root, sid)` `read_allow(root, sid)` `list_other_active(root, sid)` `is_stale(meta)` `behind_origin_main(cwd, do_fetch=True)` `one_line(text, limit=120)` `format_handoff(short, meta, ended, uncommitted, touched)` `parse_handoff_summary(path)` | `KST` `STALE_HOURS=24` `HANDOFF_KEEP_DAYS=14` `PURPOSE_RE` |
| `session_workflow-start.py` | SessionStart — 레지스트리 등록·활성/stale/handoff/게이트 예고 주입·handoff GC | `gc_handoffs(root)` `main()` | `HANDOFF_SHOW=5` `TOUCHED_SHOW=10` |
| `session_workflow-gate.py` | UserPromptSubmit — 목적 게이트·등록, 충돌 경보(1회성), last_seen 갱신 | `conflict_lines(root, sid, meta)` `main()` | — |
| `session_workflow-track.py` | PostToolUse — 세션별 수정 파일 누적(dedup, repo/프로젝트 상대경로) | `main()` | `TRACK_TOOLS` |
| `session_workflow-file-gate.py` | PreToolUse — 타 활성 세션 파일 Write/Edit 차단(allow override) | `main() -> int` | `GATE_TOOLS` |
| `session_workflow-autocommit.py` | SessionEnd — 세션 touched∩dirty 만 부분 커밋·cherry-pick push(+fito)·실패 시 보존+사유 기록 | `git(args, cwd, timeout=15)` `dirty_of(top, paths)` `note(root, sid, text)` `main()` | `EXCLUDE_PREFIXES` `PUSH_RETRIES=3` |
| `session_workflow-end.py` | SessionEnd — 미커밋 감지→handoff 박제, 레지스트리(.json/.touched/.allow) 해제 | `uncommitted(top, paths)` `main()` | — |

## session_workflow/

| 파일 | 역할 | 함수 |
| --- | --- | --- |
| `install.sh` | 복사·CLAUDE.md 등록·settings 훅 멱등 등록(SessionEnd 순서: autocommit→end→병합 훅)·INSTALLED.md 기록·`--status` 드리프트 점검 | `bundle_commit` `record_install` `drift_pairs` `status_check` + 내장 python `ensure(event, cmd, timeout, matcher=None)` `ensure_end_before(cmd, timeout, befores)` |

## mistake/hooks/

| 파일 | 역할 | 함수 (시그니처) | 전역 |
| --- | --- | --- | --- |
| `mistake-inject.py` | SessionStart — INDEX §메타 패턴·§미해결 항목 + open·청소 미완 retracted entry 목록 주입 (retracted 본문은 학습 자료로 주입 금지) | `project_root()` `index_sections(idx_path)` `open_entries(entry_dir)` `main()` | `MAX_OUT=4000` `MAX_OPEN_LIST=10` |

## mistake/checks/

| 파일 | 역할 | 함수 (시그니처) | 전역 |
| --- | --- | --- | --- |
| `entry-lint.sh` | entry 형식·closure·retracted 규칙 기계 검증 (bash 래퍼 + 내장 python) — 교차 파일 id 중복·closed 유령 반영 자산 검출 포함 | 내장 python `asset_path(tok)` | `DIR` `MISTAKE_CATS` `VIOLATION_CATS` `SECTIONS` `NAME_RE` `TODAY` `ROOT` `id_map` |
