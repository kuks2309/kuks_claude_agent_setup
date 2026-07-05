# [computer_use HIL] chrome-navigate — 크롬 실행 후 example.com 이동

> HIL = 실제 데스크톱에서 마우스·키보드가 실제로 움직인 end-to-end 검증.
> **판정: PASS** · **반영 일자**: 2026-07-05 · 번들 commit: `fc6938f` 기준.

## 목적

computer-use 루프(read→analyze→act→re-read) 전체를 실제 화면에서 검증한다.
SIL(마우스 미동작)로는 잡히지 않는 좌표 정확도·창 포커스·실입력 반영 확인.

## 환경

- OS / 세션: Ubuntu Linux, X11 (`DISPLAY=:0`, `XDG_SESSION_TYPE=x11`)
- 브라우저: `google-chrome`
- 입력 백엔드: `xdotool`
- 대상 창: 새 크롬 창(`about:blank`, id `0x3800004`, geometry x=70 y=27 w=1850 h=1053)

## 실행 절차 (실제 수행)

1. `google-chrome --new-window about:blank` 실행, `xdotool search --sync` 로 창 대기.
2. `capture_screen.py --mode window` 로 크롬 창 캡처(가려진 창을 앞으로 올림).
3. 캡처 이미지에서 주소창 위치 산출: 창(70,27) + 이미지 내 (700,62) → **절대 (770,89)**.
4. `computer_action.py`:
   - `click --x 770 --y 89` (주소창 클릭)
   - `key --keys ctrl+a` (기존 텍스트 전체선택)
   - `type --text example.com`
   - `key --keys Return`
   - `wait --duration 2.5` (로드 대기)
5. `capture_screen.py --mode window` 재캡처로 확인.

## 결과

| 항목 | 관찰 | 기대 | 판정 |
|------|------|------|------|
| 클릭 포커스 | 주소창 활성 | 주소창 포커스 | ✅ |
| 타이핑 반영 | 주소창 `example.com` | 입력됨 | ✅ |
| 엔터 이동 | 탭 제목 `Example Domain - Google Chrome`, 본문 "Example Domain" 렌더 | 이동 | ✅ |
| 좌표 정확도 | (770,89) 주소창 명중 | 의도 위치 | ✅ |
| 재확인 루프 | 재캡처로 이동 확인·보고 | 검증 | ✅ |

각 action 실행은 `{"ok":true,...}` 반환.

## 발견 (HIL 이 잡은 것, SIL 로는 불가)

1. **z-order/포커스** — 크롬을 실행·`windowactivate` 했는데도 상위에 다른 창(VS
   Code)이 덮어 크롬이 화면에 보이지 않았다. WM 포커스는 크롬이었으나 시각적
   z-order 는 아니었음. → 창 모드 캡처(캡처 전 대상 창 raise)로 강제로 앞에
   올려 해결. 전체화면 캡처만 믿고 좌표 산출/타이핑하면 엉뚱한 창에 입력될
   위험. **교훈**: 조작 전 대상 창을 명시적으로 raise + 재캡처로 시각 확인.
2. **`~/.claude` 미설치** — 스킬은 `~/.claude/computer_action.py` 를 참조하는데
   첫 시도 시 실제 설치를 안 해(격리 테스트만) "파일 없음"으로 전량 실패. 번들
   경로 우회로 성공 후, `install.sh` 로 실제 설치하여 정상 경로 복구.
   **교훈**: 스킬 사용 전 `install.sh` 실행 필요(전역 경로 존재 보장).

## 정리

- 실입력 실행기(xdotool 백엔드)·캡처·좌표 산출·재확인 루프가 실제 데스크톱에서
  end-to-end 동작함을 확인(PASS).
- 캡처 산출물(참고): `20260705_141432_chrome_win.png`(조작 전),
  `20260705_141613_chrome_after2.png`(조작 후, example.com). (임시 경로, 미커밋)
- 후속: 좌표 자동 산출(주소창 검출) 보조, 다중 모니터, Windows(pyautogui) HIL.
