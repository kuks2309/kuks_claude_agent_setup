#!/usr/bin/env bash
# hwpx 스킬 렌더 검증 환경 부트스트랩 (Linux, 루트 불필요·멱등)
#
# 구성 요소:
#   1. 포터블 LibreOffice (~/.local/opt/libreoffice) — 시스템 LO 가 Java 확장을
#      못 쓰는 경우(libreoffice-java-common 없음)에도 루트 없이 동작
#   2. H2Orestart 확장 (HWP/HWPX import filter, Java 필요: default-jre)
#   3. Nanum 폰트 per-user 설치 + fontconfig 별칭 (휴먼명조→NanumMyeongjo 등)
#   4. poppler-utils(pdftoppm/pdftotext) 확인 — 없으면 안내만 (root 필요)
#
# 사용: bash setup_env.sh
set -euo pipefail

LO_BASE="$HOME/.local/opt/libreoffice"
LO_VER="25.8.7"
PROFILE_URI="file://$LO_BASE/profile"
H2O_URL="https://github.com/ebandal/H2Orestart/releases/latest/download/H2Orestart.oxt"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "== [1/4] LibreOffice =="
SOFFICE="$(ls "$LO_BASE"/opt/libreoffice*/program/soffice 2>/dev/null | tail -1 || true)"
if [ -z "$SOFFICE" ]; then
  echo "포터블 LibreOffice $LO_VER 다운로드 (~350MB)..."
  curl -sL -o "$TMP/lo.tar.gz" \
    "https://download.documentfoundation.org/libreoffice/stable/$LO_VER/deb/x86_64/LibreOffice_${LO_VER}_Linux_x86-64_deb.tar.gz"
  tar xzf "$TMP/lo.tar.gz" -C "$TMP"
  mkdir -p "$LO_BASE"
  for d in "$TMP"/LibreOffice_*/DEBS/*.deb; do dpkg -x "$d" "$LO_BASE"; done
  SOFFICE="$(ls "$LO_BASE"/opt/libreoffice*/program/soffice | tail -1)"
fi
"$SOFFICE" --version

echo "== [2/4] H2Orestart 확장 =="
if ! java -version >/dev/null 2>&1; then
  echo "WARN: Java(JRE) 없음. H2Orestart 는 Java 필요 → sudo apt install default-jre"
fi
UNOPKG="$(dirname "$SOFFICE")/unopkg"
if ! "$UNOPKG" list -env:UserInstallation="$PROFILE_URI" 2>/dev/null | grep -q H2Orestart; then
  curl -sL -o "$TMP/H2Orestart.oxt" "$H2O_URL"
  "$UNOPKG" add -env:UserInstallation="$PROFILE_URI" "$TMP/H2Orestart.oxt"
fi
"$UNOPKG" list -env:UserInstallation="$PROFILE_URI" | grep -A1 -i h2o | head -2 || true

echo "== [3/4] Nanum 폰트 + fontconfig 별칭 =="
if ! fc-list | grep -q NanumMyeongjo; then
  (cd "$TMP" && apt-get download fonts-nanum && dpkg -x fonts-nanum*.deb x \
    && mkdir -p ~/.local/share/fonts/nanum \
    && cp x/usr/share/fonts/truetype/nanum/*.ttf ~/.local/share/fonts/nanum/)
  fc-cache -f ~/.local/share/fonts >/dev/null
fi
FC_CONF="$HOME/.config/fontconfig/conf.d/99-hwp-korean-fonts.conf"
if [ ! -f "$FC_CONF" ]; then
  mkdir -p "$(dirname "$FC_CONF")"
  cat > "$FC_CONF" <<'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<!-- HWP/HWPX 전용 폰트 → Nanum 대체 (실폰트 설치 시 alias 무시됨) -->
<fontconfig>
  <alias binding="strong"><family>휴먼명조</family><prefer><family>NanumMyeongjo</family></prefer></alias>
  <alias binding="strong"><family>HY헤드라인M</family><prefer><family>NanumGothic</family></prefer></alias>
  <alias binding="strong"><family>한양중고딕</family><prefer><family>NanumGothic</family></prefer></alias>
  <alias binding="strong"><family>HY중고딕</family><prefer><family>NanumGothic</family></prefer></alias>
  <alias binding="strong"><family>함초롬바탕</family><prefer><family>NanumMyeongjo</family></prefer></alias>
  <alias binding="strong"><family>함초롬돋움</family><prefer><family>NanumGothic</family></prefer></alias>
  <alias binding="strong"><family>맑은 고딕</family><prefer><family>NanumGothic</family></prefer></alias>
  <alias binding="strong"><family>바탕</family><prefer><family>NanumMyeongjo</family></prefer></alias>
  <alias binding="strong"><family>돋움</family><prefer><family>NanumGothic</family></prefer></alias>
  <alias binding="strong"><family>굴림</family><prefer><family>NanumGothic</family></prefer></alias>
</fontconfig>
EOF
  fc-cache -f >/dev/null
fi
fc-match "휴먼명조"

echo "== [4/4] poppler-utils =="
if command -v pdftoppm >/dev/null; then
  echo "pdftoppm OK"
else
  echo "WARN: pdftoppm 없음 → sudo apt install poppler-utils (또는 pip install pypdfium2)"
fi

echo "SETUP_DONE"
