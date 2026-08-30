#!/usr/bin/env python3
"""Cria um disco MBR de teste com uma ESP FAT16 e BOOTX64.EFI.

Não é GPT, não é FAT32 e não contém um sistema instalado. É a mídia gravável
usada pelo teste UEFI/QEMU para exercitar o registro de persistência mínimo.
"""

import os
import struct

# Deve coincidir com o bridge UEFI. O setor fica em um cluster FAT reservado,
# portanto a própria FAT não poderá reutilizá-lo para um arquivo futuro.
INSTALL_RECORD_LBA = 8192
PERSISTENT_STORE_LBA = 8193

def create_esp_disk_image(output_img: str, efi_bin_path: str, startup_nsh_path: str | None = None,
                          kernel_bin_path: str | None = None):
    TOTAL_SECTORS = 131072 # 64 MB
    SECTOR_SIZE = 512
    PART_START_LBA = 2048 # Início da partição ESP no setor 2048 (1 MB)
    PART_SECTORS = TOTAL_SECTORS - PART_START_LBA
    
    if not os.path.isfile(efi_bin_path):
        raise FileNotFoundError(f"BOOTX64.EFI obrigatório não encontrado: {efi_bin_path}")
    with open(efi_bin_path, "rb") as f:
        efi_data = f.read()
    if not efi_data:
        raise ValueError("BOOTX64.EFI está vazio")

    if startup_nsh_path and os.path.exists(startup_nsh_path):
        with open(startup_nsh_path, "rb") as f:
            startup_data = f.read()
    else:
        startup_data = None

    if kernel_bin_path and os.path.exists(kernel_bin_path):
        with open(kernel_bin_path, "rb") as f:
            kernel_data = f.read()
    else:
        kernel_data = None
        
    disk = bytearray(TOTAL_SECTORS * SECTOR_SIZE)
    
    # -------------------------------------------------------------
    # 1. MBR Partition Table no Setor 0
    # -------------------------------------------------------------
    # Entrada de Partição 1 no offset 446 (0x1BE)
    # Bootable flag (0x80), Type 0xEF (EFI System Partition)
    part_entry = struct.pack(
        "<BBBBBBBBII",
        0x80,               # Bootable (Active)
        0x00, 0x02, 0x00,   # Start CHS
        0xEF,               # Partition Type: EFI System Partition (0xEF)
        0xFF, 0xFF, 0xFF,   # End CHS
        PART_START_LBA,     # Starting LBA (2048)
        PART_SECTORS        # Total Sectors in Partition
    )
    disk[446 : 446 + 16] = part_entry
    disk[510:512] = b"\x55\xaa" # MBR Signature
    
    # -------------------------------------------------------------
    # 2. FAT16 VBR no Setor 2048 (Início da Partição ESP)
    # -------------------------------------------------------------
    vbr_offset = PART_START_LBA * SECTOR_SIZE
    disk[vbr_offset : vbr_offset + 3] = b"\xeb\x3c\x90"
    disk[vbr_offset + 3 : vbr_offset + 11] = b"BAKENEFI"
    
    struct.pack_into("<H", disk, vbr_offset + 11, SECTOR_SIZE) # Bytes/Sector (512)
    disk[vbr_offset + 13] = 4 # Sectors/Cluster (2048 bytes)
    struct.pack_into("<H", disk, vbr_offset + 14, 1) # Reserved sectors
    disk[vbr_offset + 16] = 2 # Num FATs
    struct.pack_into("<H", disk, vbr_offset + 17, 512) # Root Entries (512)
    struct.pack_into("<H", disk, vbr_offset + 19, 0)
    struct.pack_into("<H", disk, vbr_offset + 21, 0xF8) # Media descriptor
    struct.pack_into("<H", disk, vbr_offset + 22, 128) # Sectors/FAT (128 setores cobrem perfeitamente os 32215 clusters)
    struct.pack_into("<H", disk, vbr_offset + 24, 63)
    struct.pack_into("<H", disk, vbr_offset + 26, 255)
    struct.pack_into("<I", disk, vbr_offset + 28, PART_START_LBA) # Hidden sectors
    struct.pack_into("<I", disk, vbr_offset + 32, PART_SECTORS)
    disk[vbr_offset + 36] = 0x80
    disk[vbr_offset + 38] = 0x29
    struct.pack_into("<I", disk, vbr_offset + 39, 0xBA1CE001)
    disk[vbr_offset + 43 : vbr_offset + 54] = b"BAKEN_ESP  "
    disk[vbr_offset + 54 : vbr_offset + 62] = b"FAT16   "
    disk[vbr_offset + 510 : vbr_offset + 512] = b"\x55\xaa"
    
    # -------------------------------------------------------------
    # 3. Inicializa FAT e Diretórios dentro da Partição
    # -------------------------------------------------------------
    fat1_offset = vbr_offset + (1 * SECTOR_SIZE)
    fat2_offset = vbr_offset + ((1 + 128) * SECTOR_SIZE)
    root_dir_offset = vbr_offset + ((1 + 128 * 2) * SECTOR_SIZE)
    data_area_offset = root_dir_offset + (512 * 32)
    first_data_sector = (data_area_offset - vbr_offset) // SECTOR_SIZE
    data_clusters = (PART_SECTORS - first_data_sector) // 4
    last_data_cluster = 2 + data_clusters - 1
    
    struct.pack_into("<H", disk, fat1_offset + 0, 0xFFF8)
    struct.pack_into("<H", disk, fat1_offset + 2, 0xFFFF)
    struct.pack_into("<H", disk, fat2_offset + 0, 0xFFF8)
    struct.pack_into("<H", disk, fat2_offset + 2, 0xFFFF)
    
    current_cluster = 2
    def write_file(name_8_3, data):
        nonlocal current_cluster
        cluster_size = 4 * SECTOR_SIZE
        num_clusters = (len(data) + cluster_size - 1) // cluster_size
        if num_clusters == 0: num_clusters = 1
        if current_cluster + num_clusters - 1 > last_data_cluster:
            raise ValueError("arquivo excede a capacidade da ESP FAT16 de teste")
        
        start_cluster = current_cluster
        offset = data_area_offset + (start_cluster - 2) * cluster_size
        disk[offset : offset + len(data)] = data
        
        for c in range(num_clusters):
            c_curr = start_cluster + c
            c_next = 0xFFFF if c == num_clusters - 1 else c_curr + 1
            struct.pack_into("<H", disk, fat1_offset + c_curr * 2, c_next)
            struct.pack_into("<H", disk, fat2_offset + c_curr * 2, c_next)
            
        current_cluster += num_clusters
        return start_cluster, len(data)

    def reserve_raw_lba(lba):
        """Marca o cluster que contém um registro bare-metal como ocupado."""
        if lba < PART_START_LBA:
            raise ValueError("LBA de registro fora da partição ESP")
        sector_in_partition = lba - PART_START_LBA
        if sector_in_partition < first_data_sector:
            raise ValueError("LBA de registro invade metadados FAT")
        cluster = 2 + (sector_in_partition - first_data_sector) // 4
        if cluster >= 0xFFF7:
            raise ValueError("LBA de registro fora da FAT16")
        curr_fat = struct.unpack_from("<H", disk, fat1_offset + cluster * 2)[0]
        if curr_fat == 0:
            struct.pack_into("<H", disk, fat1_offset + cluster * 2, 0xFFFF)
            struct.pack_into("<H", disk, fat2_offset + cluster * 2, 0xFFFF)
        
    c_bootx64, sz_bootx64 = write_file(b"BOOTX64 EFI", efi_data)
    
    def make_entry(dir_buf, entry_idx, name_8_3, cluster, size, attr=0x20):
        off = entry_idx * 32
        dir_buf[off:off+11] = name_8_3
        dir_buf[off+11] = attr
        struct.pack_into("<H", dir_buf, off + 26, cluster)
        struct.pack_into("<I", dir_buf, off + 28, size)
        
    root_dir = memoryview(disk)[root_dir_offset : root_dir_offset + 512*32]
    root_entry_index = 0
    if startup_data is not None:
        c_startup, sz_startup = write_file(b"STARTUP NSH", startup_data)
        make_entry(root_dir, root_entry_index, b"STARTUP NSH", c_startup, sz_startup)
        root_entry_index += 1
    if kernel_data is not None:
        c_kernel, sz_kernel = write_file(b"KERNEL  BKN", kernel_data)
        make_entry(root_dir, root_entry_index, b"KERNEL  BKN", c_kernel, sz_kernel)
        root_entry_index += 1
    make_entry(root_dir, root_entry_index, b"BOOTX64 EFI", c_bootx64, sz_bootx64)
    root_entry_index += 1
    
    efi_dir_cluster = current_cluster
    current_cluster += 1
    struct.pack_into("<H", disk, fat1_offset + efi_dir_cluster * 2, 0xFFFF)
    struct.pack_into("<H", disk, fat2_offset + efi_dir_cluster * 2, 0xFFFF)
    make_entry(root_dir, root_entry_index, b"EFI        ", efi_dir_cluster, 0, attr=0x10)
    
    efi_dir_offset = data_area_offset + (efi_dir_cluster - 2) * (4 * SECTOR_SIZE)
    efi_dir = memoryview(disk)[efi_dir_offset : efi_dir_offset + 4 * SECTOR_SIZE]
    make_entry(efi_dir, 0, b".          ", efi_dir_cluster, 0, attr=0x10)
    make_entry(efi_dir, 1, b"..         ", 0, 0, attr=0x10)
    
    boot_dir_cluster = current_cluster
    current_cluster += 1
    struct.pack_into("<H", disk, fat1_offset + boot_dir_cluster * 2, 0xFFFF)
    struct.pack_into("<H", disk, fat2_offset + boot_dir_cluster * 2, 0xFFFF)
    make_entry(efi_dir, 2, b"BOOT       ", boot_dir_cluster, 0, attr=0x10)
    
    boot_dir_offset = data_area_offset + (boot_dir_cluster - 2) * (4 * SECTOR_SIZE)
    boot_dir = memoryview(disk)[boot_dir_offset : boot_dir_offset + 4 * SECTOR_SIZE]
    make_entry(boot_dir, 0, b".          ", boot_dir_cluster, 0, attr=0x10)
    make_entry(boot_dir, 1, b"..         ", efi_dir_cluster, 0, attr=0x10)
    make_entry(boot_dir, 2, b"BOOTX64 EFI", c_bootx64, sz_bootx64, attr=0x20)
    reserve_raw_lba(INSTALL_RECORD_LBA)
    reserve_raw_lba(PERSISTENT_STORE_LBA)
    
    with open(output_img, "wb") as f:
        f.write(disk)
        
    print(f"[OK] Disco MBR de teste com ESP FAT16 criado em: {output_img}")

if __name__ == "__main__":
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out_img = os.path.join(root, "build", "baken_disk.img")
    efi = os.path.join(root, "build", "iso_root", "EFI", "BOOT", "BOOTX64.EFI")
    startup = os.path.join(root, "build", "iso_root", "startup.nsh")
    kernel = os.path.join(root, "build", "iso_root", "KERNEL.BKN_EXEC")
    
    create_esp_disk_image(out_img, efi, startup, kernel)
    target_img = os.path.join(root, "build", "baken_install_target.img")
    if not os.path.exists(target_img):
        with open(target_img, "wb") as f:
            f.truncate(64 * 1024 * 1024)
        print(f"[OK] Disco alvo de instalacao GPT de 64MB criado em: {target_img}")
