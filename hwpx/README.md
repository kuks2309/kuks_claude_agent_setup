# hwpx — 한글(HWP/HWPX) 문서 생성·편집 + PDF 렌더 검증 번들

아래 한글 HWPX 문서를 양식(템플릿) 치환으로 생성·편집하고, **완료 선언 전 PDF→PNG 렌더를
눈으로 검토(서식·글자 깨짐·디자인)하는 검증 루프**를 강제하는 Claude Code 스킬 번들.

원류: [kuks_claude_setup/hwp스킬](https://github.com/kuks2309/kuks_claude_setup/tree/master/hwp%EC%8A%A4%ED%82%AC) (원본 gonggong_hwpxskills + Windows supplement) 의 v3 번들 이식판.

## 설치

```bash
cd hwpx
./install.sh              # 파일 배치 + 의존성(포터블 LibreOffice ~350MB 다운로드 가능) + preflight
./install.sh --no-deps    # 파일 배치만 (의존성은 나중에 skills/hwpx/scripts/setup_env.sh)
./install.sh --check      # 환경 점검만
./install.sh --status     # 설치본 낡음 점검
```

배치: `skill/` → `~/.claude/skills/hwpx/`, `claude.snippet.md` → `~/.claude/CLAUDE.md` (marker `kuks_agent_setup:hwpx`, 중복 방지). 설치 기록은 `~/.claude/INSTALLED.md`.

## 구성

| 경로 | 내용 |
| --- | --- |
| `skill/SKILL.md` | 워크플로 본문 — 양식 선택 정책 + ZIP-level 치환 + **렌더 시각 검증 루프(최우선 규칙)** |
| `skill/scripts/` | `render_verify.py`(원커맨드 루프), `render_pdf.py`(LibreOffice+H2Orestart), `pdf_to_png.py`, `remove_paragraphs.py`(미사용 플레이스홀더 문단 삭제), `fix_linesegarray.py`, `fix_namespaces.py`, `setup_env.sh`(환경 부트스트랩, 루트 불필요) |
| `skill/references/` | `render-verify.md`(검증 루프·체크리스트·Linux 한계·Windows 부록), `hwp-render-gotchas.md`(렌더 함정 5종), 보고서/공문 스타일 가이드, XML 내부 구조 |
| `skill/assets/` | 공공기관 보고서 양식 `report-template.hwpx` |

## 의존 환경

- **Linux** (기본): `setup_env.sh` 가 루트 없이 구성 — 포터블 LibreOffice 25.8 + [H2Orestart](https://github.com/ebandal/H2Orestart)(HWPX import, **Java/JRE 필요**) + Nanum 폰트 + fontconfig 별칭. 시스템 권장 패키지: `poppler-utils`, `default-jre`.
- **Windows** (정밀 검증): 한컴오피스 + `pip install pyhwpx pywin32` — `skill/references/render-verify.md` 부록.
- LibreOffice 렌더는 한컴 한글과 근사치: 글자 깨짐·치환 오류·서식·디자인 검증에 유효하나, 원본 폰트 부재 시 페이지 경계가 실제 한글과 다를 수 있다.

## 업데이트

번들 저장소 pull 후 `./install.sh --status` 로 낡음 여부 확인 → 재설치 권장 시 `./install.sh` 재실행 (멱등).
