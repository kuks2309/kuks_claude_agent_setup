# [debt 단위 HIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. HIL = 실제 런타임. 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.

## 목적

라이브 게이트에서 미등록 마커가 실제로 차단되어 registry 등록을 강제하는가, `debt.md` 규칙이 세션에 활성화되는가.

## 환경

- 타깃 프로젝트 / commit:
- 게이트: pre-commit / CI

## 실행 절차

1. 타깃에 `install.sh` → `pre-commit install`.
2. 맨 `# TODO` 포함 코드 커밋 시도 → 차단 확인.
3. `registry.md` 등록 + `debt-042` 부착 후 재커밋 → 통과 확인.

## 결과

| 항목 | 관찰 | 기대 | 판정 |
|------|------|------|------|
| 미등록 마커 차단 | — | 커밋 거부 | ⏳ |
| 등록 후 통과 | — | 커밋 허용 | ⏳ |
| 규칙 활성화 | — | `debt.md` 컨텍스트 | ⏳ |

## 정리

(registry 경로 SSOT 준수, 우회 가능성)
