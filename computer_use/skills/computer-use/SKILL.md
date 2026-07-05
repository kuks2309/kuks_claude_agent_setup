---
name: computer-use
description: PC 화면을 읽고 분석해 실제 마우스·키보드로 조작하는 스킬. 화면 캡처 후 Claude 가 다음 동작을 결정하고 클릭/타이핑/스크롤을 실행한 뒤 재캡처로 결과를 확인하는 read→analyze→act→re-read 루프. "화면 조작", "대신 클릭", "자동 입력", "GUI 자동화", "computer use" 요청 시 사용. 사용자가 부를 때만 동작(on-demand).
user_invocable: true
trigger: computer-use
arguments:
  - name: goal
    description: 달성할 목표 (예 "메모장 열어 hello 입력")
    required: false
  - name: autorun
    description: 피드백 없이 연속 실행할 스텝 수 (기본 1 = 매 스텝 피드백)
    required: false
---

# Computer Use — 화면 읽기·분석·조작 루프

읽기 전용 `capture-test` 를 확장하여 분석 결과를 실제 입력으로 연결한다.
읽기 = `~/.claude/capture_screen.py`, 쓰기 = `~/.claude/computer_action.py`.
사용자가 호출할 때만 동작하며, 백그라운드로 화면을 감시하지 않는다.

## 안전 원칙 (입력 후 피드백)

마우스·키보드를 실제로 조작하므로 잘못된 동작은 되돌리기 어렵다. 그래서 이
스킬은 **사전 차단이 아니라 사후 피드백**으로 안전을 확보한다: action 을 실행한
뒤 즉시 재캡처해 결과를 사용자에게 보고하고, 사용자가 계속/수정/중지를
선택한다. 기본은 매 스텝 보고, `autorun N` 이면 N 스텝 연속 후 보고한다.

## 워크플로

### Step 1: 목표 확인
`goal` 인자가 있으면 그대로, 없으면 사용자에게 무엇을 시킬지 묻는다.

### Step 2: 대상 창 준비 + 화면 읽기 (캡처)
**먼저 조작할 대상 앱 창을 앞으로 올린다(raise/activate).** 상위에 다른 창이
덮여 있으면(z-order) 이후 클릭·타이핑이 **엉뚱한 창에 들어갈 수 있다**. 대상
창을 `--mode window` 로 캡처하면 캡처 전 그 창을 자동으로 앞으로 올린다(창 id
는 `--mode list` 로 확인).

```bash
# 대상 창을 앞으로 올리며 캡처 (권장)
python3 ~/.claude/capture_screen.py --mode list                      # 창 id 확인
python3 ~/.claude/capture_screen.py --mode window --window-id 0x... --label "cu_step"
# 또는 전체 화면 (대상 창이 이미 최상위·포커스임이 확실할 때)
python3 ~/.claude/capture_screen.py --mode full --label "cu_step"
```

좌표는 화면 절대 좌표(전체화면 1:1; 창 모드는 창 offset 을 더함). 포커스를
명시적으로 주려면 `xdotool windowactivate <id>`. 조작 후 Step 5 재캡처의 화면
변화로 대상 창이 맞았는지 반드시 재확인한다.

### Step 3: 분석 + 다음 action 결정
Read 도구로 캡처 이미지를 읽고 목표 대비 현재 화면을 분석한다. 다음 한
동작을 결정하고, **실행 전에** "무엇을, 어디(좌표)에, 왜" 를 텍스트로 명시한다.

### Step 4: action 실행
결정한 동작을 `computer_action.py` 로 실행한다. 먼저 `--dry-run` 으로 계획을
확인한 뒤 같은 명령을 `--dry-run` 없이 실행한다.

```bash
python3 ~/.claude/computer_action.py click --x 840 --y 410
python3 ~/.claude/computer_action.py type --text "hello"
python3 ~/.claude/computer_action.py key --keys ctrl+s
python3 ~/.claude/computer_action.py scroll --x 960 --y 540 --direction down --amount 3
```

사용 가능한 action: `move click double_click right_click middle_click
triple_click drag type key scroll wait`. 각 호출은 결과 JSON 한 줄을 출력한다
(`{"ok":true,...}` / `{"ok":false,"error":...}`).

### Step 5: 재캡처 + 결과 보고
Step 2 와 동일하게 재캡처하고 Read 로 비교한다. "실행한 동작 / 화면 변화 /
목표 진척" 을 보고한다.

### Step 6: 피드백 또는 반복
기본은 사용자 피드백(계속/수정/중지)을 받고 Step 3 으로 돌아간다. `autorun N`
이면 피드백 없이 N 스텝까지 Step 3-5 를 반복한 뒤 보고한다.

## 정지 조건
- 목표 달성
- 사용자 중지
- 동일 화면이 N회(기본 3) 연속 = 무진전 → 자동 정지 후 원인 보고
- 최대 스텝(기본 20) 초과

## 좌표 가이드
캡처 이미지에서 대상의 픽셀 위치를 그대로 좌표로 쓴다(전체화면 1:1). 클릭이
빗나가면 재캡처에서 미변화를 감지해 좌표를 재추론한 뒤 보정한다.

## 환경 요구
- Linux(X11): `xdotool`, `x11-utils` 필요. Wayland 미지원.
- Windows: `pyautogui` 필요.
- 설치: 번들의 `install.sh`(Linux/macOS) 또는 `install.ps1`(Windows). 전역
  `~/.claude` 설치이므로 어느 프로젝트에서든 사용 가능.
- **사용 전 install.sh 선행 필요** — 스킬은 `~/.claude/computer_action.py`·
  `~/.claude/capture_screen.py` 를 참조하므로 미설치 시 "파일 없음"으로 실패한다.
