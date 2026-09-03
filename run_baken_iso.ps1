# Baken OS - Launcher da ISO óptica UEFI de teste.
# A ISO é El Torito para VM; não é uma imagem híbrida para pendrive.

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$gcc_bin = "$root\tools\w64devkit\bin"
$env:PATH = "$gcc_bin;" + $env:PATH

$qemu = "C:\Program Files\qemu\qemu-system-x86_64.exe"
$ovmf = "$root\build\ovmf.fd"
$iso = "$root\build\baken_os.iso"
$efi_out = "$root\build\iso_root\EFI\BOOT\BOOTX64.EFI"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      BAKEN OS - GERADOR & LAUNCHER DE ISO BOOTÁVEL UEFI         " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 0. Garante que os diretórios de build existem
Write-Host "`n[0/3] Verificando estrutura de diretórios..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$root\build\iso_root\EFI\BOOT" | Out-Null
New-Item -ItemType Directory -Force -Path "$root\build" | Out-Null
Write-Host "      OK: $root\build\iso_root\EFI\BOOT" -ForegroundColor Green

# 1. Compilação do bootloader e do desktop nativo no mesmo EFI
Write-Host "`n[1/3] Compilando UEFI Bootloader (GCC)..." -ForegroundColor Yellow
& "$root\tools\build_uefi_desktop.ps1" -OutputPath $efi_out
if ($LASTEXITCODE -ne 0) { exit 1 }

# 2. Empacota o Sistema em ISO óptica UEFI
Write-Host "`n[2/3] Gerando ISO óptica UEFI pela rota nativa..." -ForegroundColor Yellow
$py_builder = "$root\tools\scripts\create_uefi_iso.py"
python $py_builder

$iso = "$root\build\baken_os.iso"
if (-not (Test-Path $iso)) {
    Write-Host "      ERRO: Falha ao gerar ISO óptica." -ForegroundColor Red
    exit 1
}
$iso_size_mb = [math]::Round(((Get-Item $iso).Length / 1MB), 2)
Write-Host "      OK: $iso ($iso_size_mb MB) gerada com sucesso." -ForegroundColor Green

# 3. Garante firmware UEFI (OVMF)
Write-Host "`n[3/3] Verificando firmware UEFI (OVMF)..." -ForegroundColor Yellow
$ovmf_src = "C:\Program Files\qemu\share\edk2-x86_64-code.fd"

if (-not (Test-Path $ovmf)) {
    if (Test-Path $ovmf_src) {
        Copy-Item $ovmf_src $ovmf -Force
        Write-Host "      OK: OVMF copiado de $ovmf_src" -ForegroundColor Green
    } else {
        Write-Host "      ERRO: OVMF não encontrado em $ovmf_src" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "      OK: OVMF presente em $ovmf" -ForegroundColor Green
}

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "      INICIANDO BAKEN OS NO QEMU (PRESSIONE CTRL+C PARA SAIR)    " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

$qemu_args = @(
    "-accel", "tcg,thread=multi",
    "-cpu", "max",
    "-drive", "if=pflash,format=raw,unit=0,readonly=on,file=$ovmf",
    "-drive", "media=cdrom,readonly=on,file=$iso",
    "-device", "qemu-xhci,id=xhci",
    "-device", "usb-tablet,bus=xhci.0",
    "-device", "usb-kbd,bus=xhci.0",
    "-m", "4G",
    "-smp", "1",
    "-device", "VGA,vgamem_mb=64,xres=1920,yres=1080",
    "-serial", "file:build/qemu_debug.log",
    "-name", "Baken OS MVP Desktop"
)

& $qemu @qemu_args
