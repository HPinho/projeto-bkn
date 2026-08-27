#!/usr/bin/env python3
"""
Baken OS - Compilador Modular Completo da Interface Nativa Soberana
"""

import os
import sys
import struct
import subprocess

ROOT_DIR = r"E:\projeto-bkn"
BUILD_DIR = os.path.join(ROOT_DIR, "build")
RAW_IMG = os.path.join(BUILD_DIR, "baken_os.raw")
VDI_IMG = os.path.join(BUILD_DIR, "baken_os.vdi")
GCC_BIN = os.path.join(ROOT_DIR, "tools", "w64devkit", "bin")
VBOX_MANAGE = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"

def compile_kernel_and_bootloader():
    print("[1/4] Compilando Módulos Nativos do Baken OS (GPU, SDF, Fontes, Wallpaper, Topbar, Widgets, Dock)...")
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
    
    print(f"  [OK] BOOTX64.EFI compilado com sucesso ({os.path.getsize(out_efi)} bytes).")
    return True

def create_fat16_mbr_disk():
    print("[2/4] Gerando disco MBR com particao EFI FAT16 (64 MB)...")
    
    with open(os.path.join(BUILD_DIR, "BOOTX64.EFI"), "rb") as f:
        bootx64_data = f.read()
        
    sector_size = 512
    disk_size_mb = 64
    total_sectors = (disk_size_mb * 1024 * 1024) // sector_size
    
    disk = bytearray(disk_size_mb * 1024 * 1024)
    
    # 1. MBR (LBA 0)
    part_start_lba = 2048
    part_sectors = total_sectors - part_start_lba
    
    mbr_part1 = struct.pack(
        "<BBBBBBBBII",
        0x80, 0x20, 0x21, 0x00, 0xEF, 0xFE, 0xFF, 0xFF,
        part_start_lba, part_sectors
    )
    disk[446:446+16] = mbr_part1
    disk[510:512] = b"\x55\xAA"
    
    # 2. FAT16 BPB
    p_offset = part_start_lba * sector_size
    sectors_per_cluster = 4
    reserved_sectors = 1
    num_fats = 2
    root_entries = 512
    sectors_per_fat = 128
    
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
    struct.pack_into("<I", bpb, 28, part_start_lba)
    struct.pack_into("<I", bpb, 32, part_sectors)
    bpb[36] = 0x80
    bpb[38] = 0x29
    struct.pack_into("<I", bpb, 39, 0x4892A1F0)
    bpb[43:54] = b"BAKEN_BOOT "
    bpb[54:62] = b"FAT16   "
    bpb[510:512] = b"\x55\xAA"
    
    disk[p_offset : p_offset + sector_size] = bpb
    
    # 3. FAT 1 & 2
    fat1_offset = p_offset + (reserved_sectors * sector_size)
    fat2_offset = fat1_offset + (sectors_per_fat * sector_size)
    
    cluster_size = sectors_per_cluster * sector_size
    file_clusters = (len(bootx64_data) + cluster_size - 1) // cluster_size
    
    fat_entries_16 = [0xFFF8, 0xFFFF, 0xFFFF, 0xFFFF]
    start_c = 4
    for i in range(file_clusters):
        curr_c = start_c + i
        if i == file_clusters - 1:
            fat_entries_16.append(0xFFFF)
        else:
            fat_entries_16.append(curr_c + 1)
            
    fat_data = bytearray()
    for e in fat_entries_16:
        fat_data.extend(struct.pack("<H", e))
        
    disk[fat1_offset : fat1_offset + len(fat_data)] = fat_data
    disk[fat2_offset : fat2_offset + len(fat_data)] = fat_data
    
    # 4. Diretórios
    root_dir_offset = p_offset + (reserved_sectors + num_fats * sectors_per_fat) * sector_size
    root_dir_size = root_entries * 32
    data_start = root_dir_offset + root_dir_size
    
    def cluster_offset(c_num):
        return data_start + (c_num - 2) * cluster_size
        
    # Root
    vol_entry = bytearray(32); vol_entry[0:11] = b"BAKEN_BOOT "; vol_entry[11] = 0x08
    disk[root_dir_offset : root_dir_offset + 32] = vol_entry
    
    efi_entry = bytearray(32); efi_entry[0:11] = b"EFI        "; efi_entry[11] = 0x10
    struct.pack_into("<H", efi_entry, 26, 2)
    disk[root_dir_offset + 32 : root_dir_offset + 64] = efi_entry
    
    # Cluster 2: \EFI
    c2 = cluster_offset(2)
    dot = bytearray(32); dot[0:11] = b".          "; dot[11] = 0x10; struct.pack_into("<H", dot, 26, 2)
    dotdot = bytearray(32); dotdot[0:11] = b"..         "; dotdot[11] = 0x10; struct.pack_into("<H", dotdot, 26, 0)
    boot_dir = bytearray(32); boot_dir[0:11] = b"BOOT       "; boot_dir[11] = 0x10; struct.pack_into("<H", boot_dir, 26, 3)
    disk[c2:c2+32] = dot; disk[c2+32:c2+64] = dotdot; disk[c2+64:c2+96] = boot_dir
    
    # Cluster 3: \EFI\BOOT
    c3 = cluster_offset(3)
    b_dot = bytearray(32); b_dot[0:11] = b".          "; b_dot[11] = 0x10; struct.pack_into("<H", b_dot, 26, 3)
    b_dotdot = bytearray(32); b_dotdot[0:11] = b"..         "; b_dotdot[11] = 0x10; struct.pack_into("<H", b_dotdot, 26, 2)
    file_entry = bytearray(32); file_entry[0:11] = b"BOOTX64 EFI"; file_entry[11] = 0x20
    struct.pack_into("<H", file_entry, 26, 4)
    struct.pack_into("<I", file_entry, 28, len(bootx64_data))
    disk[c3:c3+32] = b_dot; disk[c3+32:c3+64] = b_dotdot; disk[c3+64:c3+96] = file_entry
    
    # Cluster 4+: BOOTX64.EFI
    c4 = cluster_offset(4)
    disk[c4 : c4 + len(bootx64_data)] = bootx64_data
    
    with open(RAW_IMG, "wb") as f:
        f.write(disk)
        
    print(f"  [OK] Imagem RAW gerada ({len(disk)} bytes).")
    return True

