#!/usr/bin/env python3
"""
Baken OS - Gerador Oficial da Imagem ISO Soberana (baken_os.iso)
Gera uma ISO bootável UEFI com o Motor Gráfico Nativo e Área de Trabalho 1:1.
"""

import os
import sys
import struct
import subprocess
import shutil

ROOT_DIR = r"E:\projeto-bkn"
BUILD_DIR = os.path.join(ROOT_DIR, "build")
OUTPUT_ISO = os.path.join(BUILD_DIR, "baken_os.iso")
GCC_BIN = os.path.join(ROOT_DIR, "tools", "w64devkit", "bin")
VBOX_MANAGE = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"

def compile_kernel_modules():
    print("[1/4] Compilando Módulos Nativos do Baken OS em BOOTX64.EFI...")
    sources = [
        os.path.join(ROOT_DIR, "boot", "src", "uefi_main.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "gpu.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "sdf.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "font.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "bkn_font.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "icons.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "wallpaper.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "topbar.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "widgets.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "dock.c"),
        os.path.join(ROOT_DIR, "kernel", "src", "bkn_kernel_core.c"),
    ]
    out_efi = os.path.join(BUILD_DIR, "BOOTX64.EFI")
    
    env = os.environ.copy()
    env["PATH"] = GCC_BIN + ";" + env.get("PATH", "")
    
    cmd = [
        os.path.join(GCC_BIN, "gcc.exe"),
        "-O2", "-nostdlib", "-Wl,--subsystem,10",
        "-fshort-wchar", "-mabi=ms",
        "-e", "efi_main", "-shared",
        "-I", os.path.join(ROOT_DIR, "kernel", "include"),
        "-o", out_efi, *sources
    ]
    
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Erro ao compilar BOOTX64.EFI:\n{res.stderr}")
        return False
    
    print(f"  [OK] BOOTX64.EFI compilado ({os.path.getsize(out_efi)} bytes).")
    return True

def create_efi_fat_img(bootx64_bytes, size_mb=32):
    sector_size = 512
    total_sectors = (size_mb * 1024 * 1024) // sector_size
    img = bytearray(size_mb * 1024 * 1024)

    sectors_per_cluster = 4
    reserved_sectors = 1
    num_fats = 2
    root_entries = 512
    sectors_per_fat = 64

    bpb = bytearray(sector_size)
    bpb[0:3] = b"\xEB\x3C\x90"
    bpb[3:11] = b"MSWIN4.1"
    struct.pack_into("<H", bpb, 11, sector_size)
    bpb[13] = sectors_per_cluster
    struct.pack_into("<H", bpb, 14, reserved_sectors)
    bpb[16] = num_fats
    struct.pack_into("<H", bpb, 17, root_entries)
    struct.pack_into("<H", bpb, 19, 0)
    bpb[21] = 0xF8
    struct.pack_into("<H", bpb, 22, sectors_per_fat)
    struct.pack_into("<H", bpb, 24, 63)
    struct.pack_into("<H", bpb, 26, 255)
    struct.pack_into("<I", bpb, 28, 0)
    struct.pack_into("<I", bpb, 32, total_sectors)
    bpb[36] = 0x80
    bpb[38] = 0x29
    struct.pack_into("<I", bpb, 39, 0x4892A1F0)
    bpb[43:54] = b"BAKEN_ISO  "
    bpb[54:62] = b"FAT16   "
    bpb[510:512] = b"\x55\xAA"
    img[0:sector_size] = bpb

    fat1_offset = reserved_sectors * sector_size
    fat2_offset = fat1_offset + (sectors_per_fat * sector_size)

    cluster_size = sectors_per_cluster * sector_size
    file_clusters = (len(bootx64_bytes) + cluster_size - 1) // cluster_size

    fat_entries = [0xFFF8, 0xFFFF, 0xFFFF, 0xFFFF]
    start_c = 4
    for i in range(file_clusters):
        curr_c = start_c + i
        fat_entries.append(0xFFFF if i == file_clusters - 1 else curr_c + 1)

    fat_data = bytearray()
    for e in fat_entries:
        fat_data.extend(struct.pack("<H", e))

    img[fat1_offset : fat1_offset + len(fat_data)] = fat_data
    img[fat2_offset : fat2_offset + len(fat_data)] = fat_data

    root_dir_offset = (reserved_sectors + num_fats * sectors_per_fat) * sector_size
    root_dir_size = root_entries * 32
    data_start = root_dir_offset + root_dir_size

    def cluster_offset(c_num):
        return data_start + (c_num - 2) * cluster_size

    vol_entry = bytearray(32); vol_entry[0:11] = b"BAKEN_ISO  "; vol_entry[11] = 0x08
    img[root_dir_offset : root_dir_offset + 32] = vol_entry

    efi_entry = bytearray(32); efi_entry[0:11] = b"EFI        "; efi_entry[11] = 0x10
    struct.pack_into("<H", efi_entry, 26, 2)
    img[root_dir_offset + 32 : root_dir_offset + 64] = efi_entry

    c2 = cluster_offset(2)
    dot = bytearray(32); dot[0:11] = b".          "; dot[11] = 0x10; struct.pack_into("<H", dot, 26, 2)
    dotdot = bytearray(32); dotdot[0:11] = b"..         "; dotdot[11] = 0x10; struct.pack_into("<H", dotdot, 26, 0)
    boot_dir = bytearray(32); boot_dir[0:11] = b"BOOT       "; boot_dir[11] = 0x10; struct.pack_into("<H", boot_dir, 26, 3)
    img[c2:c2+32] = dot; img[c2+32:c2+64] = dotdot; img[c2+64:c2+96] = boot_dir

    c3 = cluster_offset(3)
    b_dot = bytearray(32); b_dot[0:11] = b".          "; b_dot[11] = 0x10; struct.pack_into("<H", b_dot, 26, 3)
    b_dotdot = bytearray(32); b_dotdot[0:11] = b"..         "; b_dotdot[11] = 0x10; struct.pack_into("<H", b_dotdot, 26, 2)
    file_entry = bytearray(32); file_entry[0:11] = b"BOOTX64 EFI"; file_entry[11] = 0x20
    struct.pack_into("<H", file_entry, 26, 4)
    struct.pack_into("<I", file_entry, 28, len(bootx64_bytes))
    img[c3:c3+32] = b_dot; img[c3+32:c3+64] = b_dotdot; img[c3+64:c3+96] = file_entry

    c4 = cluster_offset(4)
    img[c4 : c4 + len(bootx64_bytes)] = bootx64_bytes
    return img

def build_iso():
    print("[2/4] Construindo Imagem ISO com Catálogo de Boot El Torito UEFI...")
    with open(os.path.join(BUILD_DIR, "BOOTX64.EFI"), "rb") as f:
        bootx64_bytes = f.read()

    efi_fat = create_efi_fat_img(bootx64_bytes, size_mb=32)

    sector_size = 2048
    system_area = bytearray(16 * sector_size)

    pvd_sector = 16
    boot_catalog_sector = 17
    efi_img_sector = 18
    efi_img_sectors = (len(efi_fat) + sector_size - 1) // sector_size
    total_iso_sectors = efi_img_sector + efi_img_sectors + 10

    # 1. Primary Volume Descriptor (PVD)
    pvd = bytearray(sector_size)
    pvd[0] = 1 # Type: PVD
    pvd[1:6] = b"CD001"
    pvd[6] = 1 # Version
    pvd[40:72] = b"BAKEN_OS_LIVE                   "
    struct.pack_into("<I", pvd, 80, total_iso_sectors)
    struct.pack_into(">I", pvd, 84, total_iso_sectors)
    struct.pack_into("<H", pvd, 120, 1); struct.pack_into(">H", pvd, 122, 1)
    struct.pack_into("<H", pvd, 124, 1); struct.pack_into(">H", pvd, 126, 1)
    struct.pack_into("<H", pvd, 128, sector_size); struct.pack_into(">H", pvd, 130, sector_size)

    # 2. Boot Record Volume Descriptor (El Torito)
    brvd = bytearray(sector_size)
    brvd[0] = 0 # Type: Boot Record
    brvd[1:6] = b"CD001"
    brvd[6] = 1
    brvd[7:39] = b"EL TORITO SPECIFICATION\0\0\0\0\0\0\0\0\0"
    struct.pack_into("<I", brvd, 71, boot_catalog_sector)

    # 3. Volume Descriptor Set Terminator
    terminator = bytearray(sector_size)
    terminator[0] = 255
    terminator[1:6] = b"CD001"
    terminator[6] = 1

    # 4. Boot Catalog
    boot_catalog = bytearray(sector_size)
    boot_catalog[0] = 0x01 # Validation entry
    boot_catalog[1] = 0xEF # Platform ID: EFI
    boot_catalog[28:30] = b"\xAA\x55" # Key
    # Checksum validation
    chk = 0
    for i in range(0, 32, 2):
        chk = (chk + struct.unpack_from("<H", boot_catalog, i)[0]) & 0xFFFF
    struct.pack_into("<H", boot_catalog, 28, (-chk) & 0xFFFF)

    # Default / Initial Entry (EFI Boot Image)
    boot_entry_offset = 32
    boot_catalog[boot_entry_offset] = 0x88 # Bootable
    boot_catalog[boot_entry_offset + 1] = 0x00 # No emulation
    struct.pack_into("<H", boot_catalog, boot_entry_offset + 2, 0)
    boot_catalog[boot_entry_offset + 4] = 0xEF # System Type: EFI
    struct.pack_into("<H", boot_catalog, boot_entry_offset + 6, efi_img_sectors)
    struct.pack_into("<I", boot_catalog, boot_entry_offset + 8, efi_img_sector)

    # 5. Monta o arquivo final da ISO
    with open(OUTPUT_ISO, "wb") as f:
        f.write(system_area) # 0-15
        f.write(pvd)         # 16
        f.write(brvd)        # 17 (brvd aponta para catalog)
        f.write(terminator)  # 18
        f.write(boot_catalog)# 19
        # Padding até o setor de imagem EFI
        pad_sectors = efi_img_sector - 20
        if pad_sectors > 0:
            f.write(bytearray(pad_sectors * sector_size))
        f.write(efi_fat)
        # Padding final de alinhamento
        f.write(bytearray(4 * sector_size))

    print(f"  [OK] ISO Soberana gerada com sucesso ({os.path.getsize(OUTPUT_ISO)} bytes): {OUTPUT_ISO}")
    return True

def configure_virtualbox_iso():
    print("[3/4] Configurando VirtualBox para Inicializar a partir de baken_os.iso...")
    vm_name = "BakenOS "

    # 1. Desanexa discos antigos
    subprocess.run([VBOX_MANAGE, "storageattach", vm_name, "--storagectl", "SATA", "--port", "0", "--device", "0", "--type", "dvddrive", "--medium", "none"], capture_output=True)

    # 2. Conecta a nova ISO gerada
    cmd = [
        VBOX_MANAGE, "storageattach", vm_name,
        "--storagectl", "SATA",
        "--port", "0", "--device", "0",
        "--type", "dvddrive",
        "--medium", OUTPUT_ISO
    ]
    subprocess.run(cmd, check=True)

    # 3. Define ordem de boot prioritária para DVD
    subprocess.run([VBOX_MANAGE, "modifyvm", vm_name, "--boot1", "dvd", "--boot2", "disk"], check=True)
    print("  [OK] ISO conectada à VM como drive primário de boot.")

def main():
    if not compile_kernel_modules():
        sys.exit(1)
    if not build_iso():
        sys.exit(1)
    configure_virtualbox_iso()
    print("\n[SUCESSO] ISO do Baken OS criada e pronta para teste no VirtualBox!")

if __name__ == "__main__":
    main()
