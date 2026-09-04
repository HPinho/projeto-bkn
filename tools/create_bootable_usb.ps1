# Baken OS - Utilitario para Criacao de Pendrive Bootavel UEFI
param(
    [string]$Drive = ""
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
$efiFile = Join-Path $root "build\iso_root\EFI\BOOT\BOOTX64.EFI"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "         BAKEN OS - CRIADOR DE PENDRIVE BOOTAVEL UEFI        " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Test-Path $efiFile)) {
    Write-Host "`n[!] Binario BOOTX64.EFI nao encontrado em: $efiFile" -ForegroundColor Yellow
    Write-Host "[*] Compilando Baken OS..." -ForegroundColor Cyan
    & "$root\tools\build_uefi_desktop.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRO] Falha ao compilar o sistema." -ForegroundColor Red
        exit 1
    }
}

if ([string]::IsNullOrWhiteSpace($Drive)) {
    Write-Host "`nUnidades detectadas no sistema:" -ForegroundColor Yellow
    Get-Volume | Where-Object { $_.DriveLetter } | Format-Table DriveLetter, FileSystemLabel, FileSystem, @{Name="Tamanho Total (GB)"; Expression={[math]::Round($_.Size/1GB, 2)}}
    $Drive = Read-Host "Digite a letra do seu pendrive (ex: E ou F)"
}

$letter = $Drive.Trim().TrimEnd(':').ToUpper()
if ([string]::IsNullOrWhiteSpace($letter) -or $letter.Length -ne 1) {
    Write-Host "[ERRO] Letra de unidade invalida: '$Drive'" -ForegroundColor Red
    exit 1
}

$targetDrive = "$letter`:"
if (-not (Test-Path "$targetDrive\")) {
    Write-Host "[ERRO] A unidade $targetDrive nao esta acessivel." -ForegroundColor Red
    exit 1
}

$vol = Get-Volume -DriveLetter $letter -ErrorAction SilentlyContinue
$fs = if ($vol) { $vol.FileSystem } else { "Desconhecido" }
$label = if ($vol) { $vol.FileSystemLabel } else { "Sem Nome" }

Write-Host "`nUnidade selecionada: $targetDrive\ [$label - $fs]" -ForegroundColor Cyan
if ($fs -ne "FAT32" -and $fs -ne "FAT") {
    Write-Host "[AVISO] O pendrive esta formatado como $fs. Para boot UEFI nativo, FAT32 e recomendado." -ForegroundColor Yellow
}

$ans = Read-Host "`nDeseja copiar os arquivos de boot do Baken OS para $targetDrive\ ? (S/N)"
if ($ans -notmatch '^[sSyY]') {
    Write-Host "Operacao cancelada." -ForegroundColor Gray
    exit 0
}

$destDir = Join-Path "$targetDrive\" "EFI\BOOT"
Write-Host "`n[1/2] Criando pasta $destDir..." -ForegroundColor Yellow
if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
}

Write-Host "[2/2] Copiando BOOTX64.EFI..." -ForegroundColor Yellow
Copy-Item -Path $efiFile -Destination (Join-Path $destDir "BOOTX64.EFI") -Force

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " [SUCESSO] Pendrive Bootavel Baken OS criado com sucesso!    " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Arquivo gravado:" -ForegroundColor Gray
Write-Host "  $destDir\BOOTX64.EFI" -ForegroundColor Gray
Write-Host "`nPassos para dar boot no seu PC:" -ForegroundColor Cyan
Write-Host "1. Conecte o pendrive com o computador desligado."
Write-Host "2. Ligue o PC e pressione a tecla do Menu de Boot (F12, F11, F8 ou F10)."
Write-Host "3. Escolha 'UEFI: [Nome do Pendrive]'."
Write-Host "4. Nota: Desative o Secure Boot na BIOS caso esteja ativado."
