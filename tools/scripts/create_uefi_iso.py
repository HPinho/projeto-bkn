#!/usr/bin/env python3
"""Cria uma ISO óptica UEFI (El Torito) de teste para Baken OS.

Ela é apropriada para boot por CD/DVD virtual em QEMU, VirtualBox ou VMware.
Não é uma imagem híbrida GPT/USB e não deve ser gravada diretamente em pendrive.
"""

import os
import struct

def create_fat_efi_img(efi_bin_bytes: bytes) -> bytes:
    """Cria uma ESP FAT12 de 12MB contendo /EFI/BOOT/BOOTX64.EFI.

    Os atlas multi-DPI são parte do executável UEFI; a antiga ESP de 2.88MB
    não comporta uma interface de alta definição. 12MB ainda é uma mídia
    óptica pequena e mantém o layout El-Torito simples para as VMs.
    """
    SECTOR_SIZE = 512
    TOTAL_SECTORS = 24576 # 12 MB
    SECTORS_PER_CLUSTER = 8 # 4 KB; mantém a contagem no limite FAT12
    RESERVED_SECTORS = 1
    FAT_COUNT = 2
    SECTORS_PER_FAT = 9
    ROOT_ENTRIES = 224
    fat_disk = bytearray(TOTAL_SECTORS * SECTOR_SIZE)
    if not efi_bin_bytes:
        raise ValueError("BOOTX64.EFI não pode estar vazio")
    
    # 1. FAT12/16 VBR no Setor 0
    fat_disk[0:3] = b"\xeb\x3c\x90"
    fat_disk[3:11] = b"MSWIN4.1"
    struct.pack_into("<H", fat_disk, 11, SECTOR_SIZE) # Bytes/Sector
    fat_disk[13] = SECTORS_PER_CLUSTER # Sectors/Cluster (1024 bytes)
    struct.pack_into("<H", fat_disk, 14, RESERVED_SECTORS) # Reserved sectors
    fat_disk[16] = FAT_COUNT # Num FATs
    struct.pack_into("<H", fat_disk, 17, ROOT_ENTRIES) # Root Entries
    struct.pack_into("<H", fat_disk, 19, TOTAL_SECTORS) # Total sectors
    fat_disk[21] = 0xF8 # Media descriptor
    struct.pack_into("<H", fat_disk, 22, SECTORS_PER_FAT) # Sectors/FAT
    struct.pack_into("<H", fat_disk, 24, 18) # Sectors/Track
    struct.pack_into("<H", fat_disk, 26, 2) # Heads
    struct.pack_into("<I", fat_disk, 28, 0) # Hidden sectors
    fat_disk[36] = 0x80
    fat_disk[38] = 0x29
    struct.pack_into("<I", fat_disk, 39, 0xBA1CE001)
    fat_disk[43:54] = b"BAKEN_EFI  "
    fat_disk[54:62] = b"FAT12   "
    fat_disk[510:512] = b"\x55\xaa"
    
    # 2. Inicializa FAT1 e FAT2
    fat1_off = RESERVED_SECTORS * SECTOR_SIZE
    fat2_off = (RESERVED_SECTORS + SECTORS_PER_FAT) * SECTOR_SIZE
    root_off = (RESERVED_SECTORS + SECTORS_PER_FAT * FAT_COUNT) * SECTOR_SIZE
    data_off = root_off + (ROOT_ENTRIES * 32)
    
    fat_disk[fat1_off:fat1_off+3] = b"\xf8\xff\xff"
    fat_disk[fat2_off:fat2_off+3] = b"\xf8\xff\xff"
    
    current_cluster = 2
    
    # Grava BOOTX64.EFI
    cluster_size = SECTORS_PER_CLUSTER * SECTOR_SIZE
    num_clusters = (len(efi_bin_bytes) + cluster_size - 1) // cluster_size
    data_clusters = (TOTAL_SECTORS * SECTOR_SIZE - data_off) // cluster_size
    # /EFI e /EFI/BOOT ocupam um cluster cada. Não cresça o buffer caso o
    # executável não caiba: a mídia precisa falhar fechada.
    if num_clusters + 2 > data_clusters:
        raise ValueError("BOOTX64.EFI excede a capacidade da ESP óptica")
    
    start_cluster = current_cluster
    offset = data_off + (start_cluster - 2) * cluster_size
    fat_disk[offset : offset + len(efi_bin_bytes)] = efi_bin_bytes
    
    # Atualiza FAT12 entries
    def set_fat12(fat_buf, cluster, val):
        entry_offset = (cluster * 3) // 2
        if cluster % 2 == 0:
            fat_buf[entry_offset] = val & 0xFF
            fat_buf[entry_offset + 1] = (fat_buf[entry_offset + 1] & 0xF0) | ((val >> 8) & 0x0F)
        else:
            fat_buf[entry_offset] = (fat_buf[entry_offset] & 0x0F) | ((val & 0x0F) << 4)
            fat_buf[entry_offset + 1] = (val >> 4) & 0xFF

    for c in range(num_clusters):
        c_curr = start_cluster + c
        c_next = 0xFFF if c == num_clusters - 1 else c_curr + 1
        set_fat12(memoryview(fat_disk)[fat1_off:fat1_off+9*512], c_curr, c_next)
        set_fat12(memoryview(fat_disk)[fat2_off:fat2_off+9*512], c_curr, c_next)
        
    current_cluster += num_clusters
    
    # Cria estrutura de pastas: /EFI/BOOT/BOOTX64.EFI
    efi_dir_cluster = current_cluster
    current_cluster += 1
    set_fat12(memoryview(fat_disk)[fat1_off:fat1_off+9*512], efi_dir_cluster, 0xFFF)
    set_fat12(memoryview(fat_disk)[fat2_off:fat2_off+9*512], efi_dir_cluster, 0xFFF)
    
    boot_dir_cluster = current_cluster
    current_cluster += 1
    set_fat12(memoryview(fat_disk)[fat1_off:fat1_off+9*512], boot_dir_cluster, 0xFFF)
    set_fat12(memoryview(fat_disk)[fat2_off:fat2_off+9*512], boot_dir_cluster, 0xFFF)
    
    def make_entry(buf, off, name_8_3, cluster, size, attr=0x20):
        buf[off:off+11] = name_8_3
        buf[off+11] = attr
        struct.pack_into("<H", buf, off + 26, cluster)
        struct.pack_into("<I", buf, off + 28, size)
        
    # Root dir entry -> EFI
    make_entry(memoryview(fat_disk), root_off, b"EFI        ", efi_dir_cluster, 0, attr=0x10)
    make_entry(memoryview(fat_disk), root_off + 32, b"BOOTX64 EFI", start_cluster, len(efi_bin_bytes), attr=0x20)
    
    # EFI dir -> BOOT
    efi_dir_off = data_off + (efi_dir_cluster - 2) * cluster_size
    make_entry(memoryview(fat_disk), efi_dir_off, b".          ", efi_dir_cluster, 0, attr=0x10)
    make_entry(memoryview(fat_disk), efi_dir_off + 32, b"..         ", 0, 0, attr=0x10)
    make_entry(memoryview(fat_disk), efi_dir_off + 64, b"BOOT       ", boot_dir_cluster, 0, attr=0x10)
    
    # BOOT dir -> BOOTX64.EFI
    boot_dir_off = data_off + (boot_dir_cluster - 2) * cluster_size
    make_entry(memoryview(fat_disk), boot_dir_off, b".          ", boot_dir_cluster, 0, attr=0x10)
    make_entry(memoryview(fat_disk), boot_dir_off + 32, b"..         ", efi_dir_cluster, 0, attr=0x10)
    make_entry(memoryview(fat_disk), boot_dir_off + 64, b"BOOTX64 EFI", start_cluster, len(efi_bin_bytes), attr=0x20)
    
    return bytes(fat_disk)

