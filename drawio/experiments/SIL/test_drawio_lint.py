#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIL — drawio_lint.py 가 각 규칙을 해당 fixture 에서만 적발하는지 검증.

실행: cd drawio && python3 -m pytest experiments/SIL/ -v
"""
import os
import re
import sys

import pytest

BUNDLE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKS = os.path.join(BUNDLE, "checks")
sys.path.insert(0, CHECKS)

import drawio_lint as L  # noqa: E402

ERR, WARN = L.ERR, L.WARN


def lint(name):
    return L.lint_file(os.path.join(CHECKS, name))


def rules(problems, level=None):
    return {r for r, lv, _ in problems if level is None or lv == level}


# ── good fixture: 전 규칙 무결점 ──────────────────────────────────────

def test_good_example_has_zero_problems():
    problems, nv, ne = lint("good.example.drawio")
    assert problems == [], f"good fixture 에서 적발됨: {problems}"
    assert (nv, ne) == (5, 4)


# ── 규칙별 fixture: 의도한 규칙만 발화 ────────────────────────────────

@pytest.mark.parametrize("fixture,expected_err,expected_warn", [
    ("bad-L4-diagonal.example.drawio",      {"L4"}, {"L4"}),
    ("bad-L5-overflow.example.drawio",      {"L5"}, set()),
    ("bad-L6-overlap.example.drawio",       {"L6"}, {"L6"}),
    ("bad-L7-through.example.drawio",       set(),  {"L7"}),
    ("bad-L8-jog.example.drawio",           set(),  {"L8"}),
    ("bad-L9-stacked-edges.example.drawio", {"L9"}, {"L10"}),
    ("bad-L11-eaten-text.example.drawio",   {"L11"}, set()),
])
def test_fixture_triggers_only_its_rule(fixture, expected_err, expected_warn):
    problems, _, _ = lint(fixture)
    assert rules(problems, ERR) == expected_err, \
        f"{fixture}: ERROR 규칙 불일치 — {problems}"
    assert rules(problems, WARN) == expected_warn, \
        f"{fixture}: WARN 규칙 불일치 — {problems}"


# ── L4 사선: 세 갈래 판정 ─────────────────────────────────────────────

def test_L4_distinguishes_true_diagonal_from_fragile_straight():
    problems, _, _ = lint("bad-L4-diagonal.example.drawio")
    l4 = {re.match(r"엣지 (\w+)", msg).group(1): lv
          for r, lv, msg in problems if r == "L4"}
    assert l4["e_diag"] == ERR          # 축 어긋남 → 진짜 사선
    assert l4["e_curved"] == ERR        # curved=1 → 곡선
    assert l4["e_bare_aligned"] == WARN  # 지금은 직선이나 취약


# ── L5 글자 넘침: 폭 초과와 높이 초과를 각각 잡는가 ───────────────────

def test_L5_catches_both_width_and_height_overflow():
    problems, _, _ = lint("bad-L5-overflow.example.drawio")
    msgs = [m for r, _, m in problems if r == "L5"]
    assert any("nowrap" in m and "좌우" in m for m in msgs)
    assert any("toohigh" in m and "위아래" in m for m in msgs)
    assert not any("fits" in m for m in msgs)   # 여유 있는 박스는 무시


def test_L5_text_width_uses_wide_char_metrics():
    """한글은 전각(1.0em), ASCII 는 Helvetica 폭. 같은 글자수라도 폭이 다르다."""
    assert L.text_width("한글다섯글자", 12) == pytest.approx(72.0)
    assert L.text_width("abcdef", 12) < L.text_width("한글다섯글자", 12)


def test_L5_wrap_breaks_cjk_without_spaces():
    """공백 없는 한글 문자열도 문자 단위로 줄바꿈된다 (브라우저 CJK 동작)."""
    assert L.wrap_lines("가나다라마바사아자차", 60, 12) == 2
    assert L.wrap_lines("가나", 60, 12) == 1


# ── L6 겹침 vs 간격 부족 등급 분리 ────────────────────────────────────

def test_L11_spares_escaped_formatting_and_nonhtml_cells():
    """이중 이스케이프·서식 태그·html=0 은 렌더에서 멀쩡하므로 적발하지 않는다."""
    problems, _, _ = lint("bad-L11-eaten-text.example.drawio")
    msgs = [m for r, _, m in problems if r == "L11"]
    assert len(msgs) == 1
    assert "eaten" in msgs[0] and "<id>" in msgs[0]
    for spared in ("ok_escaped", "ok_formatting", "ok_nohtml"):
        assert not any(spared in m for m in msgs), f"{spared} 오탐"


def test_L11_only_applies_when_html_is_on():
    """html=0 이면 꺾쇠가 그대로 렌더되므로 결함이 아니다."""
    cells = {}
    c = L.Cell("x")
    c.value = "Vector<T>"
    c.st = {"html": "0"}
    c.is_vertex = True
    cells["x"] = c
    problems = []
    L.check_html_eaten_text(cells, problems)
    assert problems == []
    c.st = {"html": "1"}
    L.check_html_eaten_text(cells, problems)
    assert rules(problems, ERR) == {"L11"}


def test_L6_overlap_is_error_but_tight_gap_is_warn():
    problems, _, _ = lint("bad-L6-overlap.example.drawio")
    l6 = [(lv, m) for r, lv, m in problems if r == "L6"]
    assert any(lv == ERR and "겹침" in m for lv, m in l6)
    assert any(lv == WARN and "간격 부족" in m for lv, m in l6)


# ── L9/L10: 실제 저장소 예제의 렌더 결함을 잡는가 (회귀 고정) ─────────

@pytest.mark.parametrize("bundle,name", [
    ("sw_structure", "sequence.example.drawio"),
    ("sw_structure", "flow.example.drawio"),
    ("code_review", "flow.example.drawio"),
])
def test_repo_examples_stay_defect_free(bundle, name):
    """저장소가 배포하는 예제는 결함 0 이어야 한다 — Claude 가 베끼는 원본이므로.

    sequence.example.drawio 는 한때 메시지 8개가 같은 선 위에 겹쳐 렌더됐다
    (source/target 이 있으면 mxGraph 가 sourcePoint/targetPoint 를 버린다).
    lifeline + exitY/entryY 분리로 수선했고, 본 테스트가 재발을 막는다.
    """
    path = os.path.join(os.path.dirname(BUNDLE), bundle, "checks", name)
    if not os.path.exists(path):
        pytest.skip("저장소 예제 없음 (번들 단독 배포본)")
    problems, _, _ = L.lint_file(path)
    assert not [p for p in problems if p[1] == ERR], f"{bundle}/{name}: {problems}"


# ── 파서 견고성 ───────────────────────────────────────────────────────

def test_parse_failure_is_reported_as_L1(tmp_path):
    bad = tmp_path / "broken.drawio"
    bad.write_text("<mxfile><diagram>", encoding="utf-8")
    problems, nv, ne = L.lint_file(str(bad))
    assert rules(problems, ERR) == {"L1"}
    assert (nv, ne) == (0, 0)


def test_missing_file_is_reported_as_L1():
    problems, _, _ = L.lint_file("/nonexistent/nope.drawio")
    assert rules(problems, ERR) == {"L1"}


def test_compressed_diagram_is_inflated(tmp_path):
    """drawio 가 압축 저장(base64+deflate)한 파일도 읽어야 한다."""
    import base64
    import urllib.parse
    import zlib
    inner = (
        '<mxGraphModel gridSize="10"><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<mxCell id="a" value="A" style="whiteSpace=wrap;html=1;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="40" width="140" height="50" as="geometry"/></mxCell>'
        '<mxCell id="b" value="B" style="whiteSpace=wrap;html=1;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="200" width="140" height="50" as="geometry"/></mxCell>'
        '<mxCell id="e" style="edgeStyle=orthogonalEdgeStyle;html=1;" edge="1" '
        'parent="1" source="a" target="b"><mxGeometry relative="1" as="geometry"/>'
        '</mxCell></root></mxGraphModel>'
    )
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = co.compress(urllib.parse.quote(inner).encode()) + co.flush()
    payload = base64.b64encode(packed).decode()
    f = tmp_path / "compressed.drawio"
    f.write_text(f'<mxfile><diagram name="c" id="c1">{payload}</diagram></mxfile>',
                 encoding="utf-8")
    problems, nv, ne = L.lint_file(str(f))
    assert (nv, ne) == (2, 1), f"압축 해제 실패: {problems}"
    assert problems == []


def test_object_wrapper_label_is_read(tmp_path):
    """<object label=...> 로 감싼 셀도 라벨 넘침을 검사해야 한다."""
    xml = (
        '<mxfile><diagram name="o"><mxGraphModel gridSize="10"><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<object label="아주아주아주긴한글라벨입니다" id="w1">'
        '<mxCell style="html=1;" vertex="1" parent="1">'
        '<mxGeometry x="40" y="40" width="60" height="30" as="geometry"/>'
        '</mxCell></object>'
        '</root></mxGraphModel></diagram></mxfile>'
    )
    f = tmp_path / "obj.drawio"
    f.write_text(xml, encoding="utf-8")
    problems, nv, _ = L.lint_file(str(f))
    assert nv == 1
    assert "L5" in rules(problems, ERR)


def test_child_geometry_is_absolutized(tmp_path):
    """그룹 자식 좌표는 부모 기준 상대값 — 절대 좌표로 환산해야 겹침 판정이 맞다."""
    xml = (
        '<mxfile><diagram name="g"><mxGraphModel gridSize="10"><root>'
        '<mxCell id="0"/><mxCell id="1" parent="0"/>'
        '<mxCell id="grp" value="" style="group;" vertex="1" parent="1">'
        '<mxGeometry x="200" y="200" width="300" height="200" as="geometry"/></mxCell>'
        '<mxCell id="kid" value="K" style="whiteSpace=wrap;html=1;" vertex="1" parent="grp">'
        '<mxGeometry x="10" y="10" width="100" height="40" as="geometry"/></mxCell>'
        '</root></mxGraphModel></diagram></mxfile>'
    )
    f = tmp_path / "group.drawio"
    f.write_text(xml, encoding="utf-8")
    models = L.load_models(str(f))
    cells = L.collect_cells(models[0][1])
    assert (cells["kid"].ax, cells["kid"].ay) == (210, 210)
    # 컨테이너-자식 포함은 겹침으로 보고하지 않는다
    problems = []
    L.check_overlap(cells, problems)
    assert not [m for r, lv, m in problems if lv == ERR]


# ── L3 mermaid 대조 ───────────────────────────────────────────────────

def test_L3_count_mismatch_is_reported():
    problems, _, _ = L.lint_file(
        os.path.join(CHECKS, "good.example.drawio"),
        expect_nodes=99, expect_edges=99)
    assert rules(problems, ERR) == {"L3"}
    assert len([p for p in problems if p[0] == "L3"]) == 2


def test_L3_matching_counts_pass():
    problems, _, _ = L.lint_file(
        os.path.join(CHECKS, "good.example.drawio"),
        expect_nodes=5, expect_edges=4)
    assert problems == []
