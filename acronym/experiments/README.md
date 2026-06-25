# acronym — 단위 검증 (SIL / HIL)

> 본 번들의 **L1 함수 단위 + L2 단일 프로그램** 검증을 기록한다. 통합 결과는 상위 `../../experiments/INDEX.md` 로 집계.
> 검증 모델·배치 규칙 → `../../experiments/README.md`.
> **SIL 수행 위치**: SIL 검증은 번들이 설치된 **다른(타깃) 프로젝트**에서 수행하고 결과만 여기에 반영(기록)한다.

## 검증 대상 코드

| 파일 | 종류 | 검증 초점 |
|------|------|-----------|
| `hooks/acronym-check.py` | Stop 훅 (Python) | 미병기 약자 탐지·차단 (exit 2) |
| `hooks/acronym-reminder.sh` | UserPromptSubmit 훅 (Bash) | 규칙 컨텍스트 주입 |
| `install.sh` | 설치 프로그램 | `~/.claude` 복사 · settings.json 멱등 merge |

## L1 함수 단위 (SIL)

- `find_violations(text)`:
  - 병기 도입 인식: `API(...)` 가 본문에 한 번이라도 있으면 이후 bare `API` 위반 아님.
  - whitelist 통과 (JSON·CI·SOP …), 코드블록/인라인/URL 제거.
  - 2~6자 대문자만 약자; `STM32`(문자+숫자)·`CODEOWNERS`(7자+) 제외.
- `last_assistant_text(path)`: JSONL transcript 에서 마지막 assistant text 추출, 깨진 줄 graceful.

## L2 단일 프로그램

- **SIL**: stdin 에 fixture transcript JSON 주입 → 위반 시 exit 2 + stderr 메시지, 무위반 exit 0; `stop_hook_active=true` 면 무조건 exit 0(루프 방지).
- **SIL (install)**: `CLAUDE_HOME=$(mktemp -d) ./install.sh` → 훅 3파일 복사·CLAUDE.md marker 1회·settings.json 에 UserPromptSubmit+Stop 등록; 재실행 시 "스킵"(멱등); `--reminder-only` 는 Stop 보류.
- **HIL**: 실 `~/.claude` 설치 후 세션 재시작 → 미병기 약자 답변이 실제로 차단되는지, 리마인더가 매 턴 주입되는지.

## 기록

`SIL/_template/` · `HIL/_template/` 를 `YYYY-MM-DD_<topic>/` 로 복사해 채운다. 완료 시 상위 INDEX 갱신.