def build_uefi_iso(output_iso: str, efi_bin_path: str):
    ISO_SECTOR = 2048
    
    if not os.path.isfile(efi_bin_path):
        raise FileNotFoundError(f"BOOTX64.EFI obrigatório não encontrado: {efi_bin_path}")
    with open(efi_bin_path, "rb") as f:
        efi_bytes = f.read()
        
    fat_img = create_fat_efi_img(efi_bytes)
    fat_sectors_iso = (len(fat_img) + ISO_SECTOR - 1) // ISO_SECTOR
    
    # Layout da ISO:
    # Setores 0 - 15: System Area (32 KB)
    # Setor 16: Primary Volume Descriptor (PVD)
    # Setor 17: Boot Record Volume Descriptor (El-Torito)
    # Setor 18: Volume Descriptor Set Terminator
    # Setor 19: Root Directory Record
    # Setor 20: El-Torito Boot Catalog
    # Setor 21+: EFI Boot Image (fat_img)
    
    boot_catalog_lba = 20
    efi_img_lba = 21
    total_iso_sectors = efi_img_lba + fat_sectors_iso + 10
    
    iso_buf = bytearray(total_iso_sectors * ISO_SECTOR)
    
    # 1. Primary Volume Descriptor (PVD) no Setor 16
    pvd = memoryview(iso_buf)[16 * ISO_SECTOR : 17 * ISO_SECTOR]
    pvd[0] = 0x01 # PVD Type
    pvd[1:6] = b"CD001"
    pvd[6] = 0x01
    pvd[8:40] = b"BAKEN_OS_UEFI".ljust(32, b" ")
    pvd[40:72] = b"BAKEN_OS_SYSTEM".ljust(32, b" ")
    
    # Volume Space Size
    struct.pack_into("<I", pvd, 80, total_iso_sectors)
    struct.pack_into(">I", pvd, 84, total_iso_sectors)
    
    # Logical Block Size (2048)
    struct.pack_into("<H", pvd, 128, ISO_SECTOR)
    struct.pack_into(">H", pvd, 130, ISO_SECTOR)
    
    # Root Directory Record dentro do PVD (offset 156)
    root_dr = pvd[156:190]
    root_dr[0] = 34 # Length
    root_dr[1] = 0
    struct.pack_into("<I", root_dr, 2, 19) # LBA do Root Dir
    struct.pack_into(">I", root_dr, 6, 19)
    struct.pack_into("<I", root_dr, 10, ISO_SECTOR) # Size
    struct.pack_into(">I", root_dr, 14, ISO_SECTOR)
    root_dr[25] = 0x02 # Directory flag
    root_dr[32] = 1 # Identifier length
    root_dr[33] = 0 # Root identifier
    
    # 2. Boot Record Volume Descriptor (El-Torito) no Setor 17
    el_torito_vd = memoryview(iso_buf)[17 * ISO_SECTOR : 18 * ISO_SECTOR]
    el_torito_vd[0] = 0x00 # Boot Record Type
    el_torito_vd[1:6] = b"CD001"
    el_torito_vd[6] = 0x01
    el_torito_vd[7:39] = b"EL TORITO SPECIFICATION".ljust(32, b"\x00")
    struct.pack_into("<I", el_torito_vd, 71, boot_catalog_lba) # Pointer to Boot Catalog
    
    # 3. Volume Descriptor Set Terminator no Setor 18
    term = memoryview(iso_buf)[18 * ISO_SECTOR : 19 * ISO_SECTOR]
    term[0] = 0xFF
    term[1:6] = b"CD001"
    term[6] = 0x01
    
    # 4. Root Directory Record no Setor 19
    r_dir = memoryview(iso_buf)[19 * ISO_SECTOR : 20 * ISO_SECTOR]
    # '.' entry
    r_dir[0] = 34
    struct.pack_into("<I", r_dir, 2, 19)
    struct.pack_into(">I", r_dir, 6, 19)
    struct.pack_into("<I", r_dir, 10, ISO_SECTOR)
    struct.pack_into(">I", r_dir, 14, ISO_SECTOR)
    r_dir[25] = 0x02
    r_dir[32] = 1
    r_dir[33] = 0
    # '..' entry
    r_dir[34] = 34
    struct.pack_into("<I", r_dir, 36, 19)
    struct.pack_into(">I", r_dir, 40, 19)
    struct.pack_into("<I", r_dir, 44, ISO_SECTOR)
    struct.pack_into(">I", r_dir, 48, ISO_SECTOR)
    r_dir[59] = 0x02
    r_dir[66] = 1
    r_dir[67] = 1
    
    # 5. El-Torito Boot Catalog no Setor 20
    catalog = memoryview(iso_buf)[boot_catalog_lba * ISO_SECTOR : (boot_catalog_lba + 1) * ISO_SECTOR]
    
    # Validation Entry (32 bytes)
    catalog[0] = 0x01 # Header ID
    catalog[1] = 0x00 # Platform ID (x86)
    catalog[30] = 0x55
    catalog[31] = 0xAA
    # Checksum exato El-Torito: soma de palavras de 16-bits nos primeiros 32 bytes deve ser zero
    words_sum = sum(struct.unpack("<14H", bytes(catalog[0:28]))) + 0xAA55
    checksum = (-words_sum) & 0xFFFF
    struct.pack_into("<H", catalog, 28, checksum)
    
    # Initial / Default Entry (32 bytes - offset 32) -> Bootable EFI
    catalog[32] = 0x88 # Bootable
    catalog[33] = 0x00 # No emulation
    struct.pack_into("<H", catalog, 34, 0) # Load segment
    catalog[36] = 0xEF # System Type (EFI)
    struct.pack_into("<H", catalog, 38, 1) # Sector count
    struct.pack_into("<I", catalog, 40, efi_img_lba) # Load RBA / LBA
    
    # Section Header for EFI (offset 64)
    catalog[64] = 0x91 # Final section header
    catalog[65] = 0xEF # EFI Platform ID (0xEF)
    struct.pack_into("<H", catalog, 66, 1) # 1 section entry following
    
    # Section Entry for EFI (offset 96)
    catalog[96] = 0x88 # Bootable
    catalog[97] = 0x00 # No emulation
    struct.pack_into("<H", catalog, 98, 0) # Load segment
    catalog[100] = 0xEF # System Type (EFI)
    struct.pack_into("<H", catalog, 102, 1) # Sector count
    struct.pack_into("<I", catalog, 104, efi_img_lba) # Load RBA / LBA
    
    # 6. Grava imagem FAT ESP no Setor efi_img_lba
    fat_off = efi_img_lba * ISO_SECTOR
    iso_buf[fat_off : fat_off + len(fat_img)] = fat_img
    
    with open(output_iso, "wb") as f:
        f.write(iso_buf)
        
    print(f"[OK] ISO óptica UEFI de teste criada: {output_iso} ({len(iso_buf)/(1024*1024):.2f} MB)")

if __name__ == "__main__":
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out_iso = os.path.join(root, "build", "baken_os.iso")
    efi = os.path.join(root, "build", "iso_root", "EFI", "BOOT", "BOOTX64.EFI")
    
    build_uefi_iso(out_iso, efi)
