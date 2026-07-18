# 번들 업데이트 체계 설계 (기록 + 점검 + 문서)

- 날짜: 2026-07-18
- 상태: 승인됨 (사용자: "진행해 보고 문제 있으면 업데이트 합시다")
- 문제: 저장소가 업데이트되어도 타깃 프로젝트·`~/.claude` 설치본을 갱신할 안내/방법이 없어 업데이트가 적용되지 않음.

## 배경 (현재 상태)

- 각 번들 `install.sh` 는 멱등(재실행 안전) — "갱신 = 재설치"가 설계상 이미 가능.
- 그러나 (1) 루트 README 에 업데이트 절차 섹션 없음, (2) 설치 시 타깃에 기록(커밋·인자)이 안 남아 무엇이 낡았는지 확인 불가, (3) 도메인 선택 인자(code_review·coding·external_reference)는 재설치 시 기억에 의존, (4) 전역 설치(acronym·computer_use)도 동일.
- v1(kuks_claude_setup/claude_guideline)은 자체 체계(VERSION·CHANGELOG·update.sh·audit.sh) 보유 — 문서 노출만 부족.

## §1 설치 기록 — INSTALLED.md

설치 성공 시 각 install.sh 가 자기 행을 기록한다.

- 위치: 프로젝트 번들 → `<타깃>/docs/claude_guideline/INSTALLED.md`, 전역 번들 → `$CLAUDE_HOME/INSTALLED.md`(기본 `~/.claude`).
- 형식(번들당 1행, 재설치 시 자기 행만 교체):

```markdown
| 번들 | 설치 커밋 | 날짜 | 인자 |
| --- | --- | --- | --- |
| code_review | 52125a9 | 2026-07-18 | ros2-review |
```

- 커밋 = 번들 저장소 `git rev-parse --short HEAD`. 번들 폴더에 미커밋 변경 있으면 `+dirty` 접미, git 저장소가 아니면 `unknown`.
- 인자 열 = 도메인 선택 등 설치 시 인자 원문(없으면 `-`). 재설치 시 같은 인자를 재현하기 위함.

## §2 점검 플래그 — --status

모든 번들에 통일 플래그: `./install.sh <타깃> --status` (전역 번들은 `./install.sh --status`).

- 판정 3종:
  - **최신** (exit 0) — 기록 커밋 이후 이 번들 폴더 변경 없음
  - **재설치 권장** (exit 1) — 변경 파일 목록 출력. 기록 커밋이 `unknown`/저장소에 없음/`+dirty` 인 경우도 비교 불가로 이쪽 판정
  - **기록 없음** (exit 2) — 구판 설치 또는 미설치. 재설치로 기록 생성 안내
- 추가: 설치본 파일 내용 diff 로 로컬 수정(드리프트) 감지 출력.
- 플래그명이 `--check` 가 아닌 이유: computer_use 의 기존 `--check` = preflight(의존성 점검) 와 충돌 회피. 기존 의미 보존.

## §3 문서 — 루트 README "업데이트" 섹션 (SSOT)

절차는 루트 README 한 곳에만 작성(번들 README 에 복제 금지):

1. 번들 저장소 `git pull`
2. 각 설치 타깃에서 `./install.sh <타깃> --status` 점검
3. 재설치 권장이면 INSTALLED.md 의 인자 그대로 재실행(멱등이라 안전)
4. 전역 번들·다른 PC(윈도우)도 같은 절차. 기록 없는 기존 설치본은 최초 1회 재설치로 기록 생성.

## §4 v1 (kuks_claude_setup) — 문서만

- claude_guideline: README 에 업데이트 절차(`bash docs/claude_guideline/update.sh`) 노출.
- project-autolearn: 재실행 안내 한 줄.
- v1 은 v3 이식 종착 대상이므로 투자 최소화(신규 도구 없음).

## §5 검증 — experiments SIL

임시 타깃 + `CLAUDE_HOME` 오버라이드로: 신규 설치 → 행 생성, 재실행 → 행 교체(중복 없음), --status 3판정(최신/재설치 권장/기록 없음) 재현.

## §6 구현 순서

1. 대표 번들 git_workflow 에 기록+--status 구현 → SIL 검증
2. 패턴을 나머지 12개 번들에 전개
3. 루트 README 업데이트 섹션
4. v1 문서 2건

공통 로직은 루트 공유 스크립트 없이 각 install.sh 에 동일 블록 삽입 — "폴더 자기완결 번들 + 루트 중앙 디스패처 금지" 규약 유지.
