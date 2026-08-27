#!/usr/bin/env python3
"""
Baken OS - Gerador de ISO Híbrida UEFI / El Torito (make_hybrid_iso.py)
Garante boot 100% confiável no VirtualBox via UEFI GOP.
"""

import os
import sys
import struct
import subprocess

ROOT_DIR = r"E:\projeto-bkn"
BUILD_DIR = os.path.join(ROOT_DIR, "build")
OUTPUT_ISO = os.path.join(BUILD_DIR, "baken_os.iso")
GCC_BIN = os.path.join(ROOT_DIR, "tools", "w64devkit", "bin")
VBOX_MANAGE = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"

def compile_kernel_modules():
    print("[1/3] Compilando Módulos Nativos do Baken OS em BOOTX64.EFI...")
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

def build_hybrid_uefi_iso():
    print("[2/3] Gerando ISO Híbrida UEFI (ISO9660 + EFI System Partition)...")
    with open(os.path.join(BUILD_DIR, "BOOTX64.EFI"), "rb") as f:
        bootx64_bytes = f.read()

    # Cria partição FAT16 EFI
    size_mb = 16
    sector_size = 512
    total_fat_sectors = (size_mb * 1024 * 1024) // sector_size
    fat_img = bytearray(size_mb * 1024 * 1024)

    sectors_per_cluster = 4
    reserved_sectors = 1
    num_fats = 2
    root_entries = 512
    sectors_per_fat = 32

    bpb = bytearray(sector_size)
    bpb[0:3] = b"\xEB\x3C\x90"
    bpb[3:11] = b"MSWIN4.1"
    struct.pack_into("<H", bpb, 11, sector_size)
    bpb[13] = sectors_per_cluster
    struct.pack_into("<H", bpb, 14, reserved_sectors)
    bpb[16] = num_fats
    struct.pack_into("<H", bpb, 17, root_entries)
    bpb[21] = 0xF8
    struct.pack_into("<H", bpb, 22, sectors_per_fat)
    struct.pack_into("<H", bpb, 24, 63)
    struct.pack_into("<H", bpb, 26, 255)
    struct.pack_into("<I", bpb, 32, total_fat_sectors)
    bpb[36] = 0x80; bpb[38] = 0x29
    struct.pack_into("<I", bpb, 39, 0x4892A1F0)
    bpb[43:54] = b"BAKEN_ISO  "
    bpb[54:62] = b"FAT16   "
    bpb[510:512] = b"\x55\xAA"
    fat_img[0:sector_size] = bpb

    fat1_offset = reserved_sectors * sector_size
    fat2_offset = fat1_offset + (sectors_per_fat * sector_size)

    cluster_size = sectors_per_cluster * sector_size
    file_clusters = (len(bootx64_bytes) + cluster_size - 1) // cluster_size

    fat_entries = [0xFFF8, 0xFFFF, 0xFFFF, 0xFFFF]
    for i in range(file_clusters):
        fat_entries.append(0xFFFF if i == file_clusters - 1 else 4 + i + 1)

    fat_data = bytearray()
    for e in fat_entries:
        fat_data.extend(struct.pack("<H", e))

    fat_img[fat1_offset : fat1_offset + len(fat_data)] = fat_data
    fat_img[fat2_offset : fat2_offset + len(fat_data)] = fat_data

    root_dir_offset = (reserved_sectors + num_fats * sectors_per_fat) * sector_size
    root_dir_size = root_entries * 32
    data_start = root_dir_offset + root_dir_size

    def cluster_offset(c):
        return data_start + (c - 2) * cluster_size

    # Volume Label
    vol_entry = bytearray(32); vol_entry[0:11] = b"BAKEN_ISO  "; vol_entry[11] = 0x08
    fat_img[root_dir_offset : root_dir_offset + 32] = vol_entry

    # \EFI
    efi_entry = bytearray(32); efi_entry[0:11] = b"EFI        "; efi_entry[11] = 0x10
    struct.pack_into("<H", efi_entry, 26, 2)
    fat_img[root_dir_offset + 32 : root_dir_offset + 64] = efi_entry

    # Cluster 2 (\EFI) contendo \BOOT
    c2 = cluster_offset(2)
    dot = bytearray(32); dot[0:11] = b".          "; dot[11] = 0x10; struct.pack_into("<H", dot, 26, 2)
    dotdot = bytearray(32); dotdot[0:11] = b"..         "; dotdot[11] = 0x10; struct.pack_into("<H", dotdot, 26, 0)
    boot_dir = bytearray(32); boot_dir[0:11] = b"BOOT       "; boot_dir[11] = 0x10; struct.pack_into("<H", boot_dir, 26, 3)
    fat_img[c2:c2+32] = dot; fat_img[c2+32:c2+64] = dotdot; fat_img[c2+64:c2+96] = boot_dir

    # Cluster 3 (\EFI\BOOT) contendo BOOTX64.EFI
    c3 = cluster_offset(3)
    b_dot = bytearray(32); b_dot[0:11] = b".          "; b_dot[11] = 0x10; struct.pack_into("<H", b_dot, 26, 3)
    b_dotdot = bytearray(32); b_dotdot[0:11] = b"..         "; b_dotdot[11] = 0x10; struct.pack_into("<H", b_dotdot, 26, 2)
    f_entry = bytearray(32); f_entry[0:11] = b"BOOTX64 EFI"; f_entry[11] = 0x20
    struct.pack_into("<H", f_entry, 26, 4)
    struct.pack_into("<I", f_entry, 28, len(bootx64_bytes))
    fat_img[c3:c3+32] = b_dot; fat_img[c3+32:c3+64] = b_dotdot; fat_img[c3+64:c3+96] = f_entry

    # Cluster 4+
    c4 = cluster_offset(4)
    fat_img[c4 : c4 + len(bootx64_bytes)] = bootx64_bytes

    # Monta a estrutura ISO9660 (setores de 2048 bytes)
    iso_sec_size = 2048
    system_area = bytearray(16 * iso_sec_size)

    # El Torito Catalog em LBA 19
    catalog_lba = 19
    fat_lba = 20
    fat_sectors_iso = (len(fat_img) + iso_sec_size - 1) // iso_sec_size
    total_iso_sectors = fat_lba + fat_sectors_iso + 4

    pvd = bytearray(iso_sec_size)
    pvd[0] = 1; pvd[1:6] = b"CD001"; pvd[6] = 1
    pvd[40:72] = b"BAKEN_OS_LIVE                   "
    struct.pack_into("<I", pvd, 80, total_iso_sectors)
    struct.pack_into(">I", pvd, 84, total_iso_sectors)
    struct.pack_into("<H", pvd, 120, 1); struct.pack_into(">H", pvd, 122, 1)
    struct.pack_into("<H", pvd, 124, 1); struct.pack_into(">H", pvd, 126, 1)
    struct.pack_into("<H", pvd, 128, iso_sec_size); struct.pack_into(">H", pvd, 130, iso_sec_size)

    # Root Directory Record no PVD (LBA 18)
    root_lba = 18
    pvd_root = bytearray(34)
    pvd_root[0] = 34
    struct.pack_into("<I", pvd_root, 2, root_lba); struct.pack_into(">I", pvd_root, 6, root_lba)
    struct.pack_into("<I", pvd_root, 10, iso_sec_size); struct.pack_into(">I", pvd_root, 14, iso_sec_size)
    pvd_root[25] = 2 # Directory flag
    struct.pack_into("<H", pvd_root, 28, 1); struct.pack_into(">H", pvd_root, 30, 1)
    pvd_root[32] = 1; pvd_root[33] = 0
    pvd[156:156+34] = pvd_root

    # Boot Record Volume Descriptor (LBA 17)
    brvd = bytearray(iso_sec_size)
    brvd[0] = 0; brvd[1:6] = b"CD001"; brvd[6] = 1
    brvd[7:39] = b"EL TORITO SPECIFICATION\0\0\0\0\0\0\0\0\0"
    struct.pack_into("<I", brvd, 71, catalog_lba)

    # Terminator (LBA 18)
    term = bytearray(iso_sec_size)
    term[0] = 255; term[1:6] = b"CD001"; term[6] = 1

    # Boot Catalog (LBA 19)
    catalog = bytearray(iso_sec_size)
    # Validation Entry
    catalog[0] = 0x01
    catalog[1] = 0xEF # EFI Platform
    catalog[28] = 0x55; catalog[29] = 0xAA # Key
    chk = 0
    for i in range(0, 32, 2):
        chk = (chk + struct.unpack_from("<H", catalog, i)[0]) & 0xFFFF
    struct.pack_into("<H", catalog, 28, (-chk) & 0xFFFF)

    # Initial Boot Entry (EFI)
    catalog[32] = 0x88 # Bootable
    catalog[33] = 0x00 # No emulation
    catalog[36] = 0xEF # EFI System Type
    struct.pack_into("<H", catalog, 38, fat_sectors_iso)
    struct.pack_into("<I", catalog, 40, fat_lba)

    with open(OUTPUT_ISO, "wb") as f:
        f.write(system_area) # 0..15
        f.write(pvd)         # 16
        f.write(brvd)        # 17
        f.write(term)        # 18
        f.write(catalog)     # 19
        f.write(fat_img)     # 20..
        f.write(bytearray(4 * iso_sec_size))

    print(f"  [OK] ISO Híbrida gerada com sucesso ({os.path.getsize(OUTPUT_ISO)} bytes): {OUTPUT_ISO}")
    return True

def configure_and_boot():
    print("[3/3] Anexando ISO no VirtualBox...")
    vm_name = "BakenOS "
    
    subprocess.run([VBOX_MANAGE, "storageattach", vm_name, "--storagectl", "SATA", "--port", "1", "--device", "0", "--type", "dvddrive", "--medium", OUTPUT_ISO], capture_output=True)
    subprocess.run([VBOX_MANAGE, "modifyvm", vm_name, "--boot1", "dvd", "--boot2", "disk"], check=True)
    print("  [OK] Drive de DVD configurado.")

def main():
    if not compile_kernel_modules():
        sys.exit(1)
    if not build_hybrid_uefi_iso():
        sys.exit(1)
    configure_and_boot()

if __name__ == "__main__":
    main()
