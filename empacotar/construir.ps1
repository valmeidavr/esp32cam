# Gera o instalador Windows do zero:
#
#   1. icone.ico            (gerar_icone.py)
#   2. dist\ClassificadorESP32CAM\   (PyInstaller)
#   3. dist\ClassificadorESP32CAM-Setup-x.y.z.exe   (Inno Setup)
#
# Uso:  powershell -ExecutionPolicy Bypass -File empacotar\construir.ps1
#
# Requisitos (uma vez so):
#   python -m pip install -r visao\requirements.txt pyinstaller pillow esptool
#   winget install JRSoftware.InnoSetup

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$iscc = @(
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    throw "Inno Setup nao encontrado. Instale com: winget install JRSoftware.InnoSetup"
}

Write-Host "`n[1/3] icone" -ForegroundColor Cyan
python empacotar\gerar_icone.py

Write-Host "`n[2/3] PyInstaller" -ForegroundColor Cyan
if (Test-Path dist\ClassificadorESP32CAM) { Remove-Item -Recurse -Force dist\ClassificadorESP32CAM }
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build empacotar\app.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

Write-Host "`n[3/3] Inno Setup" -ForegroundColor Cyan
& $iscc /Q empacotar\instalador.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou" }

$setup = Get-ChildItem dist\ClassificadorESP32CAM-Setup-*.exe | Sort-Object LastWriteTime | Select-Object -Last 1
Write-Host "`ninstalador pronto:" -ForegroundColor Green
Write-Host "  $($setup.FullName)  ($([math]::Round($setup.Length / 1MB, 1)) MB)"
