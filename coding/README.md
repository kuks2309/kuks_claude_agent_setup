# coding 번들 — 코드 작성 SOP

Claude Code 에이전트가 코드 작성 시 따르는 절차 규칙 + 기계 강제(이빨). **판단 기준은 마크다운, 강제는 `checks/*.sh`(pre-commit·CI)** 로 분리한다.

## 설치

```bash
cd coding && ./install.sh <타깃-프로젝트-루트> [도메인...|--all]
# 예) ./install.sh ~/myproj ros2-coding numeric-coding
```

코어(`coding.md`·`conventions.md`·`stack.md`) + `checks/` 를 `docs/claude_guideline/coding/` 로 복사, 선택 도메인 복사, 타깃 `.gitignore` 에 `.omc/` 추가, `CLAUDE.md` 에 등록 스니펫 append. **활성화 게이트**: 본 파일들이 그 경로에 없으면 룰 비활성.

## 강제 모델 — 정직 선언

- **`⟦CI:<id>⟧`** = `checks/<id>.sh` 가 커밋된 코드에서 재도출·차단(pre-commit·CI). **에이전트가 못 속인다.**
- **`⟦훅:<id>⟧`** = `hooks/coding-<id>.py` 가 도구 호출 시점에 차단(Claude Code 훅). 사후 검출이 아니라 **사전 차단** — 하려던 작업 자체가 막힌다.
- **`⟦권고⟧`** = 재도출도 시점 차단도 불가, 자기보고에 의존 → 정직하게 advisory.
- **green ≠ good, 미탐지 ≠ 무결.**

### 무-CI 환경 강등 (큰소리 선언)

CI·pre-commit 이 없으면 **`⟦CI⟧` 도 강제력 0** 으로 강등된다(도구가 안 돈다). 그 환경에선 규칙 텍스트만 생존하며, 인덱스 등은 **수동 재생성**(`index-fresh.sh --generate`)으로 유지한다. 이 사실을 숨기지 않는다.

`⟦훅⟧` 도 같다 — `.claude/settings.json` 에 등록되지 않았거나 Claude Code 가 아닌 에이전트로 작업하면 **강제력 0**. 우회 경로(`CODING_GATE_SKIP=1`·`.allow`)도 열려 있다. 다만 우회는 명시적이라 흔적이 남는다.

## 훅 (hooks/)

| 층 | 훅 · 이벤트 | 시점 | 역할 |
| --- | --- | --- | --- |
| 1 | `coding-reminder.py` · `UserPromptSubmit` | 프롬프트 | SOP 절차 문구 주입 |
| 2 | " | 프롬프트 = **계획 전** | 프롬프트의 심볼을 함수표에서 조회해 **그 행을 주입** |
| 3 | `coding-inventory-gate.py` · `PreToolUse`(Write\|Edit\|MultiEdit\|NotebookEdit) | 수정 직전 | 표 미독이면 **차단** `⟦훅:inventory-gate⟧` |
| 4 | " | 수정 직전 | 차단 메시지에 **해당 행 동봉**(수정 payload 의 심볼 순 정렬) |
| — | " · `PostToolUse`(Read) | 읽은 직후 | 읽은 표를 세션별 기록(3층 판정 근거) |
| 5 | `coding-record-gate.py` · `Stop` | 턴 종료 | 고친 코드의 **표를 갱신했는지** 확인, 아니면 종료 1회 차단 `⟦훅:record-gate⟧` |

**1~4층은 §2(선독), 5층은 §6(갱신)** 을 맡는다. `⟦CI:index-fresh⟧` 는 커밋 시점 검사라 커밋하지 않는 턴이 비는데, 표 갱신이 미뤄져 남지 않는 실패가 그 구간에서 생긴다. 5층은 인터페이스 변경 여부를 판정하지 않고 **대면만 강제**한다(내부 로직만 바꿨으면 그대로 마치면 됨).

**1층만으로는 뚫린다 (실증)**: 실사격 저장소에 reminder 가 등록·가동 중이었는데도 함수 용도를 오판했다. 주입한 것이 *"함수표를 읽어라"* 라는 **절차**였지 *"halt_steer 는 현재 실측 위치를 새 목표로 덮어쓴다"* 라는 **사실**이 아니었기 때문. 2·4층이 사실을, 3층이 강제를 담당한다.