def convert_and_attach():
    print("[3/4] Convertendo RAW para VDI e configurando VirtualBox...")
    vm_name = "BakenOS "
    
    subprocess.run([VBOX_MANAGE, "storageattach", vm_name, "--storagectl", "SATA", "--port", "0", "--device", "0", "--type", "hdd", "--medium", "none"], capture_output=True)
    subprocess.run([VBOX_MANAGE, "closemedium", "disk", VDI_IMG], capture_output=True)
    
    if os.path.exists(VDI_IMG):
        os.remove(VDI_IMG)
        
    cmd = [VBOX_MANAGE, "convertfromraw", RAW_IMG, VDI_IMG, "--format", "VDI"]
    subprocess.run(cmd, check=True)
    
    print("[4/4] Conectando disco na VM e ajustando ordem de boot...")
    subprocess.run([VBOX_MANAGE, "storageattach", vm_name, "--storagectl", "SATA", "--port", "0", "--device", "0", "--type", "hdd", "--medium", VDI_IMG], check=True)
    subprocess.run([VBOX_MANAGE, "modifyvm", vm_name, "--boot1", "disk", "--boot2", "none"], check=True)
    
    print("\n[SUCESSO] Sistema Modular Nativo compilado e pronto para boot!")

def main():
    if not compile_kernel_and_bootloader():
        sys.exit(1)
    if not create_fat16_mbr_disk():
        sys.exit(1)
    convert_and_attach()

if __name__ == "__main__":
    main()
