---
name: hwpx
description: "HWPX 문서(.hwpx 파일)를 생성, 읽기, 편집, 템플릿 치환하고 PDF 렌더로 시각 검증하는 스킬. '한글 문서', 'hwpx', 'HWPX', '한글파일', '.hwpx 파일 만들어줘', 'HWP 문서 생성', '보고서', '공문', '기안문', '한글로 작성', '한글을 PDF로' 등의 키워드가 나오면 반드시 이 스킬을 사용할 것. 한글과컴퓨터(한컴)의 HWPX 포맷(KS X 6101/OWPML 기반, ZIP+XML 구조)을 ZIP-level 치환으로 다루고, 생성·편집 후에는 반드시 PDF→PNG 렌더 검증 루프(서식·글자 깨짐·디자인 검토)를 통과시킨다. 일반 Word(.docx) 문서에는 docx 스킬을 사용할 것."
---

# HWPX 문서 생성·편집 + 렌더 검증 스킬

## 개요

HWPX 는 한컴오피스 한글의 개방형 문서 포맷이다. 내부는 **ZIP 패키지 + XML 파트** 구조이며, KS X 6101(OWPML) 표준에 기반한다. 이 스킬은 HWPX 문서를 ZIP-level 치환으로 생성·편집하고, **LibreOffice+H2Orestart 렌더 검증 루프**로 결과를 눈으로 확인한다.

스킬 루트: `~/.claude/skills/hwpx/` (아래 상대 경로는 모두 여기 기준)

## 환경 준비 (최초 1회)

```bash
bash ~/.claude/skills/hwpx/scripts/setup_env.sh   # 루트 불필요, 멱등
pip install python-hwpx --user                     # ObjectFinder (텍스트 전수 조사)
```

---

## ⚠️⚠️⚠️ 최우선 규칙 1: 양식(템플릿) 선택 정책 ⚠️⚠️⚠️

> **HWPX 문서를 만들 때 반드시 아래 순서를 따른다. 예외 없음.**

### 1단계: 사용자 제공 양식이 있는가?

사용자가 `.hwpx` 양식 파일을 제공(경로 지정·업로드)했다면 **반드시 해당 파일을 템플릿으로 사용**한다.
- 사용자가 "이 양식으로 만들어줘", "이 파일 기반으로" 등의 표현을 쓰면 100% 해당 파일 사용

### 2단계: 기본 제공 양식 사용

사용자 제공 양식이 없으면 **반드시 기본 제공 양식**을 사용한다:
- 보고서 → `assets/report-template.hwpx`
- (향후 추가될 다른 양식들도 이 규칙 적용)

### 3단계: HwpxDocument.new()는 최후의 수단

`HwpxDocument.new()`로 빈 문서를 만드는 것은 **아주 단순한 메모·목록 수준의 문서에만** 허용한다. 보고서, 공문, 기안문 등 양식이 필요한 문서는 절대 `new()`로 만들지 않는다.

---

## ⚠️⚠️⚠️ 최우선 규칙 2: 렌더 시각 검증 루프 (완료 선언 전 필수) ⚠️⚠️⚠️

> **HWPX 를 만들거나 고쳤으면, 반드시 PDF 로 출력해 서식·글자 깨짐·디자인을 눈으로
> 검토하고, 이상이 있으면 수정 후 재렌더한다. 이 루프를 통과하기 전에는 "완료"라고
> 말하지 않는다.** 구조(XML/ZIP) 검증만으로는 렌더에서만 드러나는 결함(자간 겹침,
> 색·정렬 오류, 페이지 넘침)을 잡을 수 없기 때문이다.

```bash
python3 ~/.claude/skills/hwpx/scripts/render_verify.py <file.hwpx>
# → <dir>/render-verify/ 에 PDF + page-N.png + 페이지 텍스트 생성
```

이후 **각 page-N.png 를 Read 도구로 열어** `references/render-verify.md` 의 체크리스트
(글자 깨짐·치환 정합·서식·정렬·줄바꿈·페이지 수·디자인)를 검토한다. 문제 발견 시
편집 단계로 복귀해 수정하고 재렌더한다. 렌더 함정(원인 진단)은
`references/hwp-render-gotchas.md` 를 먼저 확인.

---

## 필수 워크플로우 (모든 경우에 적용)

