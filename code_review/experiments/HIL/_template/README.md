# [code_review 단위 HIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. HIL = 실제 Claude Code 런타임("하드웨어" = 하네스). 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.

## 목적

실 설치 후 활성화 게이트(`review.md`)로 스킬이 활성화되고 규칙이 세션에 주입되는가. 리뷰 결과는 `docs/code_review/<subject>/YYYY-MM-DD.md` 경로 준수.

## 환경

- 타깃 프로젝트 / commit:
- 설치: `./code_review/install.sh <target>`

## 실행 절차

1. 타깃에 `install.sh` 설치 → 세션 시작.
2. 규칙 트리거("코드 리뷰"/"코드 분석" 요청) → 규칙 활성·기록 경로 준수 확인.

## 결과

| 항목 | 관찰 | 기대 | 판정 |
|------|------|------|------|
| 게이트 활성화 | — | `review.md` 존재 시 스킬 활성 | ⏳ |
| 규칙 주입 | — | 세션 컨텍스트 반영 | ⏳ |
| 기록 경로 | — | docs/code_review/<subject>/YYYY-MM-DD.md | ⏳ |
| never-self-approve | — | 동일 컨텍스트 자기승인 차단 | ⏳ |

## 정리

(기록 경로 SSOT 준수, 비파괴)
