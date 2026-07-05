# 영어 약자 표기 (English Acronym Notation)

> **본 파일은 지시용.** 영어 약자는 첫 등장 시 `약어(영어 단어)` 형식으로 병기한다.

## 1. 목적

약자만 쓰면 읽는 사람(사람·다음 세션 Claude)이 의미를 복원하지 못한다 — 인지 부채. 약자에 영어 전체 단어를 병기해 의미를 자족적으로 보존한다.

## 2. 규칙

- 영어 약자는 **첫 등장 시** `약어(영어 단어)` 형식으로 병기. 예: `KST(Korea Standard Time)`.
- **영어 전체 단어만** — 한국어 풀이는 넣지 않는다.
- 적용 대상: **답변 텍스트 + 작성 문서** 둘 다.

## 3. 예외 (병기 불필요)

- 코드·식별자·파일명·경로 (`CLAUDE.md`, `JSON`, `README` 등)
- 백틱·코드블록·URL(Uniform Resource Locator) 안의 토큰
- 형식 리터럴 (예: 날짜 형식의 `(KST)`)
- 제품·고유명사 (GitHub, ROS2 등)

예외 목록은 검토 훅(`acronym-review.py`)의 화이트리스트와 대체로 맞춘다 (화이트리스트는 정답 게이트가 아니라 되묻기 소음을 줄이는 용도).

## 4. 설치 (전역)

본 번들 폴더(`acronym/`)의 `install.sh` 로 `~/.claude` 에 설치한다:

```bash
cd acronym && ./install.sh
```

스크립트가 (1) 규칙·검토 훅을 `~/.claude/acronym/` 로 복사, (2) 등록 스니펫을 `~/.claude/CLAUDE.md` 에 append, (3) `~/.claude/settings.json` 에 Stop 검토 훅 1종을 멱등 등록한다 (기존 설정 보존, 사전 백업). 옛 훅(`acronym-reminder.sh`·`acronym-check.py`)이 남아 있으면 파일·등록을 함께 정리한다.

## 5. 적용 방식

규칙 적용은 두 층이다.

- **CLAUDE.md 규칙 (주 적용)**: Claude 가 §2 규칙을 읽고 답변·문서를 쓰면서 병기한다.
- **Stop 검토 훅 (`acronym-review.py`, 안전망)**: 답변을 마치면 미병기 후보 약자를 제시하고, Claude 가 **스스로 확인해 누락이면 보완**하게 한다. 위반을 단정하거나 강제 재작성을 시키지 않으므로(요청형), 화이트리스트 오탐이 있어도 무해하다. 무한 루프 방지(`stop_hook_active` → 검토 최대 1패스).

> 훅 변경은 `~/.claude/settings.json` 재로딩(세션 재시작) 후 적용된다.