```
[1] 양식 파일을 작업 디렉터리로 복사
     ↓
[2] ObjectFinder 로 양식 내 텍스트 전수 조사
     ↓
[3] 플레이스홀더 목록 작성 (어떤 텍스트를 뭘로 바꿀지 매핑)
     ↓
[4] ZIP-level 전체 치환 (표 내부 포함)
     ↓  (동일 플레이스홀더가 여러 번 나오면 순차 치환 사용)
[5] linesegarray 제거 (scripts/fix_linesegarray.py --all)
     ↓  치환된 텍스트의 자간/줄간격 깨짐 방지
[6] 네임스페이스 후처리 (scripts/fix_namespaces.py)
     ↓
[7] ObjectFinder 로 치환 결과 검증 (구조 검증)
     ↓
[8] ★ 렌더 시각 검증 루프 (scripts/render_verify.py → PNG Read → 체크리스트)
     ↓  이상 시 [3]~[4] 로 복귀 (반복)
[9] 통과 후 결과물 전달 (.hwpx + 검증용 .pdf 경로 보고)
```

### 미사용 플레이스홀더 블록 처리 (텍스트만 비우지 말 것)

양식의 반복 블록(□○―※ 8세트 등)을 전부 쓰지 않을 때, 남는 플레이스홀더를
빈 문자열로 치환하면 **마커 런(□ 등)과 문단 간격이 남아 렌더에 빈 뼈대가 나타난다**
(렌더 시각 검증에서만 드러나는 결함). 반드시 문단째 삭제한다:

```bash
python3 ~/.claude/skills/hwpx/scripts/remove_paragraphs.py report.hwpx \
    "헤드라인M 폰트 16포인트(문단 위 15)" "  ○ 휴면명조 15포인트(문단위 10)" \
    "   ― 휴면명조 15포인트(문단 위 6)" "     ※ 중고딕 13포인트(문단 위 3)"
```

삭제 후 fix_linesegarray → fix_namespaces 후처리를 다시 실행한다.

### 핵심: HwpxDocument.open()은 사용하지 않는다

`python-hwpx` 버전에 따라 `HwpxDocument.open()`이 복잡한 양식 파일을 파싱하지 못할 수 있다. **ZIP-level 치환만 사용**하는 것이 안전하다.

---

## ZIP-level 치환 함수 (직접 구현)

`hwpx_replace` 모듈은 별도로 존재하지 않으므로 아래 함수를 직접 코드에 포함한다:

### 일괄 치환 (동일 텍스트를 모두 같은 값으로)

```python
import zipfile, os

def zip_replace(src_path, dst_path, replacements):
    """HWPX ZIP 내 모든 XML에서 텍스트 치환 (표 내부 포함)"""
    tmp = dst_path + ".tmp"
    with zipfile.ZipFile(src_path, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("Contents/") and item.filename.endswith(".xml"):
                    text = data.decode("utf-8")
                    for old, new in replacements.items():
                        text = text.replace(old, new)
                    data = text.encode("utf-8")
                zout.writestr(item, data)
    if os.path.exists(dst_path):
        os.remove(dst_path)
    os.rename(tmp, dst_path)
```

### 순차 치환 (동일 플레이스홀더를 순서대로 다른 값으로)

```python
def zip_replace_sequential(src_path, dst_path, old, new_list):
    """section XML에서 old를 순서대로 new_list 값으로 하나씩 치환"""
    tmp = dst_path + ".tmp"
    with zipfile.ZipFile(src_path, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if "section" in item.filename and item.filename.endswith(".xml"):
                    text = data.decode("utf-8")
                    for new_val in new_list:
                        text = text.replace(old, new_val, 1)  # 1번만 치환
                    data = text.encode("utf-8")
                zout.writestr(item, data)
    if os.path.exists(dst_path):
        os.remove(dst_path)
    os.rename(tmp, dst_path)
```

---

## 양식 내 텍스트 전수 조사 방법

```python
from hwpx import ObjectFinder

finder = ObjectFinder("양식파일.hwpx")
results = finder.find_all(tag="t")
for r in results:
    if r.text and r.text.strip():
        print(repr(r.text))
```

이 결과를 보고 어떤 텍스트가 플레이스홀더인지 파악한 후, 치환 매핑을 작성한다.
(python-hwpx 미설치 등으로 ObjectFinder 를 못 쓰면 `zipfile` + 정규식
`<hp:t[^>]*>([^<]*)</hp:t>` 로 section XML 에서 직접 추출해도 된다.)

---

## 기본 양식(report-template.hwpx) 활용 가이드

### 양식 구조

```
1쪽: 표지      → 기관명(30pt) + 보고서 제목(25pt) + 작성일(25pt)
2쪽: 목차      → 로마숫자(Ⅰ~Ⅴ) + 제목 + 페이지, 붙임/참고
3쪽~: 본문     → 결재란 + 제목(22pt) + 섹션 바(Ⅰ~Ⅳ) + □○―※ 계층 본문
```

### 본문 기호 체계 (공문서와 완전히 다름!)

