# Baken OS - Compilador e Launcher Oficial com Janela Adaptativa e Audio Intel HDA

$root = "C:\Projetos\projeto-bkn"
$gcc_bin = "$root\tools\w64devkit\bin"
$env:PATH = "$gcc_bin;" + $env:PATH

$qemu = "C:\Program Files\qemu\qemu-system-x86_64.exe"
$ovmf = "$root\build\ovmf.fd"
$disk = "$root\build\baken_disk.img"
$efi_src = "$root\boot\src\uefi_main.c"
$efi_out = "$root\build\iso_root\EFI\BOOT\BOOTX64.EFI"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      BAKEN OS - SOBERANO BUILD PIPELINE                         " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 0. Garante que os diretorios de build existem
Write-Host "`n[0/3] Criando diretorios de build..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$root\build\iso_root\EFI\BOOT" | Out-Null
New-Item -ItemType Directory -Force -Path "$root\build" | Out-Null
Write-Host "      OK: $root\build\iso_root\EFI\BOOT" -ForegroundColor Green

# 1. Compilacao com GCC Nativo para Subsystem 10 (EFI Application)
Write-Host "`n[1/3] Compilando UEFI Bootloader (GCC)..." -ForegroundColor Yellow

if (-not (Test-Path $efi_src)) {
    Write-Host "      AVISO: $efi_src nao encontrado - pulando compilacao GCC." -ForegroundColor DarkYellow
} else {
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
        Write-Host "      ERRO: Falha na compilacao GCC (codigo $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
    Write-Host "      OK: $efi_out gerado." -ForegroundColor Green
}

# 2. Empacota a imagem de disco FAT32
Write-Host "`n[2/3] Criando imagem de disco FAT32..." -ForegroundColor Yellow
$py_script = "$root\tools\scripts\create_fat32_img.py"

if (-not (Test-Path $py_script)) {
    Write-Host "      AVISO: create_fat32_img.py nao encontrado - pulando." -ForegroundColor DarkYellow
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
    "-drive", "if=pflash,format=raw,unit=0,readonly=on,file=$ovmf",
    "-drive", "format=raw,file=$disk",
    "-device", "usb-ehci,id=ehci",
    "-device", "usb-tablet,bus=ehci.0",
    "-device", "usb-kbd,bus=ehci.0",
    "-netdev", "user,id=net0",
    "-device", "virtio-net-pci,netdev=net0",
    "-m", "4G",
    "-smp", "4",
    "-vga", "std",
    "-name", "Baken OS - Sovereign Quantum Desktop"
)

& $qemu @qemu_args
