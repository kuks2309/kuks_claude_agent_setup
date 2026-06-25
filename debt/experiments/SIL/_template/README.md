# [debt 단위 SIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.
> **SIL 수행 위치**: 본 SIL 검증은 번들이 설치된 **다른(타깃) 프로젝트**에서 수행하고 결과만 여기에 반영(기록)한다.

## 목적 / 레벨

- 레벨: L1 함수 단위 / L2 단일 프로그램 (택1 명시)
- 대상: `debt-marker.sh` / `check-mapping.sh` / `install.sh`
- **수행 프로젝트 / commit**: `<repo>@<hash>` · **반영 일자**: `YYYY-MM-DD`

## 실행 절차

```bash
mkdir -p fixture
printf 'x = 1  # TODO: 리팩터\n'           > fixture/bad.py    # 미등록 → 차단 기대
printf 'y = 2  # TODO(debt-042): 리팩터\n' > fixture/ok.py     # 등록 → 통과 기대
<target>/docs/claude_guideline/debt/checks/debt-marker.sh fixture; echo "exit=$?"
```

## 결과

| 케이스 | fixture | 측정 exit/출력 | 기대 | 판정 |
|--------|---------|----------------|------|------|
| 맨 TODO | `# TODO:` | — | exit 1 | ⏳ |
| 등록 마커 | `# TODO(debt-042)` | — | exit 0 | ⏳ |
| 마커 없음 | 정상 코드 | — | exit 0 | ⏳ |
| check-mapping | 태그↔스크립트 | — | exit 0 | ⏳ |
| install 멱등 | 2회 실행 | — | 2회째 스킵 | ⏳ |

## 분석 / 결론

(정규식 거짓양성/거짓음성, 확장자 필터 누락 여부)
