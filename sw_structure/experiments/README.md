# sw_structure — 단위 검증 (SIL / HIL)

> 본 번들의 **L2 단일 프로그램**(install.sh) 검증을 기록한다. 통합 결과는 상위 `../../experiments/INDEX.md` 로 집계.
> 검증 모델·배치 규칙 → `../../experiments/README.md`.
> **SIL 수행 위치**: SIL 검증은 번들이 설치된 **다른(타깃) 프로젝트**에서 수행하고 결과만 여기에 반영(기록)한다.

## 번들 성격

SW 구조 분석(파일 의존 그래프·클래스·시퀀스 다이어그램, mermaid). 실행 코드는 `install.sh`(멱등 설치) 중심 → L1 함수 단위 대상은 적고 **L2 단일 프로그램**이 핵심.

## 검증 대상

| 대상 | 종류 | 검증 초점 |
|------|------|-----------|
| `install.sh` | 설치 프로그램 | `docs/claude_guideline/sw_structure/` 복사 · CLAUDE.md `kuks_agent_setup:sw_structure` marker 멱등 · 비파괴 |

## L2 단일 프로그램

- **SIL** (타깃 프로젝트): `install.sh $(mktemp -d)` → 규칙 파일 복사, marker 1회, 재실행 멱등(2회째 "스킵"). 단일 규칙 파일 복사.
- **HIL**: 실 프로젝트 설치 후 활성화 게이트(`structure.md` 존재)로 스킬 활성. 분석 결과는 `docs/sw_structure/<subject>/YYYY-MM-DD.md` 경로 준수(품질 판단은 code_review 영역).

## 기록

`SIL/_template/` · `HIL/_template/` 를 `YYYY-MM-DD_<topic>/` 로 복사해 채운다. 완료 시 상위 INDEX 갱신.
