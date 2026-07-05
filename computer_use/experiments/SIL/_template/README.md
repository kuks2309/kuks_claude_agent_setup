# [computer_use 단위 SIL 템플릿] `<topic>`

> `_template/` → `YYYY-MM-DD_<topic>/` 복사 후 작성. SIL = 격리 샌드박스, 실제
> 마우스·키보드 미동작. 명령 생성/백엔드 감지/오류 경로만 검증한다.

## 목적 / 레벨

- 레벨: L1 함수 단위(`plan_action`/`detect_backend`) / L2 단일 프로그램(`main`) (택1 명시)
- 대상: `computer_action.py`
- **수행 프로젝트 / commit**: `<repo>@<hash>` · **반영 일자**: `YYYY-MM-DD`

## 실행 절차

```bash
cd computer_use
python3 -m pytest experiments/SIL -q
# 또는 단일 확인(마우스 미동작):
DISPLAY=:0 python3 computer_action.py click --x 100 --y 200 --dry-run
```

## 결과

| 케이스 | 입력 | 측정 출력/exit | 기대 | 판정 |
|--------|------|----------------|------|------|
| click 계획 | `click --x 10 --y 20` | — | `mousemove 10 20 click 1` | ⏳ |
| Wayland 거부 | `WAYLAND_DISPLAY=…` | — | `ok:false`, exit 2 | ⏳ |
| 인자 누락 | `type`(--text 없음) | — | `ok:false`, exit 2 | ⏳ |
| 전체 스위트 | `pytest experiments/SIL` | — | all passed | ⏳ |

## 분석 / 결론

(신규 action 추가 시 회귀, 백엔드별 차이)
