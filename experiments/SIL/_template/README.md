# [통합 SIL 템플릿] `<topic>`

> **사용법**: 본 `_template/` 폴더를 `experiments/SIL/YYYY-MM-DD_<topic>/` 로 복사한 뒤 아래를 채운다.
> 통합(L3) SIL = 다수 번들을 **격리 샌드박스**(`mktemp` 프로젝트, mock `CLAUDE_HOME`)에 설치해 상호작용 검증. 라이브 에이전트 없음.
> **SIL 수행 위치**: 번들이 설치된 **다른(타깃) 프로젝트**에서 수행 후 결과만 여기에 반영(기록). 완료 후 상위 [INDEX.md](../../INDEX.md) §1 에 한 줄 추가.

## 목적

(무엇을 통합 검증하는가 — 예: INT-1 전 번들 설치 시 경로 충돌·CLAUDE.md marker 중복 없음)

- **수행 프로젝트 / commit**: `<repo>@<hash>` · **반영 일자**: `YYYY-MM-DD`

## 검증 대상

- 대상 번들: (예: 9개 전부 / coding+debt)
- 시나리오 ID: (INT-1 ~ INT-5, → [마스터 §4.3](../../README.md))

## 환경

- 샌드박스: `mktemp -d` 프로젝트 루트
- mock: `CLAUDE_HOME=<tmp>` (실 `~/.claude` 비오염)
- 커밋/빌드: (해당 시 git hash)

## 실행 절차

```bash
SANDBOX=$(mktemp -d)
# 예: 전 번들 설치
for b in acronym coding debt code_review external_reference git_workflow issue_fix sw_structure user_instruction; do
  "<repo>/$b/install.sh" "$SANDBOX" --all 2>&1 | tee "results/install_$b.log"
done
# 검증: marker 중복, .gitignore, 경로 충돌
grep -c 'kuks_agent_setup:' "$SANDBOX/CLAUDE.md"
```

## 결과

| 시나리오 | 측정값 | 기대값 | 판정 |
|----------|--------|--------|------|
| (예) CLAUDE.md marker 수 | — | 9 (각 1회) | ⏳ |
| (예) .gitignore `.omc/` | — | 1회 | ⏳ |
| (예) 경로 충돌 | — | 0 | ⏳ |

## 분석 / 결론

(PASS/FAIL 판정 근거, 발견된 충돌, 후속 조치)

## 산출물

- `results/` — 로그·출력
- `scripts/` — (있으면) 재현 스크립트
