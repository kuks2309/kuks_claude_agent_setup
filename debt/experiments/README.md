# debt — 단위 검증 (SIL / HIL)

> 본 번들의 **L1 함수 단위 + L2 단일 프로그램** 검증을 기록한다. 통합 결과는 상위 `../../experiments/INDEX.md` 로 집계.
> 검증 모델·배치 규칙 → `../../experiments/README.md`.
> **SIL 수행 위치**: SIL 검증은 번들이 설치된 **다른(타깃) 프로젝트**에서 수행하고 결과만 여기에 반영(기록)한다.

## 검증 대상 코드 (checks/*.sh = 2 + install.sh)

| 스크립트 | ⟦CI⟧ 태그 | 판정 초점 |
|----------|-----------|-----------|
| `check-mapping.sh` | (메타) | ⟦CI:id⟧ 태그 ↔ `checks/id.sh` 1:1 |
| `debt-marker.sh` | debt-marker | TODO/FIXME/HACK 가 `debt-<id>` 참조하는가 |
| `install.sh` | — | debt.md + registry template 배치·CLAUDE.md marker 멱등 |

## L1 함수 단위 (SIL)

- `debt-marker.sh` 정규식 `debt[-_ ]?[0-9]+`:
  - OK: `TODO(debt-042)`, `FIXME[debt-7]`, `HACK: debt-12`.
  - 차단: 맨 `TODO`/`FIXME`/`HACK` (debt id 미참조).
- 다국어/주석 형태·확장자 필터(`--include`) 정확성.

## L2 단일 프로그램

- **SIL** (타깃 프로젝트): `debt-marker.sh <fixture-dir>` → 미등록 마커 exit 1, 전부 등록 exit 0, 마커 없음 exit 0; `check-mapping.sh` → 정합 exit 0.
- **SIL (install)**: `install.sh $(mktemp -d)` → 배치·marker 멱등.
- **HIL**: 실 프로젝트 게이트에서 미등록 마커 차단 → registry 등록 강제.

## 기록

`SIL/_template/` · `HIL/_template/` 를 `YYYY-MM-DD_<topic>/` 로 복사해 채운다. 완료 시 상위 INDEX 갱신.
