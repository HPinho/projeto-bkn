# Baken OS - Launcher Oficial do Desktop Shell Fluido em Flutter (120 FPS)

$root = "c:\Projetos\projeto-bkn"
$exe_path = "$root\ui\baken_shell\build\windows\x64\runner\Release\baken_shell.exe"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "    INICIANDO BAKEN OS DESKTOP SHELL (GPU ACCELERATED 120 FPS)   " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

if (Test-Path $exe_path) {
    Write-Host "[OK] Executando binario nativo Release em: $exe_path" -ForegroundColor Green
    Start-Process -FilePath $exe_path
} else {
    Write-Host "[...] Compilando e iniciando via Flutter..." -ForegroundColor Yellow
    Set-Location "$root\ui\baken_shell"
    flutter run -d windows
}

