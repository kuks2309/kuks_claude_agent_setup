#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIL — drawio_capture.sh 의 인자 파싱·preflight 분기. 디스플레이 불필요.

창을 실제로 띄우는 경로는 HIL 소관이고, 여기서는 그 앞단(잘못된 인자·의존성
누락·모드별 요구사항)이 올바로 갈라지는지만 본다. CLAUDE_HOME 을 스텁 디렉터리로
바꿔 computer_use 설치 유무를 흉내낸다(computer_use·hwpx 와 같은 테스트 규약).
"""
import os
import subprocess

import pytest

BUNDLE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(BUNDLE, "checks", "drawio_capture.sh")
GOOD = os.path.join(BUNDLE, "checks", "good.example.drawio")


def run(args, env_extra=None, drop=()):
    env = dict(os.environ)
    env.update(env_extra or {})
    for k in drop:
        env.pop(k, None)
    return subprocess.run(["bash", SCRIPT, *args],
                          capture_output=True, text=True, env=env, timeout=60)


def stub_claude_home(tmp_path, with_tools=True):
    """capture_screen.py·computer_action.py 유무를 흉내내는 CLAUDE_HOME."""
    home = tmp_path / "claude"
    home.mkdir()
    if with_tools:
        for n in ("capture_screen.py", "computer_action.py"):
            (home / n).write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return str(home)


# ── 인자 파싱 ─────────────────────────────────────────────────────────

def test_unknown_flag_exits_64():
    r = run(["--nope"])
    assert r.returncode == 64
    assert "unknown arg" in r.stderr


def test_missing_file_argument_exits_1():
    r = run([])
    assert r.returncode == 1
    assert "사용법" in r.stderr


def test_nonexistent_file_exits_1():
    r = run(["/nonexistent/nope.drawio"])
    assert r.returncode == 1
    assert "파일 없음" in r.stderr


# ── preflight: --export 모드 ──────────────────────────────────────────

def test_export_preflight_passes_without_display(tmp_path):
    """--export 는 xvfb 로 돌므로 DISPLAY 도 computer_use 도 필요 없다."""
    r = run(["--check", "--export"],
            env_extra={"CLAUDE_HOME": stub_claude_home(tmp_path, with_tools=False)},
            drop=("DISPLAY", "WAYLAND_DISPLAY"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "xvfb-run" in r.stdout


def test_export_preflight_does_not_require_computer_use(tmp_path):
    r = run(["--check", "--export"],
            env_extra={"CLAUDE_HOME": stub_claude_home(tmp_path, with_tools=False)})
    assert "capture_screen.py 없음" not in r.stderr


# ── preflight: GUI 모드 ───────────────────────────────────────────────

def test_gui_preflight_fails_without_display(tmp_path):
    r = run(["--check"],
            env_extra={"CLAUDE_HOME": stub_claude_home(tmp_path)},
            drop=("DISPLAY", "WAYLAND_DISPLAY"))
    assert r.returncode != 0
    assert "디스플레이 없음" in r.stderr
    assert "--export" in r.stderr        # 대안을 반드시 제시한다


def test_gui_preflight_fails_without_computer_use(tmp_path):
    r = run(["--check"],
            env_extra={"CLAUDE_HOME": stub_claude_home(tmp_path, with_tools=False)})
    assert r.returncode != 0
    assert "computer_use" in r.stderr


def test_gui_preflight_passes_with_everything(tmp_path):
    if not os.environ.get("DISPLAY"):
        pytest.skip("DISPLAY 없음 — GUI preflight 통과 경로는 검증 불가")
    r = run(["--check"], env_extra={"CLAUDE_HOME": stub_claude_home(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr


# ── drawio 미설치 안내 ────────────────────────────────────────────────

def test_missing_drawio_points_at_setup_env(tmp_path):
    """안내는 setup_env.sh 를 가리켜야 한다 — 수동 curl 지시를 다시 넣지 않는다."""
    empty = tmp_path / "home"
    empty.mkdir()
    r = run(["--check"], env_extra={"HOME": str(empty), "PATH": "/usr/bin:/bin",
                                    "CLAUDE_HOME": stub_claude_home(tmp_path)})
    assert "drawio 데스크톱을 찾을 수 없습니다" in r.stderr
    assert "setup_env.sh" in r.stderr


# ── 회귀 고정: 폐기된 것이 되살아나지 않도록 ─────────────────────────

def code_only():
    """주석을 제외한 실행 코드. 폐기 사유를 적은 주석까지 잡으면 오탐이 난다."""
    out = []
    for line in open(SCRIPT, encoding="utf-8"):
        s = line.split("#", 1)[0]
        if s.strip():
            out.append(s)
    return "\n".join(out)


def test_hide_panel_flag_stays_removed():
    """Ctrl+Shift+P 는 WM 이 가로채 창 개요를 띄운다 — 되살리지 않는다."""
    src = code_only()
    assert "--hide-panel" not in src
    assert "ctrl+shift+p" not in src.lower()


def test_capture_uses_window_mode_not_region():
    """capture_screen.py --mode window 가 스스로 창을 올린다 — region 우회 금지."""
    src = code_only()
    assert "--mode window" in src
    assert "--mode region" not in src


def test_window_picking_is_delegated_to_testable_module():
    """선택 로직을 셸에 인라인으로 되돌리면 SIL 이 다시 무력해진다."""
    src = code_only()
    assert "drawio_pick_window.py" in src


# ── ⟦CI:drawio-lint⟧ 이빨 ─────────────────────────────────────────────

TOOTH = os.path.join(BUNDLE, "checks", "drawio-lint.sh")
BAD = os.path.join(BUNDLE, "checks", "bad-L4-diagonal.example.drawio")


def tooth(args, cwd=None):
    return subprocess.run(["bash", TOOTH, *args], capture_output=True,
                          text=True, cwd=cwd, timeout=60)


def test_tooth_passes_clean_file():
    assert tooth([GOOD]).returncode == 0


def test_tooth_skips_intentional_violation_fixtures():
    """bad-L* 는 린트를 증명하는 fixture 다. 검사하면 번들 저장소가 커밋 불가가 된다."""
    assert tooth([BAD]).returncode == 0


def test_tooth_blocks_a_real_defect(tmp_path):
    """fixture 이름만 아니면 같은 내용도 정상 차단된다 — 제외가 과하지 않다."""
    d = tmp_path / "flow.drawio"
    d.write_text(open(BAD, encoding="utf-8").read(), encoding="utf-8")
    r = tooth([str(d)])
    assert r.returncode == 1
    assert "커밋 차단" in r.stderr


def test_tooth_passes_when_nothing_to_check(tmp_path):
    r = tooth([str(tmp_path)])
    assert r.returncode == 0
    assert "없음" in r.stdout


def test_tooth_rejects_unknown_flag():
    assert tooth(["--nope"]).returncode == 2


def test_tooth_all_mode_is_clean_in_this_repo():
    """저장소가 배포하는 예제는 항상 무결점이어야 한다 — 이빨이 그것을 고정한다."""
    repo = os.path.dirname(BUNDLE)
    assert tooth(["--all"], cwd=repo).returncode == 0
