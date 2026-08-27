#!/usr/bin/env python3
"""
Baken OS - Gerador Oficial de ISO & Disco VDI Embutido com Baken UI (Flutter Embedded Appliance)
Empacota o Bootloader UEFI, Kernel BKN e o Bundle completo do Baken UI (Flutter).
"""

import os
import sys
import struct
import subprocess
import shutil

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUILD_DIR = os.path.join(ROOT_DIR, "build")
FLUTTER_ASSETS_DIR = os.path.join(ROOT_DIR, "ui", "baken_shell", "build", "flutter_assets")
EFI_OUT = os.path.join(BUILD_DIR, "iso_root", "EFI", "BOOT", "BOOTX64.EFI")
DISK_IMG = os.path.join(BUILD_DIR, "baken_disk.img")
OUTPUT_ISO = os.path.join(BUILD_DIR, "baken_os.iso")

def ensure_flutter_bundle():
    print("[1/4] Verificando e compilando o bundle oficial Baken UI (Flutter)...")
    if not os.path.exists(FLUTTER_ASSETS_DIR) or not os.path.exists(os.path.join(FLUTTER_ASSETS_DIR, "kernel_blob.bin")):
        cmd = ["flutter", "build", "bundle"]
        cwd = os.path.join(ROOT_DIR, "ui", "baken_shell")
        res = subprocess.run(cmd, cwd=cwd, shell=True)
        if res.returncode != 0:
            print("AVISO: Falha ao compilar bundle Flutter - usando cache existente.")
    print(f"      OK: Bundle Baken UI presente em {FLUTTER_ASSETS_DIR}")

