# 한글 HWPX 렌더 함정 모음

> 실전에서 렌더 시각 검증으로 확인한, XML만 봐서는 알 수 없는 한글(HWPX) 동작. 각 항목은 "증상 → 원인 → 해결"로 정리.

## 1. 새로 추가한 paraPr/charPr의 margin은 한글이 무시한다 ⚠️ (가장 중요)
- **증상**: 헤더에 새 `<hh:paraPr id="42">`(또는 charPr)를 추가하고 문단이 `paraPrIDRef="42"`로 참조하면, **텍스트·정렬은 렌더되지만 그 margin(left/intent 등)은 반영되지 않는다.** 값(intent=-1400/-4000/-13672)을 바꿔도, 한글로 재저장(재계산)해도 무시됨.
- **원인**: 한글 렌더가 **템플릿에 원래 등록돼 있던 스타일**의 margin만 신뢰. 손으로 추가한 신규 스타일 id는 본문은 렌더하되 여백 속성은 적용하지 않음(itemCnt 증가시켜도 동일).
- **해결**: 여백/들여쓰기를 바꾸려면 **기존(등록된) paraPr를 직접 수정**하거나, **이미 존재하는 적절한 paraPr를 재사용**한다. 새 스타일 추가로 해결하려 하지 말 것.
  - 예) 특정 필드에만 내어쓰기를 주고 싶으면, 그 필드가 이미 쓰는 기존 paraPr를 수정하거나, 템플릿 내 음수 intent를 가진 기존 paraPr를 찾아 그 필드에 배정.

## 2. `<hp:lineBreak/>`는 렌더에서 무시된다
- **증상**: 한 문단 안에서 줄을 나누려고 `<hp:run>...<hp:t>A</hp:t><hp:lineBreak/><hp:t>B</hp:t></hp:run>` 를 넣어도 A와 B가 한 줄로 이어져 렌더됨.
- **해결**: 강제 줄바꿈은 **별도 `<hp:p>` 문단**으로 분리한다(같은 paraPrIDRef·charPrIDRef 재사용, id만 유니크하게).
```python
# guide 단일 문단을 여러 <hp:p>로 분리
segs = re.split(r'(?=①|②|③|④)', full_text)
paras = ''.join(opening_tag_with_new_id + f'<hp:run charPrIDRef="43"><hp:t>{esc(s)}</hp:t></hp:run></hp:p>' for s in segs)
```
- **부작용 주의**: 문단이 늘면 내용 높이가 커져 표/페이지가 넘칠 수 있다(→ 3번).

## 3. 표 쪽나눔: `pageBreak="TABLE"` vs `"CELL"`
- **증상**: 셀 내용이 길어져 한 쪽을 넘으면 표가 통째로 다음 쪽으로 밀리거나 푸터가 어긋남.
- **원인**: `<hp:tbl ... pageBreak="TABLE">` = 표를 쪽 경계에서 나누지 않음(행이 안 쪼개짐).
- **해결**: 내용이 자연스럽게 다음 쪽으로 흐르게 하려면 `pageBreak="CELL"`(셀을 나눠 다음 쪽으로)로 변경.
```python
xml = xml.replace('pageBreak="TABLE"', 'pageBreak="CELL"')
```

## 4. 내어쓰기(hanging indent)는 기존 paraPr의 음수 intent로만 적용
- **증상**: 번호 목록(①②③…)에서 줄바꿈 시 접힌 줄을 번호 뒤로 정렬하고 싶음.
- **원인/해결**: `<hh:margin>`의 `<hc:intent value="-D"/>`(음수 = 내어쓰기)로 구현하되, **1번 규칙 때문에 반드시 "기존 등록 paraPr"에 적용**해야 렌더에 반영된다. 새 paraPr에 넣으면 무시됨.
  - D 값은 마커 폭에 맞춘다(9pt 기준 "① " ≈ 약 1400 HWPUNIT). `7200 HWPUNIT = 1 inch`, charPr `height`는 1/100pt.
  - 필드별로 다른 내어쓰기가 필요하면, 그 필드가 참조하는 기존 paraPr를 분기(다른 기존 id로 배정)하거나 템플릿 스타일을 조정.

## 5. 한글 자동화는 보안 모달로 hang → 백그라운드+visible로 우회
- **증상**: `HwpFrame.HwpObject`/pyhwpx로 `Open`/`SaveAs` 시 몇 분간 멈춤(타임아웃).
- **원인**: 파일 접근 보안 승인 대화상자, PDF 저장 옵션 모달이 비대화형에서 응답 불가.
- **해결**: `pyhwpx.Hwp(new=True, visible=True, register_module=True)` + **백그라운드 프로세스**로 실행. 헤드리스(visible=False)·포그라운드 회피. (자세히는 `render-verify.md`)

## 부가: linesegarray(레이아웃 캐시) 재확인
- 텍스트 치환 후 원 문단의 `<hp:linesegarray>`가 남으면 짧은 캐시에 긴 텍스트가 욱여넣어져 **글자 겹침·자간 깨짐**. 편집 문단에서 반드시 제거(한글이 열 때 재계산). (원본 스킬 `fix_linesegarray.py`)
