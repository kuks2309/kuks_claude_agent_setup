# [acronym 단위 SIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. SIL = 격리 샌드박스, 라이브 에이전트 없음. 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.
> **SIL 수행 위치**: 본 SIL 검증은 번들이 설치된 **다른(타깃) 프로젝트**에서 수행하고 결과만 여기에 반영(기록)한다.

## 목적 / 레벨

- 레벨: L1 함수 단위 / L2 단일 프로그램 (택1 명시)
- 대상: `acronym-check.py::find_violations()` / `acronym-check.py` end-to-end / `install.sh`
- **수행 프로젝트 / commit**: `<repo>@<hash>` · **반영 일자**: `YYYY-MM-DD`

## 실행 절차

```bash
# L2 예: fixture transcript 로 Stop 훅 실행
TR=$(mktemp); printf '%s\n' '{"type":"assistant","message":{"content":[{"type":"text","text":"이 답변은 RTOS 를 설명한다"}]}}' > "$TR"
echo "{\"transcript_path\":\"$TR\",\"stop_hook_active\":false}" | python3 ../../../hooks/acronym-check.py; echo "exit=$?"

# install 멱등 (mock CLAUDE_HOME)
CH=$(mktemp -d); CLAUDE_HOME="$CH" ../../../install.sh && CLAUDE_HOME="$CH" ../../../install.sh
```

## 결과

| 케이스 | 입력 | 측정 exit/출력 | 기대 | 판정 |
|--------|------|----------------|------|------|
| 미병기 약자 | "RTOS 를 설명" | — | exit 2 + stderr | ⏳ |
| 병기 도입됨 | "RTOS(Real-Time OS)…RTOS" | — | exit 0 | ⏳ |
| whitelist | "JSON 파싱" | — | exit 0 | ⏳ |
| 7자+ 제외 | "CODEOWNERS" | — | exit 0 | ⏳ |
| stop_hook_active | true | — | exit 0 (루프방지) | ⏳ |
| install 멱등 | 2회 실행 | — | 2회째 "스킵" | ⏳ |

## 분석 / 결론

(거짓음성·거짓양성 케이스, whitelist 보강 필요 여부)
