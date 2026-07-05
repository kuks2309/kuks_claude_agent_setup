# install.ps1 — computer_use 우산 번들 전역 설치 (Windows, %USERPROFILE%\.claude). 멱등.
# 사용법:
#   ./install.ps1              # 파일 배치 + 의존성 설치 + preflight
#   ./install.ps1 -NoDeps      # 의존성 생략(파일 배치만)
#   ./install.ps1 -Check       # preflight 만
param([switch]$NoDeps, [switch]$Check)
$ErrorActionPreference = "Stop"
$Src  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Dest = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $env:USERPROFILE ".claude" }

Write-Host "[PREFLIGHT]"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "python 없음 — Python 3 설치 필요."; exit 1
}
Write-Host "  python OK"
if ($Check) { Write-Host "preflight only — done."; exit 0 }

if (-not $NoDeps) {
  Write-Host "[DEPS]"
  python -m pip install --user pyautogui pillow mss
}

Write-Host "[PLACE] -> $Dest"
New-Item -ItemType Directory -Force -Path $Dest, "$Dest\skills", "$Dest\agents" | Out-Null
Copy-Item "$Src\capture_screen.py"  "$Dest\capture_screen.py"  -Force
Copy-Item "$Src\computer_action.py" "$Dest\computer_action.py" -Force
foreach ($sk in @("capture-test", "computer-use")) {
  if (Test-Path "$Dest\skills\$sk") { Remove-Item "$Dest\skills\$sk" -Recurse -Force }
  Copy-Item "$Src\skills\$sk" "$Dest\skills\$sk" -Recurse -Force
}
Copy-Item "$Src\agents\computer-operator.md" "$Dest\agents\computer-operator.md" -Force

# CLAUDE.md 등록 (marker 중복방지)
$md = Join-Path $Dest "CLAUDE.md"
$marker = "kuks_agent_setup:computer_use"
if (-not (Test-Path $md)) { New-Item -ItemType File -Path $md | Out-Null }
if (Select-String -Path $md -SimpleMatch $marker -Quiet) {
  Write-Host "[CLAUDE.md] 등록 이미 존재 — 스킵"
} else {
  Add-Content -Path $md -Value ""
  Get-Content (Join-Path $Src "claude.snippet.md") | Add-Content -Path $md
  Write-Host "[CLAUDE.md] 등록 추가"
}
Write-Host "완료: computer_use → $Dest (적용은 세션 재시작 후). 다른 프로젝트에서 스킬 사용 가능."
