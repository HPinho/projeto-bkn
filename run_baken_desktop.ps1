# Baken OS - Launcher Oficial do Desktop Shell Fluido em Flutter (120 FPS)

$root = "E:\projeto-bkn"
$ui_dir = "$root\ui\baken_shell"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "    INICIANDO BAKEN OS DESKTOP SHELL (FLUTTER AERO-QUANTUM 120 FPS)  " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

Set-Location $ui_dir
flutter run -d windows
