#!/usr/bin/env bash
# adr-fields.sh 회귀 시험 — 인정 표기(영어·한국어·번호·목록형)와 진짜 누락을 가른다.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHK="$(dirname "$HERE")/adr-fields.sh"
PASS=0; FAIL=0
ok(){ echo "  PASS $1"; PASS=$((PASS+1)); }
no(){ echo "  FAIL $1: ${2:-}"; FAIL=$((FAIL+1)); }

ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
mkdir -p "$ROOT/docs/adr"

# ADR 하나만 담은 트리를 만들고 검사 → 실패 건수를 돌려준다
violations(){ # $1=파일내용
  local d; d="$(mktemp -d "$ROOT/case.XXXXXX")"
  mkdir -p "$d/adr"
  printf '%s\n' "$1" > "$d/adr/x.md"
  bash "$CHK" "$d" 2>/dev/null | grep -c '✗'
}

echo "== 인정 표기 (위반 0 이어야 함) =="
v=$(violations '# ADR
## Status
Accepted
## Context
c
## Decision
d
## Consequences
e
## Rollback
N/A')
[ "$v" = 0 ] && ok english_headings || no english_headings "위반 $v"

v=$(violations '# ADR
## 상태
채택
## 맥락
c
## 결정
d
## 영향·주의
e
## 롤백
N/A (가역)')
[ "$v" = 0 ] && ok korean_headings || no korean_headings "위반 $v"

v=$(violations '# ADR
## 1. Context (배경)
c
## 2. Decision (결정)
d
## 3. Status
Accepted
## 4. Consequences (영향)
e
## 6. Rollback Plan
N/A')
[ "$v" = 0 ] && ok numbered_headings || no numbered_headings "위반 $v"

v=$(violations '# ADR
- Status: Accepted
- **Context**: 배경 서술
- Decision: 정함
- **Consequences**: 영향
- Rollback: N/A (가역)')
[ "$v" = 0 ] && ok list_labels || no list_labels "위반 $v"

v=$(violations '# ADR
- **상태**: 채택
### 3-1 맥락
c
## 결정
d
## 결과
e
**되돌리기**: N/A')
[ "$v" = 0 ] && ok mixed_forms || no mixed_forms "위반 $v"

echo "== 진짜 누락 (검출돼야 함) =="
v=$(violations '# ADR
## Status
Accepted
## Context
c
## Decision
d
## Consequences
e')
[ "$v" = 1 ] && ok missing_rollback || no missing_rollback "위반 $v (기대 1)"

v=$(violations '# 재작성 브리프
## 1. 왜 재작성인가
본문')
[ "$v" = 5 ] && ok non_adr_all_missing || no non_adr_all_missing "위반 $v (기대 5)"

echo "== 산문 오인식 방지 =="
# 콜론 없는 산문에 필드어가 섞여 있어도 라벨로 인정하지 않는다
v=$(violations '# ADR
## Status
Accepted
## Context
c
## Decision
d
## Consequences
e
- 결정된 사항은 롤백 절차와 무관하다')
[ "$v" = 1 ] && ok prose_not_label || no prose_not_label "위반 $v (기대 1 — Rollback 만)"

echo "== 경계 =="
d="$(mktemp -d "$ROOT/empty.XXXXXX")"
bash "$CHK" "$d" >/dev/null 2>&1
[ "$?" = 0 ] && ok no_adr_exit0 || no no_adr_exit0 "ADR 없을 때 exit≠0"

echo "-- 결과: PASS=$PASS FAIL=$FAIL --"
[ "$FAIL" = 0 ]
