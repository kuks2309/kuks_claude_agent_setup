# [coding 단위 HIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. HIL = 실제 Claude Code/Git 런타임. 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.

## 목적

라이브 환경에서만 드러나는 강제력: pre-commit 훅 / CI 게이트가 위반 커밋을 실제로 차단하는가, 규칙(`coding.md`)이 세션에 활성화되는가.

## 환경

- 타깃 프로젝트 / commit:
- 게이트: `.pre-commit-config.yaml` (로컬) / `ci/coding-gates.yml` (서버)

## 실행 절차

1. 타깃 프로젝트에 `install.sh --all` → `pre-commit install`.
2. 위반 코드(중복 함수·`eval`·미포맷) 커밋 시도.
3. 게이트 차단 + 정확한 check 메시지 관찰.

## 결과

| 항목 | 관찰 | 기대 | 판정 |
|------|------|------|------|
| pre-commit 차단 | — | 위반 커밋 거부 | ⏳ |
| CI 게이트 | — | PR 체크 실패 | ⏳ |
| 규칙 활성화 | — | `coding.md` 컨텍스트 주입 | ⏳ |

## 정리

(차단 우회 가능성, 도구 미설치 환경 graceful 동작)
