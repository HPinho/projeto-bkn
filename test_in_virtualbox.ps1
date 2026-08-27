# Script de Teste Oficial do Baken OS no Oracle VirtualBox
param (
    [string]$VmName = "BakenOS "
)

$vbox_manage = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$vdi_path = "E:\projeto-bkn\build\baken_os.vdi"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "       INICIANDO BAKEN OS UEFI BOOT MANAGER NO VIRTUALBOX        " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

if (-not (Test-Path $vbox_manage)) {
    Write-Host "[!] VirtualBox nao encontrado em: $vbox_manage" -ForegroundColor Yellow
    exit 1
}

# Se a VM ja estiver ligada, avisa
$running = & $vbox_manage list runningvms
if ($running -match $VmName) {
    Write-Host "[*] A VM '$VmName' ja esta em execucao!" -ForegroundColor Green
    exit 0
}

Write-Host "[1/2] Verificando disco virtual de boot ($vdi_path)..." -ForegroundColor Yellow
if (-not (Test-Path $vdi_path)) {
    Write-Host "[*] Gerando disco virtual VDI..." -ForegroundColor Yellow
    python E:\projeto-bkn\tools\test_fat16_boot.py
}

Write-Host "[2/2] Iniciando a Maquina Virtual com UEFI..." -ForegroundColor Green
& $vbox_manage startvm $VmName --type gui

Write-Host "[OK] Baken OS Boot Manager iniciado no VirtualBox com sucesso!" -ForegroundColor Green
