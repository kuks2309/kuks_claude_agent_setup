# computer_use — 단위 검증 (SIL / HIL)

> 본 번들의 **L1 함수 단위 + L2 단일 프로그램** 검증(SIL) 및 **실기 조작**
> 검증(HIL)을 기록한다. 검증 모델·배치 규칙은 상위 저장소 규약을 따른다.

## 검증 대상 코드

| 파일 | 종류 | 검증 초점 |
|------|------|-----------|
| `computer_action.py` | 입력 실행기 (Python) | action 계획 생성(xdotool/pyautogui) · 백엔드 감지 · dry-run · 오류 경로 |
| `capture_screen.py` | 화면 캡처 (Python) | 창 목록/active/window/full/region 캡처 |
| `install.sh` | 설치 프로그램 | `~/.claude` 배치 · CLAUDE.md marker 멱등 |

## L1 함수 단위 + L2 단일 프로그램 (SIL) — 마우스 미동작

`experiments/SIL/test_computer_action.py` (pytest):
- `detect_backend()` — linux/windows 반환, Wayland·DISPLAY 미설정 거부.
- `plan_action()` — 각 action × 백엔드의 명령/호출 계획이 정확한지.
- `main()` — `--dry-run` 계획 출력, 실행 분기, 오류 시 exit 2.

실행: `cd computer_use && python3 -m pytest experiments/SIL -q`

## HIL — 실제 화면 조작

실제 데스크톱에서 마우스·키보드가 움직이는 end-to-end 검증(예: 메모장 열어
`hello` 입력 → 재캡처로 확인). `SIL/` 로는 잡히지 않는 좌표 정확도·타깃 창
포커스·실입력 반영을 확인한다. `HIL/_template/` 참조.

## 기록

`SIL/_template/` · `HIL/_template/` 를 `YYYY-MM-DD_<topic>/` 로 복사해 채운다.
