# Baken OS - Launcher Oficial para Inicialização via Imagem ISO Bootável UEFI
# Compatível com QEMU, VirtualBox, VMware e Gravação em Pendrive USB (Rufus / Ventoy / BalenaEtcher)

$root = "C:\Projetos\projeto-bkn"
$gcc_bin = "$root\tools\w64devkit\bin"
$env:PATH = "$gcc_bin;" + $env:PATH

$qemu = "C:\Program Files\qemu\qemu-system-x86_64.exe"
$ovmf = "$root\build\ovmf.fd"
$iso = "$root\build\baken_os.iso"
$efi_src = "$root\boot\src\uefi_main.c"
$efi_out = "$root\build\iso_root\EFI\BOOT\BOOTX64.EFI"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      BAKEN OS - GERADOR & LAUNCHER DE ISO BOOTÁVEL UEFI         " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 0. Garante que os diretórios de build existem
Write-Host "`n[0/3] Verificando estrutura de diretórios..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$root\build\iso_root\EFI\BOOT" | Out-Null
New-Item -ItemType Directory -Force -Path "$root\build" | Out-Null
Write-Host "      OK: $root\build\iso_root\EFI\BOOT" -ForegroundColor Green

# 1. Compilação do Bootloader UEFI com GCC
Write-Host "`n[1/3] Compilando UEFI Bootloader (GCC)..." -ForegroundColor Yellow
$gcc_args = @(
    "-Wall", "-Wextra", "-nostdlib", "-shared",
    "-Wl,--subsystem,10",
    "-Wl,--image-base,0x10000000",
    "-Wl,-e,efi_main",
    "-o", $efi_out,
    $efi_src
)
& "$gcc_bin\gcc.exe" @gcc_args

if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERRO: Falha na compilação do bootloader EFI." -ForegroundColor Red
    exit 1
}
Write-Host "      OK: $efi_out gerado." -ForegroundColor Green

# 2. Gera a Imagem ISO Bootável Híbrida El-Torito
Write-Host "`n[2/3] Gerando imagem ISO bootável UEFI..." -ForegroundColor Yellow
$py_script = "$root\tools\scripts\create_uefi_iso.py"
python $py_script

if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERRO: Falha ao gerar arquivo ISO." -ForegroundColor Red
    exit 1
}
$iso_size_mb = [math]::Round(((Get-Item $iso).Length / 1MB), 2)
Write-Host "      OK: $iso ($iso_size_mb MB) gerado com sucesso." -ForegroundColor Green

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
Write-Host "      INICIANDO BAKEN OS VIA ISO NO QEMU (CTRL+C PARA SAIR)      " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

$qemu_args = @(
    "-accel", "tcg,thread=multi",
    "-cpu", "max",
    "-drive", "if=pflash,format=raw,unit=0,readonly=on,file=$ovmf",
    "-cdrom", $iso,
    "-device", "usb-ehci,id=ehci",
    "-device", "usb-tablet,bus=ehci.0",
    "-device", "usb-kbd,bus=ehci.0",
    "-m", "4G",
    "-smp", "4",
    "-vga", "std",
    "-global", "VGA.vgamem_mb=64",
    "-name", "Baken OS - Sovereign Bootable ISO"
)

& $qemu @qemu_args
