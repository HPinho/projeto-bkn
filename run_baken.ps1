# Baken OS - Launcher do disco UEFI de teste.

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$gcc_bin = "$root\tools\w64devkit\bin"
$env:PATH = "$gcc_bin;" + $env:PATH

$qemu = "C:\Program Files\qemu\qemu-system-x86_64.exe"
$ovmf = "$root\build\ovmf.fd"
$disk = "$root\build\baken_disk.img"
$efi_out = "$root\build\iso_root\EFI\BOOT\BOOTX64.EFI"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      BAKEN OS - PIPELINE DO DISCO UEFI DE TESTE                 " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 0. Garante que os diretorios de build existem
Write-Host "`n[0/3] Criando diretorios de build..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$root\build\iso_root\EFI\BOOT" | Out-Null
New-Item -ItemType Directory -Force -Path "$root\build" | Out-Null
Write-Host "      OK: $root\build\iso_root\EFI\BOOT" -ForegroundColor Green

# 1. Compilacao do bootloader e do desktop nativo (um unico artefato EFI)
Write-Host "`n[1/3] Compilando UEFI Bootloader (GCC)..." -ForegroundColor Yellow
& "$root\tools\build_uefi_desktop.ps1" -OutputPath $efi_out
if ($LASTEXITCODE -ne 0) { exit 1 }

# 2. Empacota a imagem de disco FAT16 de teste.
Write-Host "`n[2/3] Criando imagem de disco FAT16 de teste..." -ForegroundColor Yellow
$py_script = "$root\tools\scripts\create_fat32_img.py"

if (-not (Test-Path $py_script)) {
    throw "Empacotador do disco UEFI ausente: $py_script"
} else {
    python $py_script
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      ERRO: Falha ao criar imagem de disco." -ForegroundColor Red
        exit 1
    }
    Write-Host "      OK: $disk criado." -ForegroundColor Green
}

# 3. Garante firmware UEFI (OVMF)
Write-Host "`n[3/3] Verificando firmware UEFI (OVMF)..." -ForegroundColor Yellow
$ovmf_src = "C:\Program Files\qemu\share\edk2-x86_64-code.fd"

if (-not (Test-Path $ovmf)) {
    if (Test-Path $ovmf_src) {
        Copy-Item $ovmf_src $ovmf -Force
        Write-Host "      OK: OVMF copiado de $ovmf_src" -ForegroundColor Green
    } else {
        Write-Host "      ERRO: OVMF nao encontrado em $ovmf_src" -ForegroundColor Red
        Write-Host "      Instale o QEMU: winget install SoftwareFreedomConservancy.QEMU" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "      OK: OVMF ja existe em $ovmf" -ForegroundColor Green
}

# 4. Verifica se a imagem de disco existe
if (-not (Test-Path $disk)) {
    Write-Host "`n      ERRO: Imagem de disco nao encontrada: $disk" -ForegroundColor Red
    Write-Host "      Execute o script de criacao de imagem manualmente." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "      INICIANDO BAKEN OS NO QEMU (PRESSIONE CTRL+C PARA SAIR)    " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

$qemu_args = @(
    "-accel", "tcg,thread=multi",
    "-cpu", "max",
    "-drive", "if=pflash,format=raw,unit=0,readonly=on,file=$ovmf",
    "-drive", "format=raw,file=$disk",
    "-device", "usb-ehci,id=ehci",
    "-device", "usb-tablet,bus=ehci.0",
    "-device", "usb-kbd,bus=ehci.0",
    "-m", "4G",
    "-smp", "1",
    "-vga", "std",
    "-global", "VGA.vgamem_mb=64",
    "-name", "Baken OS MVP Desktop"
)

& $qemu @qemu_args
