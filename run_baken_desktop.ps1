# Baken OS - Launcher Oficial do Desktop Shell Fluido em Flutter (120 FPS)

$root = $PSScriptRoot
$exe_path = "$root\ui\baken_shell\build\windows\x64\runner\Release\baken_shell.exe"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "    INICIANDO BAKEN OS DESKTOP SHELL (GPU ACCELERATED 120 FPS)   " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# Compila a DLL nativa libbkn com os servicos do Kernel BKN
$gcc_bin = "$root\tools\w64devkit\bin"
$env:PATH = "$gcc_bin;" + $env:PATH
New-Item -ItemType Directory -Force -Path "$root\build" | Out-Null
& "$gcc_bin\gcc.exe" -shared -O3 -o "$root\build\libbkn.dll" "$root\libbkn\src\bkn_bridge.c"

$release_dir = "$root\ui\baken_shell\build\windows\x64\runner\Release"
if (Test-Path $release_dir) {
    Copy-Item "$root\build\libbkn.dll" "$release_dir\libbkn.dll" -Force -ErrorAction SilentlyContinue
}

if (Test-Path $exe_path) {
    Write-Host "[OK] Executando binario nativo conectado a libbkn.dll: $exe_path" -ForegroundColor Green
    Start-Process -FilePath $exe_path
} else {
    Write-Host "[...] Compilando e iniciando via Flutter..." -ForegroundColor Yellow
    Set-Location "$root\ui\baken_shell"
    flutter run -d windows
}

