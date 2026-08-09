#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIL — 캡처할 drawio 창 선택 로직. 디스플레이 불필요.

여기 담긴 케이스는 전부 HIL 에서 실제로 겪은 실패다. 셸 안에 인라인으로 두었을
때는 검증할 방법이 없어 같은 버그를 세 번 고쳤다.

실행: cd drawio && python3 -m pytest experiments/SIL/ -v
"""
import json
import os
import subprocess
import sys

import pytest

BUNDLE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKS = os.path.join(BUNDLE, "checks")
sys.path.insert(0, CHECKS)

import drawio_pick_window as P  # noqa: E402

STEM = "session-lifecycle"


def win(wid, title, x=395, y=153, w=1200, h=800):
    return {"id": wid, "title": title, "x": x, "y": y, "w": w, "h": h}


DOC = win("0x100", f"{STEM}.drawio - draw.io")
SPLASH = win("0x101", "Flowchart Maker & Online Diagram Software", x=0, y=0)
EDITOR = win("0x200", "Drawio 다이어그램 품질 피드백 개선 - claude_code - Visual Studio Code",
             x=70, y=27, w=1850, h=1053)
TERMINAL = win("0x201", "tc@tc: ~", x=150, y=160, w=700, h=500)


# ── 실행 전후 차분 ────────────────────────────────────────────────────

def test_pre_existing_editor_with_drawio_in_title_is_not_picked():
    """편집기 창 제목에 'Drawio' 가 들어 있어도 기존 창이면 후보가 아니다.

    HIL 1회차: 세션 이름이 'Drawio 다이어그램…' 이라 VS Code 창이 캡처됐다.
    """
    got = P.pick([EDITOR, TERMINAL, DOC], STEM, before_ids=["0x200", "0x201"])
    assert got is not None and got["id"] == DOC["id"]


def test_all_windows_pre_existing_gives_none():
    assert P.pick([EDITOR, DOC], STEM, before_ids=["0x200", "0x100"]) is None


# ── 스플래시 창 레이스 ────────────────────────────────────────────────

def test_splash_is_rejected_while_document_window_not_yet_up():
    """스플래시만 떠 있는 순간에는 아무것도 고르지 않고 더 기다려야 한다.

    HIL 2회차: 스플래시(좌표 0,0)를 물어 화면 원점이 찍혔다.
    """
    assert P.pick([SPLASH], STEM, before_ids=[]) is None


def test_document_window_wins_over_splash_when_both_present():
    got = P.pick([SPLASH, DOC], STEM, before_ids=[])
    assert got is not None and got["id"] == DOC["id"]


def test_unplaced_window_rejected_even_in_relaxed_mode():
    """relaxed 로 내려가도 (0,0) 창은 찍어봐야 화면 원점이다."""
    assert P.pick([SPLASH], STEM, before_ids=[], mode="relaxed") is None


# ── strict / relaxed ──────────────────────────────────────────────────

def test_strict_rejects_untitled_window_but_relaxed_accepts():
    generic = win("0x300", "무제 창", x=400, y=200)
    assert P.pick([generic], STEM, before_ids=[], mode="strict") is None
    got = P.pick([generic], STEM, before_ids=[], mode="relaxed")
    assert got is not None and got["id"] == "0x300"


def test_title_still_untitled_diagram_is_accepted_by_suffix():
    """로딩 중 제목은 'Untitled Diagram - draw.io' 다 — 접미사로 인정한다."""
    loading = win("0x400", "Untitled Diagram - draw.io")
    got = P.pick([loading], STEM, before_ids=[])
    assert got is not None and got["id"] == "0x400"


# ── 다중 인스턴스 ─────────────────────────────────────────────────────

def test_largest_document_window_wins_with_multiple_instances():
    small = win("0x500", f"{STEM}.drawio - draw.io", w=800, h=600)
    large = win("0x501", f"{STEM}.drawio - draw.io", w=1400, h=900)
    got = P.pick([small, large], STEM, before_ids=[])
    assert got["id"] == "0x501"


# ── 크기 하한 ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("w,h", [(399, 800), (1200, 299), (100, 100)])
def test_tiny_windows_are_ignored(w, h):
    tiny = win("0x600", f"{STEM}.drawio - draw.io", w=w, h=h)
    assert P.pick([tiny], STEM, before_ids=[]) is None


def test_empty_window_list_gives_none():
    assert P.pick([], STEM, before_ids=[]) is None


# ── 출력 형식 (셸이 cut -f 로 자른다) ─────────────────────────────────

def test_row_format_is_tab_separated_in_field_order():
    row = P.format_row(DOC)
    f = row.split("\t")
    assert f == [DOC["id"], "395", "153", "1200", "800", DOC["title"]]


# ── CLI (셸이 실제로 호출하는 경로) ───────────────────────────────────

def _cli(windows, stem, mode, before):
    return subprocess.run(
        [sys.executable, os.path.join(CHECKS, "drawio_pick_window.py"),
         "--stdin", stem, mode, *before],
        input=json.dumps(windows), capture_output=True, text=True)


def test_cli_prints_row_and_exits_zero():
    r = _cli([EDITOR, DOC], STEM, "strict", ["0x200"])
    assert r.returncode == 0
    assert r.stdout.strip().split("\t")[0] == DOC["id"]


def test_cli_exits_one_when_nothing_matches():
    r = _cli([SPLASH], STEM, "strict", [])
    assert r.returncode == 1
    assert r.stdout.strip() == ""


def test_cli_survives_malformed_input():
    r = subprocess.run(
        [sys.executable, os.path.join(CHECKS, "drawio_pick_window.py"),
         "--stdin", STEM, "strict"],
        input="not json", capture_output=True, text=True)
    assert r.returncode == 1
