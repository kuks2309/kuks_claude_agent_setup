# [통합 HIL 템플릿] `<topic>`

> **사용법**: 본 `_template/` 폴더를 `experiments/HIL/YYYY-MM-DD_<topic>/` 로 복사한 뒤 아래를 채운다.
> 통합(L3) HIL = 번들을 **실제 Claude Code 런타임**("하드웨어" = 하네스)에 설치해 검증. 실 `~/.claude`·`settings.json`·훅 발화·라이브 세션.
> ⚠️ 실 환경을 변경하므로 사전 백업(`settings.json.bak`)·전용 테스트 프로젝트 사용. 완료 후 상위 [INDEX.md](../../INDEX.md) §1 에 한 줄 추가.

## 목적

(하네스가 있어야만 드러나는 무엇을 검증하는가 — 예: INT-4 acronym 훅 + 타 훅 공존, 실 세션 발화)

## 검증 대상

- 대상 번들 / 훅: (예: acronym Stop·UserPromptSubmit + coding pre-commit)
- 시나리오 ID: (→ [마스터 §4.3](../../README.md))

## 환경

- Claude Code 버전 / 세션: 
- 설치 루트: 실 `~/.claude` 또는 전용 `CLAUDE_HOME`
- 사전 백업: `settings.json.bak` 확인

## 실행 절차

```bash
# 예: acronym 설치 후 실 세션에서 훅 발화 확인
./acronym/install.sh                 # ~/.claude 에 훅 등록
# 세션 재시작 → 미병기 약자 답변 유도 → Stop 훅 차단 관찰
```

## 결과

| 항목 | 관찰 | 기대 | 판정 |
|------|------|------|------|
| (예) Stop 훅 차단 발화 | — | 미병기 약자 답변 차단 | ⏳ |
| (예) 훅 공존(충돌) | — | 타 훅과 충돌 0 | ⏳ |
| (예) CLAUDE.md 등록 활성 | — | 규칙 컨텍스트 주입 | ⏳ |

## 분석 / 결론

(PASS/FAIL, 라이브에서만 드러난 차이, 후속 조치)

## 산출물 / 정리

- `logs/` — 세션·훅 로그
- 정리: `settings.json.bak` 복원 또는 테스트 프로젝트 폐기