```
1단계:  □    (HY헤드라인M 16pt, 문단 위 15)
2단계:  ○    (휴먼명조 15pt, 문단 위 10)
3단계:  ―    (휴먼명조 15pt, 문단 위 6)
4단계:  ※    (한양중고딕 13pt, 문단 위 3)
```

### 치환 가능한 플레이스홀더 목록

| 플레이스홀더 | 위치 | 치환 대상 | 치환 방법 |
|------------|------|----------|----------|
| `브라더 공기관` | 표지 1줄 | 기관명 | 일괄 치환 |
| `기본 보고서 양식` | 표지 2줄 | 보고서 제목 | 일괄 치환 |
| `2024. 5. 23.` | 표지 작성일 | 실제 작성일 | 일괄 치환 |
| `제 목` | 본문 페이지 제목 | 보고서 제목 | 일괄 치환 |
| `. 개요` 등 | 목차 항목 | 실제 목차 제목 | 일괄 치환 |
| ` 추진 배경` 등 | 섹션 바 제목 | 실제 섹션 제목 | 일괄 치환 |
| `헤드라인M 폰트 16포인트(문단 위 15)` | □ 본문 (8개) | 1단계 내용 | **순차 치환** |
| `  ○ 휴면명조 15포인트(문단위 10)` | ○ 본문 (8개) | 2단계 내용 | **순차 치환** |
| `   ― 휴면명조 15포인트(문단 위 6)` | ― 본문 (8개) | 3단계 내용 | **순차 치환** |
| `     ※ 중고딕 13포인트(문단 위 3)` | ※ 주석 (7개) | 4단계 참조 | **순차 치환** |
| `  1. 세부내용` / `  2. 세부내용` | 붙임/참고 | 첨부 목록 | 일괄 치환 |

### 기본 양식 사용 예시 (전체 코드)

```python
import os, shutil, subprocess

SKILL = os.path.expanduser("~/.claude/skills/hwpx")
TEMPLATE = f"{SKILL}/assets/report-template.hwpx"
WORK = "./report.hwpx"          # 작업 디렉터리(프로젝트/스크래치패드)에 생성
shutil.copy(TEMPLATE, WORK)

# 1. 표지 + 목차 + 섹션 바 + 제목 (일괄 치환)
zip_replace(WORK, WORK, {
    "브라더 공기관": "실제 기관명",
    "기본 보고서 양식": "실제 보고서 제목",
    "2024. 5. 23.": "2026. 7. 17.",
    "제 목": "실제 보고서 제목",
    ". 개요": ". 실제 목차1",
    ". 추진배경": ". 실제 목차2",
    # ... 나머지 목차, 섹션 바 치환
})

# 2. □ 항목 (순차 치환 — 8개)
zip_replace_sequential(WORK, WORK,
    "헤드라인M 폰트 16포인트(문단 위 15)",
    ["첫번째 □ 내용", "두번째 □ 내용", ...]
)

# 3. ○, ―, ※ 항목도 각각 순차 치환
# ...

# 4. linesegarray 제거 (필수! 자간 깨짐 방지)
subprocess.run(["python3", f"{SKILL}/scripts/fix_linesegarray.py", WORK], check=True)

# 5. 네임스페이스 후처리 (필수!)
subprocess.run(["python3", f"{SKILL}/scripts/fix_namespaces.py", WORK], check=True)

# 6. 구조 검증 (ObjectFinder 또는 zipfile+정규식)
# 7. ★ 렌더 시각 검증 (필수)
subprocess.run(["python3", f"{SKILL}/scripts/render_verify.py", WORK], check=True)
# → render-verify/page-N.png 를 Read 도구로 열어 체크리스트 검토
```

---

## 사용자 제공 양식 활용 가이드

사용자가 자신만의 `.hwpx` 양식을 제공한 경우:

1. 양식을 작업 디렉터리로 복사
2. **양식 내 텍스트 전수 조사 (★ 필수)** — 양식마다 플레이스홀더가 다르므로 반드시 조사 후 진행
3. 조사 결과로 치환 매핑 작성
4. ZIP-level 치환 (`zip_replace` / 반복 플레이스홀더는 `zip_replace_sequential`)
5. `fix_linesegarray.py` → `fix_namespaces.py` 후처리
6. 치환 결과 구조 검증
7. **렌더 시각 검증 루프 (최우선 규칙 2)**

---

## 문서 유형별 스타일 가이드

### 보고서(내부 보고용) 작성 시

→ **`references/report-style.md`** 를 먼저 읽고 따를 것

### 공문서(기안문) 작성 시

→ **`references/official-doc-style.md`** 를 먼저 읽고 따를 것

### 저수준 XML 조작이 필요한 경우

→ **`references/xml-internals.md`** 를 읽을 것

