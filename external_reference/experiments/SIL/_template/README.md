# [external_reference 단위 SIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.
> **SIL 수행 위치**: 번들이 설치된 **다른(타깃) 프로젝트**에서 수행 후 결과만 여기에 반영(기록).

## 목적 / 레벨

- 레벨: L2 단일 프로그램 (`install.sh`)
- **수행 프로젝트 / commit**: `<repo>@<hash>` · **반영 일자**: `YYYY-MM-DD`

## 실행 절차

```bash
SB=$(mktemp -d)
<repo>/external_reference/install.sh "$SB"        # 1회
<repo>/external_reference/install.sh "$SB"        # 2회 (멱등)
grep -c 'kuks_agent_setup:external_reference' "$SB/CLAUDE.md"      # 기대 1
ls "$SB/docs/claude_guideline/external_reference/"
```

## 결과

| 케이스 | 측정 | 기대 | 판정 |
|--------|------|------|------|
| 규칙 파일 복사 | — | docs/claude_guideline/external_reference/ 존재 | ⏳ |
| CLAUDE.md marker | — | 1회 | ⏳ |
| 재실행 멱등 | — | 2회째 "스킵" | ⏳ |
| 표준 인덱스 | — | coding_standards.md grep 태그 정합 | ⏳ |

## 분석 / 결론

(경로 SSOT 준수, 비파괴 동작)
