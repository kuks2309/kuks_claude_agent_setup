# mistake — 기각(retraction)·오염 청소 체계 + lint 검출 확장

## 2026-08-01 09:20 (KST) — entry-lint 검출 2종 추가(교차 id 중복·유령 자산) + 따옴표 오탐 수정

- 대상:
  - `mistake/checks/entry-lint.sh` — 내장 python 에 `asset_path(tok)` 함수·`ROOT`·`id_map` 전역 추가
  - `mistake/mistake.md`·`mistake/README.md` — 검출 항목 서술 동기
- 변경: ① 교차 파일 id 중복 검출 — 전 entry 의 frontmatter id 를 `id_map` 에 수집, 2개 이상 파일이 같은 id 면 별도 `[FAIL] id 중복` 블록. ② closed entry 의 `reflected_assets` 경로 실재 검증 — 각 항목 첫 토큰을 정규화(backtick/따옴표 제거, `#앵커`·`:L번호` 절단, `~`/절대/상대 해석)해 존재하지 않으면 "유령 자산" FAIL. retracted 는 청소로 자산이 정당 삭제될 수 있어 검사 제외. YAML 인용 스타일(`- "path"`) 오탐은 따옴표 strip 으로 수정.
- 사유: LGIT-C6-Cobot 실전 감사 실측 — 같은 id 를 두 entry 가 쓰는 사례 2쌍(`2026-07-23-001`·`2026-07-31-004`, bare id 인용의 지시 대상 모호화)과 존재하지 않는 자산을 근거로 closed 한 사례 1건이 실재. 재설치 후 실전 17 entry 재검에서 진성 2건(유령 자산·open 시한 초과)만 검출, 오탐 0. SIL(Software-In-the-Loop) fixture 6종(실재/유령/중복쌍/open 스킵/기각-청소삭제) 전건 의도 판정.
- 커밋: `2fdbb9b` feat(mistake): entry-lint 검출 2종 추가 / `1ef3c38` fix(mistake): 따옴표 오탐 수정 (origin·fito 병합 push `b0ee9c0`)

## 2026-08-01 07:20 (KST) — status `retracted` 신설: 오판 기록 tombstone + 오염 청소(sweep) 절차

- 대상:
  - `mistake/mistake.md` — status enum `retracted` 추가, §기각·오염 청소 절차 신설(1단계 tombstone·2단계 sweep·청소 완료 전 취급), §type 재분류/사용 규칙/Closure/INDEX 템플릿/자체 점검 연동 갱신
  - `mistake/hooks/mistake-inject.py` — `open_entries()` 가 `status: retracted` 를 인식: 학습 자료 주입 금지, owner 잔존(청소 미완) 건만 "(기각·청소 미완)" 표기로 미해결 목록 주입. 출력 문구 "미해결 entry — closure 또는 오염 청소" 로 갱신
  - `mistake/checks/entry-lint.sh` — retracted 형식 검출(기각 각주·오염 목록 존재, 청소 미완 7일 초과, 청소 완료 주장인데 TBD/추후/미처리 잔존)
  - `mistake/README.md` — 훅·lint 설명 동기
- 변경: 오판으로 판명된 entry 를 삭제(이력 상실)도 방치(오염)도 아닌 `retracted` 로 처리 — 기각 각주 + `reflected_assets` 역추적 오염 목록으로 오판이 낳은 주석·문서·메모리를 청소하고, 즉시 청소 불가 항목은 `debt` 번들에 조건부 위임(미설치 시 무해).
- 사유: 사용자 문제 제기 "오판이 기록에 박제되어 코드가 계속 오염" — 기존 체계는 사건 기록·재발 방지 반영만 있고 기록 자체의 오판을 정정·청소하는 경로가 없었음(인지 부채 되먹임). SIL fixture 6종(open/closed/retracted 정상·시한초과·형식누락·허위완료) 전건 의도 판정.
- 커밋: `031534c` feat(mistake): 기각(retracted)·오염 청소 절차 신설