### 렌더 검증·렌더 함정

→ **`references/render-verify.md`** (루프·체크리스트·Linux 한계·Windows 부록)
→ **`references/hwp-render-gotchas.md`** (신규 paraPr margin 무시, lineBreak 무시, 표 쪽나눔, 내어쓰기, 보안 모달 hang)

---

## ⚠️ 필수 후처리 1: linesegarray 제거 (자간/줄간격 수정)

> **텍스트 치환 후 반드시 실행. 빠뜨리면 자간이 찌그러지거나 줄간격이 깨진다.**

### 원인
linesegarray 는 한글이 마지막으로 렌더링한 레이아웃 캐시이다. 짧은 텍스트에 대한
레이아웃 정보가 남아 있으면, 긴 텍스트로 치환했을 때 한글이 캐시를 그대로 사용하려 해서
자간이 찌그러진다.

### 해결
linesegarray 를 제거하면 한글이 파일을 열 때 자동으로 레이아웃을 재계산한다.

```python
subprocess.run(["python3", f"{SKILL}/scripts/fix_linesegarray.py", WORK], check=True)
```

### 빈 셀/빈 run 처리
표 내부 텍스트를 빈 문자열로 치환하면 빈 노드가 남을 수 있다.
이 경우에도 linesegarray 를 제거하면 한글이 빈 셀을 정상 처리한다.

---

## ⚠️ 필수 후처리 2: 네임스페이스 수정

> **가장 중요한 단계. 빠뜨리면 한글 Viewer 에서 빈 페이지로 표시된다.**

ZIP-level 치환 후 또는 `doc.save()` 후 반드시 실행:

```python
subprocess.run(["python3", f"{SKILL}/scripts/fix_namespaces.py", WORK], check=True)
```

> 주의: `exec(open(...).read())` 방식은 스크립트의 `if __name__ == "__main__"` 블록 때문에 오동작할 수 있다. 반드시 `subprocess.run()` 방식을 사용한다.

---

## Quick Reference

| 작업 | 접근 방식 |
|------|----------|
| 보고서/공문/양식 문서 생성 | **양식 파일 + ZIP-level 치환** (★ 권장) |
| 아주 단순한 문서 | `HwpxDocument.new()` → `.save()` → 후처리 |
| 표(테이블) 추가 | `doc.add_table(rows, cols)` → `set_cell_text()` |
| 머리글/바닥글 | `doc.set_header_text()` / `doc.set_footer_text()` |
| 텍스트 검색/추출 | `ObjectFinder(filepath)` |
| **자간/줄간격 수정** | **`fix_linesegarray.py` (치환 후 필수)** |
| 미사용 플레이스홀더 블록 삭제 | `remove_paragraphs.py` (빈 문자열 치환 금지) |
| **렌더 시각 검증** | **`render_verify.py` → PNG Read (완료 선언 전 필수)** |
| 셀 병합 | `table.merge_cells(row1, col1, row2, col2)` |

---

## 주의사항

1. **양식 우선**: 사용자 제공 양식 > 기본 제공 양식 > HwpxDocument.new()
2. **ZIP-level 치환 우선**: HwpxDocument.open()보다 ZIP-level 치환이 안전하고 호환성이 높다
3. **네임스페이스 후처리 필수**: 모든 저장/치환 후 `fix_namespaces.py` 실행
4. **양식 텍스트 조사 필수**: 치환 전에 반드시 텍스트 전수 조사
5. **순차 치환 주의**: 동일 플레이스홀더가 여러 번 나오면 `zip_replace_sequential` 사용
6. **레이아웃 충실도**: ZIP 치환은 레이아웃 엔진이 아님. 페이지 나눔은 뷰어가 결정
7. **글꼴 임베딩**: 생성 HWPX 에 글꼴 미포함. 열람 환경에 해당 글꼴 필요
8. **공문서 날짜 형식**: `2026-02-13`이 아닌 `2026. 2. 13.` (월·일 앞 0 생략)
9. **HWPX ↔ HWP**: 이 스킬은 HWPX 만 처리. 레거시 `.hwp`는 별도 도구 필요
10. **fix_namespaces 호출법**: `exec()` 말고 `subprocess.run()` 사용
11. **linesegarray 제거 필수**: 텍스트 치환 후 반드시 `fix_linesegarray.py` 실행
12. **후처리 순서 준수**: 치환 → linesegarray 제거 → 네임스페이스 후처리 → **렌더 검증**
13. **빈 셀 처리**: 표 내부 텍스트를 빈 문자열로 치환 시에도 linesegarray 제거 필요
14. **완료 선언 금지**: 렌더 시각 검증 루프(최우선 규칙 2)를 통과하기 전에는 완료가 아니다
