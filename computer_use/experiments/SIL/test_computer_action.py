"""SIL 단위 테스트 — computer_action.py.

마우스/키보드를 실제로 움직이지 않고 (1) 백엔드 감지, (2) action 계획(Linux/
Windows 명령 생성), (3) CLI dry-run/오류 경로만 검증한다. 실제 입력 검증은
HIL(experiments/HIL) 소관.

실행: cd computer_use && python3 -m pytest experiments/SIL -v
"""
import json

import pytest

import computer_action
from computer_action import ActionError, detect_backend, plan_action, main


# --- 1) 백엔드 감지 ---------------------------------------------------------

def test_linux_x11():
    assert detect_backend("linux", {"DISPLAY": ":0"}) == "linux"


def test_windows():
    assert detect_backend("win32", {}) == "windows"


def test_wayland_rejected():
    with pytest.raises(ActionError):
        detect_backend("linux", {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"})


def test_linux_no_display_rejected():
    with pytest.raises(ActionError):
        detect_backend("linux", {})


def test_unsupported_platform_rejected():
    with pytest.raises(ActionError):
        detect_backend("darwin", {})


# --- 2) Linux(xdotool) action 계획 ------------------------------------------

def L(action, **args):
    return plan_action(action, args, "linux")["ops"]


def test_linux_move():
    assert L("move", x=10, y=20) == [{"run": ["xdotool", "mousemove", "10", "20"]}]


def test_linux_click():
    assert L("click", x=5, y=6) == [
        {"run": ["xdotool", "mousemove", "5", "6", "click", "1"]}
    ]


def test_linux_double_click():
    assert L("double_click", x=1, y=2) == [
        {"run": ["xdotool", "mousemove", "1", "2", "click", "--repeat", "2", "1"]}
    ]


def test_linux_right_click():
    assert L("right_click", x=1, y=2) == [
        {"run": ["xdotool", "mousemove", "1", "2", "click", "3"]}
    ]


def test_linux_middle_click():
    assert L("middle_click", x=1, y=2) == [
        {"run": ["xdotool", "mousemove", "1", "2", "click", "2"]}
    ]


def test_linux_triple_click():
    assert L("triple_click", x=1, y=2) == [
        {"run": ["xdotool", "mousemove", "1", "2", "click", "--repeat", "3", "1"]}
    ]


def test_linux_drag():
    assert L("drag", x=1, y=2, to_x=3, to_y=4) == [
        {"run": ["xdotool", "mousemove", "1", "2", "mousedown", "1",
                 "mousemove", "3", "4", "mouseup", "1"]}
    ]


def test_linux_type():
    assert L("type", text="hi") == [
        {"run": ["xdotool", "type", "--clearmodifiers", "--", "hi"]}
    ]


def test_linux_key():
    assert L("key", keys="ctrl+c") == [{"run": ["xdotool", "key", "ctrl+c"]}]


def test_linux_scroll_down():
    assert L("scroll", x=1, y=2, direction="down", amount=3) == [
        {"run": ["xdotool", "mousemove", "1", "2", "click", "--repeat", "3", "5"]}
    ]


def test_linux_scroll_up():
    assert L("scroll", x=1, y=2, direction="up", amount=2) == [
        {"run": ["xdotool", "mousemove", "1", "2", "click", "--repeat", "2", "4"]}
    ]


def test_linux_wait():
    assert L("wait", duration=0.5) == [{"sleep": 0.5}]


def test_linux_click_requires_xy():
    with pytest.raises(ActionError):
        plan_action("click", {}, "linux")


def test_linux_drag_requires_to_xy():
    with pytest.raises(ActionError):
        plan_action("drag", {"x": 1, "y": 2}, "linux")


def test_linux_unknown_action():
    with pytest.raises(ActionError):
        plan_action("teleport", {"x": 1, "y": 2}, "linux")


# --- 3) Windows(pyautogui) action 계획 --------------------------------------

def W(action, **args):
    return plan_action(action, args, "windows")["ops"]


def test_win_move():
    assert W("move", x=10, y=20) == [{"call": "moveTo", "args": [10, 20]}]


def test_win_click():
    assert W("click", x=5, y=6) == [{"call": "click", "args": [5, 6]}]


def test_win_double_click():
    assert W("double_click", x=1, y=2) == [{"call": "doubleClick", "args": [1, 2]}]


def test_win_right_click():
    assert W("right_click", x=1, y=2) == [{"call": "rightClick", "args": [1, 2]}]


def test_win_middle_click():
    assert W("middle_click", x=1, y=2) == [{"call": "middleClick", "args": [1, 2]}]


def test_win_triple_click():
    assert W("triple_click", x=1, y=2) == [{"call": "tripleClick", "args": [1, 2]}]


def test_win_drag():
    assert W("drag", x=1, y=2, to_x=3, to_y=4) == [
        {"call": "moveTo", "args": [1, 2]},
        {"call": "dragTo", "args": [3, 4]},
    ]


def test_win_type():
    assert W("type", text="hi") == [{"call": "write", "args": ["hi"]}]


def test_win_key():
    assert W("key", keys="ctrl+c") == [{"call": "hotkey", "args": ["ctrl", "c"]}]


def test_win_scroll_down():
    assert W("scroll", x=1, y=2, direction="down", amount=3) == [
        {"call": "moveTo", "args": [1, 2]},
        {"call": "scroll", "args": [-3]},
    ]


def test_win_scroll_up():
    assert W("scroll", x=1, y=2, direction="up", amount=2) == [
        {"call": "moveTo", "args": [1, 2]},
        {"call": "scroll", "args": [2]},
    ]


def test_win_wait():
    assert W("wait", duration=0.5) == [{"sleep": 0.5}]


def test_unknown_backend():
    with pytest.raises(ActionError):
        plan_action("move", {"x": 1, "y": 2}, "macos")


# --- 4) CLI main() / dry-run / 오류 경로 ------------------------------------

def test_main_dry_run_outputs_plan(capsys, monkeypatch):
    monkeypatch.setattr(computer_action, "detect_backend", lambda: "linux")
    rc = main(["click", "--x", "10", "--y", "20", "--dry-run"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["ok"] is True and out["dry_run"] is True
    assert out["ops"] == [{"run": ["xdotool", "mousemove", "10", "20", "click", "1"]}]


def test_main_dry_run_does_not_execute(monkeypatch):
    monkeypatch.setattr(computer_action, "detect_backend", lambda: "linux")
    called = []
    monkeypatch.setattr(computer_action, "execute", lambda plan: called.append(plan))
    main(["move", "--x", "1", "--y", "2", "--dry-run"])
    assert called == []


def test_main_executes_when_not_dry_run(capsys, monkeypatch):
    monkeypatch.setattr(computer_action, "detect_backend", lambda: "linux")
    called = []
    monkeypatch.setattr(computer_action, "execute", lambda plan: called.append(plan))
    rc = main(["move", "--x", "1", "--y", "2"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["ok"] is True and out["action"] == "move"
    assert len(called) == 1


def test_main_action_error_returns_2(capsys, monkeypatch):
    monkeypatch.setattr(computer_action, "detect_backend", lambda: "linux")
    rc = main(["click", "--dry-run"])  # --x/--y 누락
    out = json.loads(capsys.readouterr().out)
    assert rc == 2 and out["ok"] is False and "error" in out


def test_execute_runs_subprocess(monkeypatch):
    calls = []
    monkeypatch.setattr(computer_action.subprocess, "run",
                        lambda cmd, check: calls.append((cmd, check)))
    computer_action.execute({"backend": "linux", "action": "move",
                             "ops": [{"run": ["xdotool", "mousemove", "1", "2"]}]})
    assert calls == [(["xdotool", "mousemove", "1", "2"], True)]
