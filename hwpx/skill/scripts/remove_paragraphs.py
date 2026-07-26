#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HWPX 미사용 플레이스홀더 문단 삭제 유틸리티

양식의 반복 블록(□○―※ 등)을 전부 쓰지 않을 때, 남는 플레이스홀더의
텍스트만 빈 문자열로 치환하면 **마커 런(□ 등)과 문단 간격이 그대로 남아**
렌더에 빈 뼈대가 나타난다(렌더 시각 검증에서 발견되는 전형적 결함).
이 스크립트는 지정 문자열을 포함한 <hp:p> 문단을 통째로 삭제한다.

주의:
  - 문단 안에 표/그림이 없는 단순 텍스트 문단에만 사용할 것 (비탐욕 매칭).
  - 삭제 후 fix_linesegarray.py → fix_namespaces.py 후처리를 다시 실행할 것.

사용:
  python3 remove_paragraphs.py <file.hwpx> <포함문자열> [<포함문자열> ...]
"""
import re
import sys
import zipfile
import os


def paragraph_text(p_xml):
    return "".join(re.findall(r"<[a-zA-Z0-9]*:?t[^>]*>([^<]*)</[a-zA-Z0-9]*:?t>", p_xml))


def remove_paragraphs(hwpx_path, needles):
    tmp = hwpx_path + ".tmp"
    removed = 0
    p_pattern = re.compile(r"<([a-zA-Z0-9]+:)?p\b[^>]*>.*?</\1p>", re.DOTALL)
    with zipfile.ZipFile(hwpx_path, "r") as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if "section" in item.filename and item.filename.endswith(".xml"):
                text = data.decode("utf-8")

                def repl(m):
                    nonlocal removed
                    ptext = paragraph_text(m.group(0))
                    if any(n in ptext for n in needles):
                        removed += 1
                        return ""
                    return m.group(0)

                text = p_pattern.sub(repl, text)
                data = text.encode("utf-8")
            zout.writestr(item, data)
    os.replace(tmp, hwpx_path)
    print(f"Removed {removed} paragraph(s) from {hwpx_path}")
    return removed


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    remove_paragraphs(sys.argv[1], sys.argv[2:])