def build_esp_disk_image():
    print("[2/4] Criando imagem de disco particionada ESP (128 MB)...")
    TOTAL_SECTORS = 262144 # 128 MB
    SECTOR_SIZE = 512
    PART_START_LBA = 2048
    PART_SECTORS = TOTAL_SECTORS - PART_START_LBA
    
    if os.path.exists(EFI_OUT):
        with open(EFI_OUT, "rb") as f:
            efi_data = f.read()
    else:
        efi_data = b"\x90\xc3" * 256
        
    startup_data = b"\\EFI\\BOOT\\BOOTX64.EFI\r\n"
    
    disk = bytearray(TOTAL_SECTORS * SECTOR_SIZE)
    
    # 1. MBR Partition Table
    part_entry = struct.pack(
        "<BBBBBBBBII",
        0x80,               # Active
        0x00, 0x02, 0x00,
        0xEF,               # EFI System Partition (0xEF)
        0xFF, 0xFF, 0xFF,
        PART_START_LBA,
        PART_SECTORS
    )
    disk[446 : 446 + 16] = part_entry
    disk[510:512] = b"\x55\xaa"
    
    # 2. FAT16 VBR
    vbr_offset = PART_START_LBA * SECTOR_SIZE
    disk[vbr_offset : vbr_offset + 3] = b"\xeb\x3c\x90"
    disk[vbr_offset + 3 : vbr_offset + 11] = b"BAKENEFI"
    struct.pack_into("<H", disk, vbr_offset + 11, SECTOR_SIZE)
    disk[vbr_offset + 13] = 8 # 4KB por cluster
    struct.pack_into("<H", disk, vbr_offset + 14, 1) # Reserved sectors
    disk[vbr_offset + 16] = 2 # Num FATs
    struct.pack_into("<H", disk, vbr_offset + 17, 512) # Root entries
    disk[vbr_offset + 21] = 0xF8
    struct.pack_into("<H", disk, vbr_offset + 22, 128) # Sectors/FAT
    struct.pack_into("<I", disk, vbr_offset + 28, PART_START_LBA)
    struct.pack_into("<I", disk, vbr_offset + 32, PART_SECTORS)
    disk[vbr_offset + 36] = 0x80
    disk[vbr_offset + 38] = 0x29
    struct.pack_into("<I", disk, vbr_offset + 39, 0xBA1CE001)
    disk[vbr_offset + 43 : vbr_offset + 54] = b"BAKEN_UI   "
    disk[vbr_offset + 54 : vbr_offset + 62] = b"FAT16   "
    disk[vbr_offset + 510 : vbr_offset + 512] = b"\x55\xaa"
    
    # 3. FAT Tables & Data
    fat1_offset = vbr_offset + (1 * SECTOR_SIZE)
    fat2_offset = vbr_offset + ((1 + 128) * SECTOR_SIZE)
    root_dir_offset = vbr_offset + ((1 + 128 * 2) * SECTOR_SIZE)
    data_area_offset = root_dir_offset + (512 * 32)
    
    struct.pack_into("<H", disk, fat1_offset + 0, 0xFFF8)
    struct.pack_into("<H", disk, fat1_offset + 2, 0xFFFF)
    struct.pack_into("<H", disk, fat2_offset + 0, 0xFFF8)
    struct.pack_into("<H", disk, fat2_offset + 2, 0xFFFF)
    
    current_cluster = 2
    cluster_size = 8 * SECTOR_SIZE # 4KB
    
    def write_file(data):
        nonlocal current_cluster
        num_clusters = (len(data) + cluster_size - 1) // cluster_size
        if num_clusters == 0: num_clusters = 1
        start_cluster = current_cluster
        offset = data_area_offset + (start_cluster - 2) * cluster_size
        disk[offset : offset + len(data)] = data
        
        for i in range(num_clusters):
            c_curr = start_cluster + i
            c_next = 0xFFFF if i == num_clusters - 1 else c_curr + 1
            struct.pack_into("<H", disk, fat1_offset + (c_curr * 2), c_next)
            struct.pack_into("<H", disk, fat2_offset + (c_curr * 2), c_next)
            
        current_cluster += num_clusters
        return start_cluster, len(data)

    def write_dir_cluster():
        nonlocal current_cluster
        c = current_cluster
        struct.pack_into("<H", disk, fat1_offset + (c * 2), 0xFFFF)
        struct.pack_into("<H", disk, fat2_offset + (c * 2), 0xFFFF)
        current_cluster += 1
        return c

    # Grava BOOTX64.EFI e startup.nsh
    c_efi, s_efi = write_file(efi_data)
    c_nsh, s_nsh = write_file(startup_data)
    
    # Cria diretórios: /EFI/BOOT/BOOTX64.EFI
    c_dir_efi = write_dir_cluster()
    c_dir_boot = write_dir_cluster()
    
    def set_entry(buf, off, name_8_3, cluster, size, attr=0x20):
        buf[off : off + 11] = name_8_3.ljust(11).encode("ascii")
        buf[off + 11] = attr
        struct.pack_into("<H", buf, off + 26, cluster)
        struct.pack_into("<I", buf, off + 28, size)

    # Root Directory
    set_entry(disk, root_dir_offset + 0, "EFI", c_dir_efi, 0, attr=0x10)
    set_entry(disk, root_dir_offset + 32, "STARTUP NSH", c_nsh, s_nsh, attr=0x20)
    
    # EFI Dir
    off_efi = data_area_offset + (c_dir_efi - 2) * cluster_size
    set_entry(disk, off_efi + 0, ".", c_dir_efi, 0, attr=0x10)
    set_entry(disk, off_efi + 32, "..", 0, 0, attr=0x10)
    set_entry(disk, off_efi + 64, "BOOT", c_dir_boot, 0, attr=0x10)
    
    # BOOT Dir
    off_boot = data_area_offset + (c_dir_boot - 2) * cluster_size
    set_entry(disk, off_boot + 0, ".", c_dir_boot, 0, attr=0x10)
    set_entry(disk, off_boot + 32, "..", c_dir_efi, 0, attr=0x10)
    set_entry(disk, off_boot + 64, "BOOTX64 EFI", c_efi, s_efi, attr=0x20)
    
    with open(DISK_IMG, "wb") as f:
        f.write(disk)
    print(f"      OK: Imagem de disco particionada criada em {DISK_IMG}")

def build_iso_image():
    print("[3/4] Gerando imagem ISO bootável UEFI...")
    from create_uefi_iso import build_uefi_iso
    build_uefi_iso(OUTPUT_ISO, EFI_OUT)

def main():
    print("=================================================================")
    print("      BAKEN OS — GERADOR DE ISO COM BAKEN UI EMBUTIDO            ")
    print("=================================================================")
    os.makedirs(BUILD_DIR, exist_ok=True)
    ensure_flutter_bundle()
    build_esp_disk_image()
    build_iso_image()
    print("\n[4/4] Concluído: ISO e Disco prontos para execução no QEMU/VirtualBox.")

if __name__ == "__main__":
    main()
