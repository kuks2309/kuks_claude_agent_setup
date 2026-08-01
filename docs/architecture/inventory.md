# kuks_claude_agent_setup 인벤토리

## 목적

번들 모음 저장소의 실행 코드 자산(검사 스크립트·훅) 인터페이스 현황표. 증분 작성 — 수정이 닿은 파일부터 등재한다.

## 커버 파일

- `mistake/checks/entry-lint.sh`

## 함수 표

| 함수 | 시그니처 | 역할 (1 줄) | 파일 |
|---|---|---|---|
| `asset_path` | `asset_path(tok) -> pathlib.Path \| None` | reflected_assets 토큰(따옴표·앵커·`:L줄` 제거)을 검사 가능한 경로로 정규화 | `mistake/checks/entry-lint.sh` |

## 전역 변수 표

| 변수 | 타입 | 의미·단위 | 파일 |
|---|---|---|---|
| `DIR` | `pathlib.Path` | 검사 대상 entry 폴더 (argv[1]) | `mistake/checks/entry-lint.sh` |
| `MISTAKE_CATS` | `set[str]` | type=mistake 유효 category enum (4종) | `mistake/checks/entry-lint.sh` |
| `VIOLATION_CATS` | `set[str]` | type=rule-violation 유효 category enum (7종, record-skip 포함) | `mistake/checks/entry-lint.sh` |
| `SECTIONS` | `list[str]` | entry 필수 5절 헤딩 (존재·순서 검사 기준) | `mistake/checks/entry-lint.sh` |
| `NAME_RE` | `re.Pattern` | entry 파일명 규칙 `YYYY-MM-DD-NNN[_제목].md` | `mistake/checks/entry-lint.sh` |
| `TODAY` | `datetime.date` | open 7일 초과 판정 기준일 | `mistake/checks/entry-lint.sh` |
| `ROOT` | `pathlib.Path` | 프로젝트 루트 (DIR 의 2단계 상위) — 상대 경로 자산 실재 검사 기준 | `mistake/checks/entry-lint.sh` |
