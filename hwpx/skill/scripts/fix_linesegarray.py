#!/usr/bin/env python3
"""
HWPX linesegarray 제거 유틸리티

텍스트 치환 후 원본 paragraph의 linesegarray(레이아웃 캐시)가
남아 있으면 자간/줄간격이 깨진다. 이 스크립트로 linesegarray를
제거하면 한글이 파일을 열 때 자동으로 레이아웃을 재계산한다.

실행 순서:
  1. zip_replace / zip_replace_sequential (텍스트 치환)
  2. fix_linesegarray.py (이 스크립트)      <- 치환 직후
  3. fix_namespaces.py (네임스페이스 후처리)

사용법:
  CLI:
    python fix_linesegarray.py <file.hwpx>                 # --all (기본)
    python fix_linesegarray.py <file.hwpx> --all           # 모든 paragraph
    python fix_linesegarray.py <file.hwpx> --changed-only <original.hwpx>

  Import:
    from fix_linesegarray import remove_linesegarray
    remove_linesegarray("output.hwpx")                     # --all 모드
    remove_linesegarray("output.hwpx", original="template.hwpx")  # --changed-only
"""

import zipfile
import os
import re
import sys


def _remove_all_linesegarray(xml_text):
    """모든 linesegarray 요소를 제거한다 (자기 닫힘 태그 + 블록 태그 모두)."""
    patterns = [
        # 네임스페이스 프리픽스 있는 블록 태그 (hp:, ns0:, ns1: 등)
        r'<[a-zA-Z0-9]+:linesegarray[^>]*>.*?</[a-zA-Z0-9]+:linesegarray>',
        # 네임스페이스 프리픽스 없는 블록 태그
        r'<linesegarray[^>]*>.*?</linesegarray>',
        # 자기 닫힘 태그 (프리픽스 있음)
        r'<[a-zA-Z0-9]+:linesegarray[^/]*/\s*>',
        # 자기 닫힘 태그 (프리픽스 없음)
        r'<linesegarray[^/]*/\s*>',
    ]
    result = xml_text
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.DOTALL)
    return result


def _extract_paragraph_texts(xml_text):
    """paragraph별 텍스트 내용을 추출하여 dict로 반환 (인덱스 -> 텍스트)."""
    paragraphs = {}
    p_pattern = r'<[a-zA-Z0-9]*:?p\b[^>]*>(.*?)</[a-zA-Z0-9]*:?p>'
    t_pattern = r'<[a-zA-Z0-9]*:?t[^>]*>([^<]*)</[a-zA-Z0-9]*:?t>'
    for i, p_match in enumerate(re.finditer(p_pattern, xml_text, re.DOTALL)):
        p_content = p_match.group(1)
        texts = re.findall(t_pattern, p_content)
        paragraphs[i] = ''.join(texts)
    return paragraphs


def _remove_changed_linesegarray(xml_text, original_xml_text):
    """원본과 비교하여 텍스트가 변경된 paragraph의 linesegarray만 제거한다."""
    orig_paragraphs = _extract_paragraph_texts(original_xml_text)
    new_paragraphs = _extract_paragraph_texts(xml_text)

    changed_indices = set()
    for idx in new_paragraphs:
        orig_text = orig_paragraphs.get(idx, '')
        if new_paragraphs[idx] != orig_text:
            changed_indices.add(idx)

    if not changed_indices:
        return xml_text

    p_pattern = r'(<[a-zA-Z0-9]*:?p\b[^>]*>)(.*?)(</[a-zA-Z0-9]*:?p>)'
    result_parts = []
    last_end = 0

    for i, match in enumerate(re.finditer(p_pattern, xml_text, re.DOTALL)):
        result_parts.append(xml_text[last_end:match.start()])
        if i in changed_indices:
            cleaned_body = _remove_all_linesegarray(match.group(2))
            result_parts.append(match.group(1) + cleaned_body + match.group(3))
        else:
            result_parts.append(match.group(0))
        last_end = match.end()

    result_parts.append(xml_text[last_end:])
    return ''.join(result_parts)


def remove_linesegarray(hwpx_path, original=None):
    """
    HWPX 파일의 Contents/*.xml에서 linesegarray를 제거한다.

    Args:
        hwpx_path: 수정할 .hwpx 파일 경로
        original: (선택) 원본 .hwpx 파일 경로. 지정 시 변경된 paragraph만 처리.

    Returns:
        수정된 XML 파일 수
    """
    tmp_path = hwpx_path + ".tmp"
    removed_count = 0

    original_xmls = {}
    if original:
        with zipfile.ZipFile(original, "r") as zin:
            for item in zin.infolist():
                if item.filename.startswith("Contents/") and item.filename.endswith(".xml"):
                    original_xmls[item.filename] = zin.read(item.filename).decode("utf-8")

    with zipfile.ZipFile(hwpx_path, "r") as zin:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)

                if item.filename.startswith("Contents/") and item.filename.endswith(".xml"):
                    text = data.decode("utf-8")

                    if original and item.filename in original_xmls:
                        new_text = _remove_changed_linesegarray(text, original_xmls[item.filename])
                    else:
                        new_text = _remove_all_linesegarray(text)

                    if new_text != text:
                        removed_count += 1
                    data = new_text.encode("utf-8")

                zout.writestr(item, data)

    os.replace(tmp_path, hwpx_path)
    return removed_count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fix_linesegarray.py <file.hwpx>                          # all (default)")
        print("  python fix_linesegarray.py <file.hwpx> --all                    # all paragraphs")
        print("  python fix_linesegarray.py <file.hwpx> --changed-only <orig>    # changed only")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Error: File not found: {path}")
        sys.exit(1)

    original = None
    if "--changed-only" in sys.argv:
        idx = sys.argv.index("--changed-only")
        if idx + 1 >= len(sys.argv):
            print("Error: --changed-only requires <original.hwpx> path")
            sys.exit(1)
        original = sys.argv[idx + 1]
        if not os.path.exists(original):
            print(f"Error: Original file not found: {original}")
            sys.exit(1)

    count = remove_linesegarray(path, original=original)
    mode = "changed-only" if original else "all"
    print(f"Fixed linesegarray ({mode}): {count} XML file(s) modified in {path}")
