# 렌더 시각 검증 루프 (HWPX 생성·편집 후 필수)

> **원칙: 완료 선언 = 렌더 시각 검증 통과 이후.** 구조(XML/ZIP) 검증만으로 "완료" 금지.
> 문서 포맷은 레이아웃 캐시·글자속성·표 속성이 렌더를 좌우하므로, 실제 렌더 출력(PDF→PNG)을
> 눈으로 확인해야 글자 깨짐·색·정렬·줄바꿈·페이지 넘침 결함을 잡을 수 있다.

## 루프 (Linux)

```
편집(ZIP 치환) → fix_linesegarray → fix_namespaces
   → scripts/render_verify.py <file.hwpx>     # PDF + PNG + 페이지 텍스트 한번에
   → 각 page-N.png 를 Read 도구로 열어 체크리스트 검토
   → 이상 발견 → 편집 단계로 복귀하여 수정 → 재렌더 (반복)
   → 전 항목 통과 → 완료 선언
```

개별 단계 실행이 필요하면:
```bash
python3 scripts/render_pdf.py  <file.hwpx> [out.pdf]   # HWPX → PDF (LibreOffice+H2Orestart)
python3 scripts/pdf_to_png.py  <file.pdf>  [outdir]    # PDF → page-N.png (pdftoppm)
```

## 체크리스트 (PNG 마다 확인)

- [ ] **글자 깨짐**: U+FFFD(�)·□(tofu)·자간 겹침이 없는가 (render_verify.py 가 텍스트 추출로 1차 경고)
- [ ] **치환 정합**: 플레이스홀더가 남아 있지 않은가 / 치환 값이 올바른 위치에 들어갔는가
- [ ] **서식**: 글자색·굵기·이탤릭·크기가 의도대로인가 (placeholder 서식 상속 오류 주의)
- [ ] **정렬**: LEFT/JUSTIFY — 좁은 셀은 JUSTIFY 가 단어 사이 공백을 벌림
- [ ] **줄바꿈**: 겹침 없는가 / 의도한 줄바꿈이 실제 반영됐는가
- [ ] **페이지 수**: 예기치 않은 오버플로로 페이지가 늘지 않았는가
- [ ] **디자인**: 계층 기호(□○―※)·섹션 바·표지 요소가 템플릿 의도대로 배치됐는가
- [ ] **빈 뼈대**: 마커(□ 등)만 남고 내용이 빈 문단이 없는가 — 미사용 플레이스홀더를
      빈 문자열로 치환한 흔적. `scripts/remove_paragraphs.py` 로 문단째 삭제할 것

문제를 발견하면 `references/hwp-render-gotchas.md` 의 함정 목록(신규 paraPr margin 무시,
lineBreak 무시, 표 쪽나눔, 내어쓰기, linesegarray 캐시)에서 원인을 먼저 찾을 것.

## Linux 렌더의 한계 (정직하게 알고 쓸 것)

- LibreOffice+H2Orestart 렌더는 **한컴 한글의 렌더와 근사**하다. 원본 폰트(휴먼명조 등)가
  없으면 fontconfig 별칭(Nanum 계열)으로 대체되므로 **자간·줄높이·페이지 경계가 실제
  한글과 1:1 이 아닐 수 있다** (예: 원본 5쪽 → 대체 폰트로 4쪽).
- 따라서 Linux 루프가 확실히 잡는 것: 글자 깨짐, 치환 누락/오위치, 색·굵기·정렬,
  계층 기호·표 구조, 큰 폭의 오버플로. 최종 인쇄 픽셀 검증이 필요하면 Windows+한글에서
  아래 부록 경로로 재검증한다.
- 환경 준비는 `scripts/setup_env.sh` (포터블 LibreOffice + H2Orestart + Nanum 폰트, 루트 불필요).

## 부록: Windows + 한컴오피스 경로 (원조 파이프라인)

```python
from pyhwpx import Hwp          # pip install pyhwpx pywin32
hwp = Hwp(new=True, visible=True, register_module=True)
hwp.open(src_hwpx)
hwp.save_as(pdf_path, "PDF")
hwp.quit()
```
- **headless(visible=False)·포그라운드 실행은 보안 승인/PDF 저장 모달로 hang**(수 분 타임아웃).
  반드시 **백그라운드 프로세스 + visible=True** 로 실행.
- `register_module=True` 가 파일 접근 보안 대화상자를 억제. `RegisterModule` 경고가 떠도
  활성 데스크톱 세션이면 렌더는 성공한다. 비대화형(서비스) 세션에서는 실패할 수 있다.
- PDF→PNG 는 동일하게 `scripts/pdf_to_png.py` (pypdfium2 폴백 내장, poppler 불요).
