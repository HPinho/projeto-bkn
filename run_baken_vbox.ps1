# Baken OS - Compilador e Launcher Oficial para Oracle VirtualBox (UEFI Native)

$root = "C:\Projetos\projeto-bkn"
$gcc_bin = "$root\tools\w64devkit\bin"
$env:PATH = "$gcc_bin;" + $env:PATH

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$efi_src = "$root\boot\src\uefi_main.c"
$efi_out = "$root\build\iso_root\EFI\BOOT\BOOTX64.EFI"
$disk_img = "$root\build\baken_disk.img"
$disk_vdi = "$root\build\baken_disk.vdi"
$vm_name = "BakenOS"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      BAKEN OS - VIRTUALBOX EFI BUILD & LAUNCH PIPELINE          " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 0. Garante que os diretorios de build existem
Write-Host "`n[0/4] Criando diretorios de build..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$root\build\iso_root\EFI\BOOT" | Out-Null
New-Item -ItemType Directory -Force -Path "$root\build" | Out-Null
Write-Host "      OK: $root\build\iso_root\EFI\BOOT" -ForegroundColor Green

# 1. Compilação do Bootloader UEFI com GCC
Write-Host "`n[1/4] Compilando UEFI Bootloader (GCC)..." -ForegroundColor Yellow
if (-not (Test-Path $efi_src)) {
    Write-Host "      ERRO: $efi_src nao encontrado!" -ForegroundColor Red
    exit 1
}

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

# 2. Empacota a imagem de disco FAT32 ESP
Write-Host "`n[2/4] Criando imagem de disco FAT32 ESP..." -ForegroundColor Yellow
$py_script = "$root\tools\scripts\create_fat32_img.py"
python $py_script
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERRO: Falha ao criar imagem de disco." -ForegroundColor Red
    exit 1
}
Write-Host "      OK: $disk_img criado." -ForegroundColor Green

# 3. Converte .IMG para .VDI do VirtualBox
Write-Host "`n[3/4] Convertendo para disco VirtualBox VDI..." -ForegroundColor Yellow
if (-not (Test-Path $vbox)) {
    Write-Host "      ERRO: VirtualBox (VBoxManage.exe) nao encontrado em $vbox" -ForegroundColor Red
    exit 1
}

# Encerra instancias anteriores presas em segundo plano
& $vbox controlvm $vm_name poweroff 2>$null
Get-Process *virtualboxvm* -ErrorAction SilentlyContinue | Stop-Process -Force 2>$null
Start-Sleep -Milliseconds 500

# Desanexa e recria o VDI para evitar conflito de UUID
& $vbox storageattach $vm_name --storagectl "SATA" --port 0 --device 0 --type hdd --medium "none" 2>$null

if (Test-Path $disk_vdi) {
    & $vbox closemedium disk $disk_vdi --delete 2>$null
    if (Test-Path $disk_vdi) {
        Remove-Item $disk_vdi -Force -ErrorAction SilentlyContinue
    }
}

& $vbox convertfromraw $disk_img $disk_vdi --format VDI
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERRO: Falha ao converter disco para VDI." -ForegroundColor Red
    exit 1
}
Write-Host "      OK: $disk_vdi gerado com sucesso." -ForegroundColor Green

# 4. Configura VM e Inicializa
Write-Host "`n[4/4] Configurando VM '$vm_name' (Firmware EFI)..." -ForegroundColor Yellow
& $vbox modifyvm $vm_name --firmware efi --boot1 disk --boot2 none --memory 4096 --cpus 4 --vram 128 --graphicscontroller vboxsvga --mouse usbtablet
& $vbox storageattach $vm_name --storagectl "SATA" --port 0 --device 0 --type hdd --medium $disk_vdi

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "      INICIANDO BAKEN OS NO VIRTUALBOX (INTERFACE GRAFICA)       " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

$vbox_gui = "C:\Program Files\Oracle\VirtualBox\VirtualBox.exe"
Start-Process $vbox_gui -ArgumentList "--startvm", $vm_name
Write-Host "      OK: VM iniciada na interface grafica do VirtualBox." -ForegroundColor Green
