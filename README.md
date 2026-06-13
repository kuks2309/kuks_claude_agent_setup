# kuks_claude_agent_setup

Claude Code 자산(규칙·훅) 설치 저장소. 각 자산은 **폴더별 자기완결 번들**이며, 폴더 안의 `install.sh` 로 **따로** 설치한다 (루트 중앙 스크립트 없음).

## 자산 목록

| 번들 | 용도 | 설치 대상 | 설치 명령 |
|---|---|---|---|
| [user_instruction/](user_instruction/recording.md) | 사용자 지시 원문 기록 (의도 부채 방지) | 프로젝트별 | `cd user_instruction && ./install.sh <타깃-프로젝트-루트>` |
| [acronym/](acronym/acronym.md) | 영어 약자 `약어(영어 단어)` 병기 + 자동 적용 훅 | 전역 (`~/.claude`) | `cd acronym && ./install.sh [--reminder-only]` |

## 설치 방식

각 번들은 자기 폴더의 `install.sh` 로 설치한다.

- **user_instruction** — 타깃 프로젝트 인자를 받아 규칙(`recording.md`)을 `docs/claude_guideline/user_instruction/` 로 복사 + 타깃 `CLAUDE.md` 에 등록 줄 append.
- **acronym** — `~/.claude` 에 규칙·훅 복사 + `CLAUDE.md` 등록 + `settings.json` 훅 등록. `--reminder-only` 면 리마인더(`UserPromptSubmit`)만, 생략하면 검증(`Stop`)까지 등록.

설치는 기존 `CLAUDE.md`·`settings.json` 을 **덮어쓰지 않고 append/merge** 하며, 중복은 마커로 스킵하고 `settings.json` 은 사전 백업한다.

## 구조 규약

- 자산 = 폴더별 자기완결 번들. 한 폴더에 **규칙 + `claude.snippet.md`(CLAUDE.md 등록 포인터) + `install.sh`**.
- 규칙은 단순하게 유지하고, 분석·검증은 별도로 분리한다.
- `claude.snippet.md` 은 통파일 설치가 아니라 타깃 `CLAUDE.md` 에 붙는 등록 포인터다.
