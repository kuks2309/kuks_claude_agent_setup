# [acronym 단위 HIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. HIL = 실제 Claude Code 런타임("하드웨어" = 하네스). ⚠️ 실 `~/.claude` 변경 — 사전 백업. 완료 후 상위 `../../../../experiments/INDEX.md` §2 갱신.

## 목적

라이브 세션에서만 드러나는 강제력 검증: Stop 훅이 실제 답변을 차단하는가, UserPromptSubmit 리마인더가 매 턴 주입되는가.

## 환경

- Claude Code 버전 / 세션:
- 설치: `./acronym/install.sh` (또는 전용 `CLAUDE_HOME`)
- 사전 백업: `~/.claude/settings.json.bak` 확인

## 실행 절차

1. `./install.sh` → 세션 재시작.
2. 미병기 영어 약자를 포함하는 답변 유도.
3. Stop 훅 차단 → 모델이 병기 형식으로 재작성하는지 관찰.
4. settings.json 에 타 훅과 공존(충돌 없음) 확인.

## 결과

| 항목 | 관찰 | 기대 | 판정 |
|------|------|------|------|
| Stop 훅 차단 | — | 미병기 약자 답변 차단·재작성 | ⏳ |
| 리마인더 주입 | — | 매 턴 규칙 컨텍스트 | ⏳ |
| 훅 공존 | — | 타 훅 충돌 0 | ⏳ |

## 정리

- `settings.json.bak` 복원 또는 변경 유지 결정 기록.
