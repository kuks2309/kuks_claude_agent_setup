# mistake — 단위 검증 (SIL / HIL)

> 본 번들의 **L1 함수/스크립트 + L2 단일 프로그램** 검증을 기록한다. 통합 결과는 상위 `../../experiments/INDEX.md` 로 집계.
> 검증 모델·배치 규칙 → `../../experiments/README.md`.
> **SIL(Software-In-the-Loop) 수행 위치**: SIL 검증은 번들이 설치된 **다른(타깃) 프로젝트**에서 수행하고 결과만 여기에 반영(기록)한다.

## 번들 성격

Claude 실패 사건(2-type) 기록·closure 규칙. 실행 코드는 `install.sh`(멱등 설치) + `entry-lint.sh`(형식 검증) + `mistake-inject.py`(SessionStart 주입) 3 종.

## 검증 대상

| 대상 | 종류 | 검증 초점 |
| --- | --- | --- |
| `install.sh` | 설치 프로그램 (L2) | `docs/claude_guideline/mistake/`·`docs/claude-mistake/` 생성 · CLAUDE.md `kuks_agent_setup:mistake` marker 멱등 · SessionStart 훅 등록 멱등 · 비파괴 |
| `checks/entry-lint.sh` | 형식 이빨 (L1) | 정상 entry PASS · 위반 entry(정합·owner·TBD(To Be Determined)·7 일 초과 등) FAIL 검출 · entry 0 건/폴더 부재 시 PASS |
| `hooks/mistake-inject.py` | SessionStart 훅 (L1) | INDEX §메타 패턴·§미해결 항목 추출 · open entry 목록 · 기록 부재 시 무출력 · 항상 exit 0 |

## L2 단일 프로그램

- **SIL** (타깃 프로젝트): `install.sh $(mktemp -d)` → 규칙·이빨·훅 복사, marker 1회, 재실행 멱등(2회째 "스킵"), settings.json 훅 1회 등록.
- **HIL**: 실 프로젝트 설치 후 활성화 게이트(`mistake.md` 존재)로 룰 활성. 실제 사건 발생 → entry 기록 → SessionStart 주입 확인.

## 기록

`SIL/_template/` · `HIL/_template/` 를 `YYYY-MM-DD_<topic>/` 로 복사해 채운다. 완료 시 상위 INDEX 갱신.
