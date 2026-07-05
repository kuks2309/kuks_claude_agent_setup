# [mistake 단위 SIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.
> **SIL(Software-In-the-Loop) 수행 위치**: 번들이 설치된 **다른(타깃) 프로젝트**에서 수행 후 결과만 여기에 반영(기록).

## 목적 / 레벨

- 레벨: L1 (`entry-lint.sh`·`mistake-inject.py`) 또는 L2 (`install.sh`)
- **수행 프로젝트 / commit**: `<repo>@<hash>` · **반영 일자**: `YYYY-MM-DD`

## 실행 절차

```bash
SB=$(mktemp -d)
<repo>/mistake/install.sh "$SB"        # 1회
<repo>/mistake/install.sh "$SB"        # 2회 (멱등)
grep -c 'kuks_agent_setup:mistake' "$SB/CLAUDE.md"              # 기대 1
ls "$SB/docs/claude_guideline/mistake/" "$SB/docs/claude-mistake/"
(cd "$SB" && ./docs/claude_guideline/mistake/checks/entry-lint.sh)   # entry 0 건 PASS
```

## 결과

| 케이스 | 측정 | 기대 | 판정 |
| --- | --- | --- | --- |
| 규칙·이빨·훅 복사 | — | docs/claude_guideline/mistake/{mistake.md,checks/,hooks/} 존재 | ⏳ |
| entry 폴더 생성 | — | docs/claude-mistake/ 존재 (비파괴) | ⏳ |
| CLAUDE.md marker | — | 1회 | ⏳ |
| SessionStart 훅 등록 | — | 1회 (재실행 "스킵") | ⏳ |
| entry-lint 판정 | — | 정상 PASS / 위반 FAIL | ⏳ |

## 분석 / 결론

(경로 SSOT 준수, 비파괴 동작, 판정 정확도)
