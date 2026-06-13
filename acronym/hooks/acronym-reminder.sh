#!/usr/bin/env bash
# UserPromptSubmit 훅 — 영어 약자 표기 규칙을 매 턴 컨텍스트에 주입.
# stdout 이 컨텍스트로 들어가 답변 작성 시 규칙이 적용되게 한다.
cat <<'EOF'
[표기 규칙] 영어 약자는 첫 등장 시 "약어(영어 단어)" 형식으로 병기한다. 예: KST(Korea Standard Time). 영어 전체 단어만(한국어 병기 없음). 코드·파일명·URL·고유명사·형식 리터럴은 예외.
EOF
