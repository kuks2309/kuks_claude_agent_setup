# mistake 번들 — Claude 실수·규칙 위반 기록

Claude 의 **실패 사건**을 2-type 단일 체계로 기록하고 closure(재발 방지 자산 반영)까지 강제하는 규칙. `type: mistake`(지식 공백 → 지식·컨텍스트 보강) 와 `type: rule-violation`(명시 규칙 위반 → 강제 메커니즘 보강) 을 한 폴더·한 형식으로 운용하며, 판정 tie-break 는 rule-violation 우선이다. 판단 기준은 마크다운(`mistake.md`), 세션 진입 리마인드는 SessionStart 훅, 형식 강제는 `checks/entry-lint.sh` 다.

> 계보: v1/v2 저장소의 `claude-mistake`·`claude-rule-violation` 자매 SSOT(Single Source of Truth) 를 v2.0 에서 단일 체계로 통합 후 본 번들로 이식 (2026-07-05). SIL(Software-In-the-Loop) 2 라운드 (gap G1~G11 closure) 를 거친 형식이다.

## 설치

```bash
cd mistake && ./install.sh <타깃-프로젝트-루트>
```

`mistake.md` + `checks/` + `hooks/` 를 `docs/claude_guideline/mistake/` 로 복사, entry 폴더 `docs/claude-mistake/` 생성(비파괴), `CLAUDE.md` 에 등록 스니펫 append, 타깃 `.claude/settings.json` 에 SessionStart(inject) 훅 등록(python 있을 때). **활성화 게이트**: `mistake.md` 가 그 경로에 없으면 룰 비활성. **설치 산출물은 규칙·이빨·훅뿐** — `install.sh`·`claude.snippet.md`·`README.md` 는 복사하지 않는다.

## 이관 (타 프로젝트) — 설치·검증

본 번들은 **self-contained**(외부 도구·상대경로 의존 0)라 폴더째 옮겨 설치한다.

```bash
# 1) 이관 — 어디서 실행하든 $SRC 기준
./mistake/install.sh /path/to/other-project

# 2) 설치 검증 (대상 프로젝트에서)
ls /path/to/other-project/docs/claude_guideline/mistake/          # mistake.md + checks/ + hooks/
ls -d /path/to/other-project/docs/claude-mistake/                 # entry 폴더
grep -c 'kuks_agent_setup:mistake' /path/to/other-project/CLAUDE.md   # 1
python3 - <<'PY'
import json; h=json.load(open('/path/to/other-project/.claude/settings.json'))['hooks']
print([g for g in h.get('SessionStart', [])])
PY
```

- **멱등** — 재실행 안전(규칙 덮어쓰기, 마커·훅 "스킵", `settings.json` `.bak` 백업). **갱신 = 재설치**.
- **python 부재** — 훅 등록·entry-lint 실행만 생략(경고), 규칙 파일은 설치됨(강제력 0으로 정직 강등).
- **기존 기록 보존** — `docs/claude-mistake/` 는 `mkdir -p` 만 수행, 기존 entry·INDEX 를 건드리지 않는다.

## 강제 모델 — 정직 선언

- **SessionStart 훅**(`hooks/mistake-inject.py`) = 세션 시작 시 `docs/claude-mistake/INDEX.md` §메타 패턴·§미해결 항목 + open entry 목록을 주입 — 과거 실패를 세션 초기 컨텍스트로 승격해 동일 실수 재발과 open entry 방치를 차단. 기록이 없으면 침묵(no-op).
- **entry-lint 이빨**(`checks/entry-lint.sh`) = 형식·closure 규칙(단일 frontmatter·id/파일명·type↔category 정합·owner 규칙·TBD(To Be Determined) 금지·5 절 순서·open 7 일 시한) 기계 검출. pre-commit·CI(Continuous Integration) 에 연결하면 커밋 게이트로 승격 가능.
- **한계(정직)** — 사건 발생 시 entry 를 *작성하는 행위 자체*는 자기보고 의존 **advisory** (CLAUDE.md 스니펫 + 세션 주입으로 상기할 뿐 강제 불가). entry-lint 는 "작성된 기록의 형식"만 강제하며 "기록 누락"은 검출하지 못한다. python 없는 환경에선 훅·이빨 모두 생략 — 규칙 텍스트만 생존한다.

## 자체 점검

```bash
# entry 형식·closure 검증 (타깃 프로젝트 루트에서)
./docs/claude_guideline/mistake/checks/entry-lint.sh

# open entry 수동 확인
grep -l '^status: open' docs/claude-mistake/*.md 2>/dev/null || echo "(open entry 없음)"
```

## 변경 절차

- SSOT 는 본 번들 폴더. 규칙 변경은 사용자 승인 후 `mistake.md` + (필요 시) `hooks/`·`checks/` + `claude.snippet.md` 를 **단일 번들 VERSION 으로 동반 갱신**(부분 드리프트 금지).
- category enum 추가·변경은 `mistake.md` §카테고리 정의 와 `checks/entry-lint.sh` 의 enum 상수를 함께 맞춘다.

## 검증 (experiments/)

`install.sh` 멱등성·비파괴, `entry-lint.sh` 판정 정확도는 `experiments/SIL/` 에 기록(타깃 프로젝트에서 수행 후 반영). 통합 결과는 상위 `../experiments/INDEX.md` §2 로 집계.

## 파일

`mistake.md`(코어 규칙 — 2-type 범위·항목 형식·카테고리 10 종·재분류 절차·closure 규칙·INDEX 템플릿) · `hooks/mistake-inject.py`(SessionStart 요약 주입) · `checks/entry-lint.sh`(형식·closure 기계 검증) · `install.sh`(멱등 설치) · `claude.snippet.md`(CLAUDE.md 등록) · `experiments/`(SIL/HIL 검증)
