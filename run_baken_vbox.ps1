# Baken OS - Launcher isolado para Oracle VirtualBox (UEFI Native).
# Ele nunca procura, desliga ou reutiliza uma VM pessoal chamada "BakenOS".

param(
    [string]$VmName = "BakenOS-MVP-Test"
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$gcc_bin = "$root\tools\w64devkit\bin"
$env:PATH = "$gcc_bin;" + $env:PATH

$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
$efi_out = "$root\build\iso_root\EFI\BOOT\BOOTX64.EFI"
$disk_img = "$root\build\baken_disk.img"
$disk_vdi = "$root\build\baken_disk.vdi"
$iso = "$root\build\baken_os.iso"
$vm_name = $VmName

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      BAKEN OS - VIRTUALBOX EFI BUILD & LAUNCH PIPELINE          " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 0. Garante que os diretorios de build existem
Write-Host "`n[0/4] Criando diretorios de build..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$root\build\iso_root\EFI\BOOT" | Out-Null
New-Item -ItemType Directory -Force -Path "$root\build" | Out-Null
Write-Host "      OK: $root\build\iso_root\EFI\BOOT" -ForegroundColor Green

# 1. Compilação do bootloader e do desktop nativo no mesmo EFI
Write-Host "`n[1/4] Compilando UEFI Bootloader (GCC)..." -ForegroundColor Yellow
& "$root\tools\build_uefi_desktop.ps1" -OutputPath $efi_out
if ($LASTEXITCODE -ne 0) { exit 1 }

# 2. Empacota o mesmo EFI e cria o disco ESP gravável usado pelo VirtualBox
Write-Host "`n[2/4] Gerando ISO e Disco ESP do desktop nativo..." -ForegroundColor Yellow
$py_builder = "$root\tools\scripts\create_uefi_iso.py"
python $py_builder
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERRO: Falha ao empacotar ISO UEFI." -ForegroundColor Red
    exit 1
}
$disk_builder = "$root\tools\scripts\create_fat32_img.py"
python $disk_builder
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERRO: Falha ao criar disco ESP de teste." -ForegroundColor Red
    exit 1
}
Write-Host "      OK: $disk_img e $iso gerados com sucesso." -ForegroundColor Green

# 3. Converte .IMG para .VDI do VirtualBox
Write-Host "`n[3/4] Convertendo para disco VirtualBox VDI..." -ForegroundColor Yellow
if (-not (Test-Path $vbox)) {
    Write-Host "      ERRO: VirtualBox (VBoxManage.exe) nao encontrado em $vbox" -ForegroundColor Red
    exit 1
}

# Usa somente a VM de teste escolhida explicitamente.
$vms_list = & $vbox list vms
if ($vms_list -match ('"' + [regex]::Escape($vm_name) + '"')) {
    Write-Host "      OK: VM de teste existente detectada: '$vm_name'" -ForegroundColor Green
} else {
    Write-Host "      Criando VM de teste isolada '$vm_name'..." -ForegroundColor Yellow
    & $vbox createvm --name $vm_name --ostype "Linux_64" --register
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      ERRO: Falha ao criar VM de teste." -ForegroundColor Red
        exit 1
    }
    & $vbox storagectl $vm_name --name "SATA" --add sata --controller IntelAhci
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      ERRO: Falha ao criar controladora SATA da VM de teste." -ForegroundColor Red
        exit 1
    }
}

# Encerra somente a VM de teste, se ela estiver em execução.
& $vbox controlvm $vm_name poweroff 2>$null
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

# 4. Configura VM e Inicializa em Alta Resolução EFI
Write-Host "`n[4/4] Configurando VM '$vm_name' (Firmware EFI + Alta Definicao)..." -ForegroundColor Yellow
& $vbox modifyvm $vm_name --firmware efi --boot1 disk --boot2 none --memory 4096 --cpus 1 --vram 128 --graphicscontroller vboxsvga --mouse usbtablet
& $vbox setextradata $vm_name "VBoxInternal2/EfiGraphicsResolution" "1280x800" 2>$null
& $vbox storageattach $vm_name --storagectl "SATA" --port 0 --device 0 --type hdd --medium $disk_vdi

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "      INICIANDO BAKEN OS NO VIRTUALBOX (INTERFACE GRAFICA)       " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

$vbox_gui = "C:\Program Files\Oracle\VirtualBox\VirtualBox.exe"
Start-Process $vbox_gui -ArgumentList "--startvm", $vm_name
Write-Host "      OK: VM iniciada na interface grafica do VirtualBox." -ForegroundColor Green
