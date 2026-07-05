# 2026-07-05 — 세션: 영어 약자 병기 훅 — 검증(check) → AI 검토(review) 전환 + uninstall 추가

세션 기간: 2026-07-05 오전 KST(Korea Standard Time). 대상 자산: `acronym/` 번들 (repo `kuks_claude_skill_setup`, remote origin + fito).

## 개요

기존 영어 약자 병기 강제는 훅 2종(UserPromptSubmit 리마인더 + Stop 검증 `acronym-check.py`)으로 동작했다. 검증 훅이 정규식 + 화이트리스트로 위반을 **단정**해 매 턴 오탐 재작성을 유발한 것이 문제였다. 이를 **AI 판단 기반 검토 훅**으로 전환: 답변을 마치면 미병기 후보 약자를 *제시*만 하고 병기 판단은 AI 에게 위임(요청형). 리마인더는 제거. 규칙 문서(`acronym.md`)는 CLAUDE.md 포인터로 유지. 번들에 대칭 `uninstall.sh` 추가.

## 결정 히스토리 (다음 세션 주의)

- 최초 요청은 "hook 방식이 **아니라** CLAUDE.md 규칙"이었으나, 진행 중 사용자가 "답변 후 검사하는 훅이 가능한가?"로 선회 → **M2 (AI 검토 Stop 훅)** 을 명시 선택.
- 즉 **최종 결정 = 훅 유지(M2)**. 초안의 "hookless"는 대체됨.
- (세션 중 이 히스토리를 잘못 읽어 "hookless 로 되돌리자"는 오판이 있었고, 사용자 교정으로 정정. 현재 라이브·번들 모두 M2 로 일관.)

## 단계별 결과

### 1단계 — 현황 분석
- 훅 2종 구조 규명: 리마인더(무마찰) + 검증(마찰원). `acronym-check.py` 가 대문자 2~6자 미(未)화이트리스트 토큰을 위반 단정 → 강제 재작성.

### 2단계 — 설계 (M1/M2/M3)
- M1 답변 내 자기점검 / M2 AI 검토 Stop 훅 / M3 결정론 검사기(현행) 제시. 사용자 **M2 선택**.

### 3단계 — 라이브 적용 (`~/.claude`)
- 신규 `acronym-review.py` (요청형 메시지, `stop_hook_active` 루프 방지 — 검토 최대 1패스). `settings.json`: UserPromptSubmit 리마인더 제거, Stop → `acronym-review.py`. 옛 훅 파일 삭제. 4-케이스 테스트 통과.

### 4단계 — 번들 반영 (`kuks_claude_skill_setup/acronym/`)
- `hooks/acronym-review.py` 신규(check.py rename), `hooks/acronym-reminder.sh` 삭제, `install.sh` 마이그레이션(옛 훅 파일·등록 정리 + Stop 검토 훅만 등록), `acronym.md` §4/§5 개정.
- 커밋 `3e8f7f9`(feat) · `94bd167`(docs) → origin + fito 푸시, SHA(Secure Hash Algorithm) 동기 검증.

### 5단계 — uninstall.sh 추가
- install 의 역: 훅 등록 · CLAUDE.md 스니펫 · `~/.claude/acronym/` 파일 외과적 제거. 사전 백업, 멱등, `.bak` 복원 안 함(옛 reminder+check 구성 부활 방지). install→uninstall 왕복 · 멱등 테스트 통과.
- 커밋 `5b10ecd`(feat) → origin + fito 푸시, SHA 동기 검증.

## 산출물 (커밋)

| 커밋 | 내용 |
|---|---|
| `3e8f7f9` | feat(acronym): 검증 훅 → AI 검토 방식 전환 (오탐 재작성 제거) |
| `94bd167` | docs(acronym): 적용 방식 개정 (CLAUDE.md 규칙 + Stop AI 검토 훅) |
| `5b10ecd` | feat(acronym): 전역 제거 스크립트 uninstall.sh 추가 |

- 라이브(`~/.claude`): `acronym-review.py` 훅 작동 중(M2). 세션 중 `SHA` 미병기를 실제로 잡아 교정 지시함(실동작 확인).
- 번들: `install.sh` ↔ `uninstall.sh` 대칭 쌍 완성. 다른 프로젝트에서 설치→테스트→제거 반복 가능.

## 미해결 / 후속

- **`SHA` 화이트리스트 결정 대기**: 세션 중 `SHA` 가 검토 요청에 2회 걸림(git·암호 문맥 흔한 약어). 화이트리스트 추가(되묻기 소음 감소) 여부 사용자 판단 필요.
- 라이브 훅 변경은 세션 재시작 후 적용.
- 다른 프로젝트 설치 테스트 결과 피드백 대기(사용자 예고).
