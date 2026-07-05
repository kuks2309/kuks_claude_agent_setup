# computer_use — PC 화면 읽기·분석·조작 (SSOT)

PC 화면을 캡처해 분석하고, 실제 마우스·키보드로 조작하는 Claude Code 자산의
단일 근원(SSOT). 읽기 절반(`capture-test`)과 쓰기 절반(`computer-use`)을 한
번들로 묶어 전역(`~/.claude`) 설치한다.

## 구성

| 파일 | 역할 |
|------|------|
| `capture_screen.py` | 화면 읽기 — 창 목록/active/window/full/region 캡처 (Linux X11 / Windows) |
| `computer_action.py` | 화면 쓰기 — 마우스·키보드 입력 실행기 (Linux=xdotool / Windows=pyautogui) |
| `skills/capture-test/SKILL.md` | 캡처·분석 스킬(읽기 전용) |
| `skills/computer-use/SKILL.md` | read→analyze→act→re-read 오케스트레이터(쓰기) |
| `agents/computer-operator.md` | 화면 조작 전문 에이전트 |
| `install.sh` / `install.ps1` | 전역 설치 + preflight |
| `experiments/` | SIL(단위) / HIL(실기) 검증 기록 |
| `app/` | 2단계 독립 앱 stub |

## action 어휘 (Anthropic computer_use 도구와 일치)

`move click double_click right_click middle_click triple_click drag type key
scroll wait`. 각 실행은 결과 JSON 한 줄 출력(`{"ok":true|false,...}`).

```bash
python3 ~/.claude/computer_action.py click --x 840 --y 410
python3 ~/.claude/computer_action.py type  --text "hello"
python3 ~/.claude/computer_action.py key   --keys ctrl+s
python3 ~/.claude/computer_action.py <action> ... --dry-run   # 실행 없이 계획만 출력
```

## 안전 모델 (입력 후 피드백)

사전 차단이 아니라 **사후 피드백**으로 안전을 확보한다: action 실행 → 즉시
재캡처 → 결과 보고 → 사용자 피드백(계속/수정/중지). 기본 매 스텝, `autorun N`
이면 N 스텝 연속 후 보고. 사용자가 부를 때만 동작하며 백그라운드 감시는 없다.

## 좌표

전체화면 네이티브 캡처를 기본으로 하여 캡처 이미지의 픽셀 좌표를 화면 절대
좌표로 사용한다(1:1). 창 모드는 창 offset 을 더해 변환.

## 플랫폼

- Linux X11: `xdotool` + `x11-utils`. **Wayland 미지원**(감지 시 거부).
- Windows: `pyautogui`.

## 설치 / 제거

```bash
# Linux/macOS
cd computer_use && ./install.sh            # 배치+의존성+preflight
./install.sh --check                       # preflight 만
CLAUDE_HOME=/tmp/x ./install.sh --no-deps  # 테스트(격리 설치)

# Windows
./install.ps1                              # 또는 ./install.ps1 -Check / -NoDeps
```

설치 위치: `~/.claude/{capture_screen.py, computer_action.py,
skills/capture-test, skills/computer-use, agents/computer-operator.md}` +
`~/.claude/CLAUDE.md` 등록. 전역 설치이므로 어느 프로젝트에서든 동작.

제거:
```bash
rm -f  ~/.claude/capture_screen.py ~/.claude/computer_action.py
rm -rf ~/.claude/skills/capture-test ~/.claude/skills/computer-use
rm -f  ~/.claude/agents/computer-operator.md
# ~/.claude/CLAUDE.md 의 <!-- kuks_agent_setup:computer_use --> 줄 수동 삭제
```

## 검증

- SIL(단위, 마우스 미동작): `cd computer_use && python3 -m pytest experiments/SIL -q`
- HIL(실기, 실제 조작): `experiments/HIL/_template/` 참조.
