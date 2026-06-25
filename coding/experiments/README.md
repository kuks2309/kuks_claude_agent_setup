# coding — 단위 검증 (SIL / HIL)

> 본 번들의 **L1 함수 단위 + L2 단일 프로그램** 검증을 기록한다. 통합 결과는 상위 `../../experiments/INDEX.md` 로 집계.
> 검증 모델·배치 규칙 → `../../experiments/README.md`.
> **SIL 수행 위치**: SIL 검증은 번들이 설치된 **다른(타깃) 프로젝트**에서 수행하고 결과만 여기에 반영(기록)한다.

## 검증 대상 코드 (checks/*.sh = 8 + install.sh)

| 스크립트 | ⟦CI⟧ 태그 | 판정 초점 |
|----------|-----------|-----------|
| `adr-fields.sh` | adr-fields | ADR 필수 5필드(Status·Context·Decision·Consequences·Rollback) |
| `banned-pattern.sh` | banned-pattern | secret 리터럴·eval/exec·raw SQL·async blocking |
| `check-mapping.sh` | (메타) | ⟦CI:id⟧ 태그 ↔ `checks/id.sh` 1:1 (빈약속·고아 차단) |
| `dup-signature.sh` | dup-signature | 중복 함수명 (Python def·C/C++), `.dup-allow` 예외 |
| `format.sh` | format | formatter `--check` (clang-format/black/prettier) |
| `index-fresh.sh` | index-fresh | 함수/전역 인덱스 ↔ 코드 동기 |
| `memory.sh` | memory | clang-tidy + AddressSanitizer (C/C++, 없으면 graceful) |
| `tests-ran.sh` | tests-ran | TEST_CMD/pytest 실행·통과 |
| `install.sh` | — | 코어3+checks 복사·.gitignore·CLAUDE.md marker 멱등 |

## L1 함수 단위 (SIL)

- 각 check 의 grep/sed 정규식이 **위반 fixture 는 잡고, 정상 fixture 는 통과**시키는가.
- `check-mapping.sh`: placeholder `⟦CI:<id>⟧`·`⟦CI⟧`(id 없음) 제외, 실제 id 만 매칭.
- `dup-signature.sh`: 제어문(`if/while/for…`) 오탐 제외, `.dup-allow` 적용.

## L2 단일 프로그램

- **SIL** (타깃 프로젝트): 각 `checks/<id>.sh <fixture-dir>` → 위반 fixture exit 1, 정상 fixture exit 0, 도구 없으면 graceful exit 0.
- **SIL (install)**: `install.sh $(mktemp -d) --all` → 코어3+checks+도메인 복사, `.gitignore` `.omc/` 1회, CLAUDE.md marker 1회; 재실행 멱등.
- **HIL**: 실 프로젝트 pre-commit / `ci/coding-gates.yml` 게이트에서 위반 커밋 차단.

## 기록

`SIL/_template/` · `HIL/_template/` 를 `YYYY-MM-DD_<topic>/` 로 복사해 채운다. 완료 시 상위 INDEX 갱신.