정렬 규칙(실측 확정): 토큰은 **단어 경계** 일치만 인정(`steer` 가 `halt_steer` 안에서 걸리면 무관한 행이 위로 올라감), 표 행(`|` 시작)은 산문 언급보다 우대. 상한 초과분은 `… 외 N행` 으로 **감췄음을 고지**한다.

**게이트 동작**: 대상 코드 파일을 등재한 **최근접 조상 모듈의 표**(모듈 로컬 = 권위본)를 이번 세션에 읽었는지 검사한다. 등재 판정은 표의 위치 컬럼 형식(`backend.py:315-349`)에 맞춘 `파일명:줄` 앵커. `docs/claude_guideline/**`(설치된 규칙 문서)는 표 후보에서 제외.

**표가 없어도 차단한다** — §2 의 "표가 없으면 먼저 만든다"를 기계로 강제. 초기엔 통과를 기본값으로 뒀으나 실측에서 **코드의 82%가 표 없이 지나가며 부채를 쌓고** 있어 뒤집었다. 완화는 `CODING_GATE=lenient`·`.allow` 로만(명시적, 흔적 남음).

## 이빨 (checks/)

| 이빨 | 태그 | 검사 |
| --- | --- | --- |
| `check-mapping.sh` | (메타) | `⟦CI⟧` ↔ `checks/*.sh`, `⟦훅⟧` ↔ `hooks/coding-*.py` 1:1 정합(번들이 자기 강제력에 거짓말 못 함) |
| `banned-pattern.sh` | `⟦CI:banned-pattern⟧` | secret·eval·raw SQL·blocking |
| `format.sh` | `⟦CI:format⟧` | 포맷터 `--check`(clang-format/black/prettier) |
| `dup-signature.sh` | `⟦CI:dup-signature⟧` | 중복 함수 시그니처 |
| `index-fresh.sh` | `⟦CI:index-fresh⟧` | 함수 인덱스 ↔ 코드 일치 |
| `memory.sh` | `⟦CI:memory⟧` | clang-tidy 정적 + AddressSanitizer 런타임 |
| `tests-ran.sh` | `⟦CI:tests-ran⟧` | 테스트 실행·통과 |
| `adr-fields.sh` | `⟦CI:adr-fields⟧` | ADR 필수 필드 |

도구 없으면 각 이빨은 graceful 생략(강제력 0, 정직히 알림).

## 도메인 (domains/) — 트리거 조건부

`memory-coding`·`concurrency-coding`·`numeric-coding`(횡단 aspect) · `ros2-coding`·`embedded-coding`(플랫폼). 트리거 감지 시 적용, 0 발화 정상. `code_review` 의 `-review` 도메인과 **write↔review 상보**.

## 자체 점검

```bash
cd docs/claude_guideline/coding
bash checks/check-mapping.sh          # ⟦CI⟧·⟦훅⟧ 정합 (green 이어야)
grep -cE '^[0-9]+\. ' coding.md       # 룰 요약 = MUST 예산 (≤7)
bash tests/inventory-gate.test.sh     # 인벤토리 게이트 계약 테스트 (21건)
```

게이트가 어떤 파일을 막을지 미리 보려면 훅을 직접 호출한다(설정 무수정, 판정만):

```bash
printf '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"file_path":"'"$PWD/src/foo/bar.py"'"},"cwd":"'"$PWD"'","session_id":"probe"}' \
  | python3 docs/claude_guideline/coding/hooks/coding-inventory-gate.py; echo "exit=$?"
```

## 변경 절차

- SSOT 는 본 번들 폴더. 규칙 변경은 사용자 승인 후 4 코어 + `checks/`·`hooks/` 를 **단일 번들 VERSION 으로 동반 갱신**(부분 드리프트 금지).
- `⟦CI:<id>⟧` 태그 추가/변경 시 `checks/<id>.sh` + `check-mapping.sh` 동반. semver + 각 파일 말미 `VERSION`.
- `⟦훅:<id>⟧` 태그 추가/변경 시 `hooks/coding-<id>.py` + `install.sh` 이벤트 등록 + `tests/` 계약 테스트 동반. **훅은 사용자 작업을 차단하므로 테스트 없이 출하 금지.**

## 파일

`coding.md`(코어) · `conventions.md` · `stack.md` · `domains/*.md`(5) · `checks/*.sh`(8) · `hooks/*.py`(2) · `tests/*.sh`(1) · `install.sh` · `claude.snippet.md` · `.pre-commit-config.yaml` · `ci/coding-gates.yml`
