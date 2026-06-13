# 打包離線排盤執行檔（PyInstaller 單一 .exe）
# 用法：在 repo 根目錄執行  powershell -ExecutionPolicy Bypass -File build/build_exe.ps1
# 需求：一個已安裝 pyinstaller 的 Python（建議 3.11）。可用 $env:JFLY_PY 指定 python.exe。

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = $env:JFLY_PY
if (-not $py) { $py = (Get-Command python).Source }

Write-Host "使用 Python：$py"
& $py -m PyInstaller --noconfirm --onefile `
    --name jingfang-liuyao-paipan `
    --paths . `
    --collect-submodules engine `
    --add-data "$root\references\solar_terms_2020_2040.csv;references" `
    --distpath dist `
    --workpath build/pyi-work `
    --specpath build `
    app/paipan.py

Write-Host "完成：$root\dist\jingfang-liuyao-paipan.exe"
