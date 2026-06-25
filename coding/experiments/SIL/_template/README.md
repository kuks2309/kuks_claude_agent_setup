# [coding 단위 SIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.
> **SIL 수행 위치**: 본 SIL 검증은 번들이 설치된 **다른(타깃) 프로젝트**에서 수행하고 결과만 여기에 반영(기록)한다.

## 목적 / 레벨

- 레벨: L1 함수 단위 / L2 단일 프로그램 (택1 명시)
- 대상 check: (예: `dup-signature.sh`, `banned-pattern.sh`)
- **수행 프로젝트 / commit**: `<repo>@<hash>` · **반영 일자**: `YYYY-MM-DD`

## 실행 절차

```bash
# 타깃 프로젝트에 설치된 check 를 fixture 로 실행 (예: dup-signature)
mkdir -p fixture && cat > fixture/a.py <<'EOF'
def foo(): pass
def foo(): pass   # 중복 → 차단 기대
EOF
<target>/docs/claude_guideline/coding/checks/dup-signature.sh fixture; echo "exit=$?"
```

## 결과

| check | fixture | 측정 exit/출력 | 기대 | 판정 |
|-------|---------|----------------|------|------|
| dup-signature | def foo ×2 | — | exit 1 | ⏳ |
| dup-signature | 정상 | — | exit 0 | ⏳ |
| banned-pattern | `eval(` 포함 | — | exit 1 | ⏳ |
| check-mapping | 태그↔스크립트 정합 | — | exit 0 | ⏳ |
| install 멱등 | 2회 실행 | — | 2회째 스킵 | ⏳ |

## 분석 / 결론

(거짓양성/거짓음성, `.dup-allow` 보강, graceful skip 동작)
