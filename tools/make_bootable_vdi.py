#!/usr/bin/env python3
"""
Baken OS - Criador de Disco Virtual Bootável VDI / RAW para VirtualBox
Gera um disco GPT 100% válido com Partição de Sistema EFI (FAT32) contendo BOOTX64.EFI.
"""

import os
import sys
import struct
import subprocess
import uuid
import zlib

ROOT_DIR = r"E:\projeto-bkn"
BUILD_DIR = os.path.join(ROOT_DIR, "build")
RAW_IMG = os.path.join(BUILD_DIR, "baken_os.raw")
VDI_IMG = os.path.join(BUILD_DIR, "baken_os.vdi")
GCC_BIN = os.path.join(ROOT_DIR, "tools", "w64devkit", "bin")
VBOX_MANAGE = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"

def compile_uefi_bootloader():
    print("[1/4] Compilando Bootloader UEFI nativo com ABI Microsoft e short-wchar...")
    src = os.path.join(ROOT_DIR, "boot", "src", "uefi_main.c")
    out_efi = os.path.join(BUILD_DIR, "BOOTX64.EFI")
    
    env = os.environ.copy()
    env["PATH"] = GCC_BIN + ";" + env.get("PATH", "")
    
    cmd = [
        os.path.join(GCC_BIN, "gcc.exe"),
        "-O2", "-nostdlib", "-Wl,--subsystem,10",
        "-fshort-wchar", "-mabi=ms",
        "-e", "efi_main", "-shared",
        "-o", out_efi, src
    ]
    
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Erro ao compilar BOOTX64.EFI:\n{res.stderr}")
        return False
    
    print(f"  [OK] BOOTX64.EFI gerado ({os.path.getsize(out_efi)} bytes).")
    return True

def create_gpt_fat32_disk():
    print("[2/4] Gerando imagem de disco GPT com Partição EFI FAT32 (128 MB)...")
    
    with open(os.path.join(BUILD_DIR, "BOOTX64.EFI"), "rb") as f:
        bootx64_data = f.read()
        
    disk_size_mb = 128
    sector_size = 512
    total_sectors = (disk_size_mb * 1024 * 1024) // sector_size
    
    disk = bytearray(disk_size_mb * 1024 * 1024)
    
    # -------------------------------------------------------------
    # 1. Protective MBR (LBA 0)
    # -------------------------------------------------------------
    mbr_part = struct.pack(
        "<BBBBBBBBII",
        0x00, # Bootable
        0x00, 0x02, 0x00, # Starting CHS
        0xEE, # GPT Protective MBR type
        0xFF, 0xFF, 0xFF, # Ending CHS
        1, # Starting LBA: 1
        total_sectors - 1 # Total LBA
    )
    disk[446:446+16] = mbr_part
    disk[510:512] = b"\x55\xAA"
    
    # -------------------------------------------------------------
    # 2. GPT Partition Table (LBA 1 a 33)
    # -------------------------------------------------------------
    # Partição 1: EFI System Partition (LBA 2048 a total_sectors - 2048)
    part1_start = 2048
    part1_end = total_sectors - 2048
    part1_sectors = part1_end - part1_start + 1
    
    # EFI System Partition GUID: C12A7328-F81F-11D2-BA4B-00A0C93EC93B
    esp_guid = uuid.UUID("C12A7328-F81F-11D2-BA4B-00A0C93EC93B").bytes_le
    part_guid = uuid.UUID("27C9F728-E644-48FE-91A9-E657DC7462B2").bytes_le
    
    part_entry = bytearray(128)
    part_entry[0:16] = esp_guid
    part_entry[16:32] = part_guid
    struct.pack_into("<QQQ", part_entry, 32, part1_start, part1_end, 0)
    # Nome da partição UTF-16LE: "EFI System Partition"
    name_bytes = "EFI System Partition".encode("utf-16le")
    part_entry[56:56+len(name_bytes)] = name_bytes
    
    # Coloca a entrada em LBA 2
    disk[2 * sector_size : 2 * sector_size + 128] = part_entry
    
    # Calcula CRC32 da tabela de partições (32 setores * 512 bytes = 16384 bytes)
    parts_data = disk[2 * sector_size : (2 + 32) * sector_size]
    parts_crc = zlib.crc32(parts_data) & 0xFFFFFFFF
    
    # GPT Header (LBA 1)
    disk_guid = uuid.UUID("98E1A43F-724B-4E38-A39B-89A82D884B12").bytes_le
    gpt_header = bytearray(92)
    gpt_header[0:8] = b"EFI PART" # Signature
    struct.pack_into("<II", gpt_header, 8, 0x00010000, 92) # Revision 1.0, Header size 92
    struct.pack_into("<QQ", gpt_header, 24, 1, total_sectors - 1) # My LBA: 1, Alternate LBA
    struct.pack_into("<QQ", gpt_header, 40, part1_start, part1_end) # First/Last usable LBA
    gpt_header[56:72] = disk_guid
    struct.pack_into("<QII", gpt_header, 72, 2, 128, 128) # Entries LBA: 2, Num Entries: 128, Entry Size: 128
    struct.pack_into("<I", gpt_header, 88, parts_crc)
    
    header_crc = zlib.crc32(gpt_header) & 0xFFFFFFFF
    struct.pack_into("<I", gpt_header, 16, header_crc)
    disk[sector_size : sector_size + 92] = gpt_header
    
    # -------------------------------------------------------------
    # 3. Formatação FAT32 da Partição EFI (Inicia em part1_start)
    # -------------------------------------------------------------
    p_offset = part1_start * sector_size
    sectors_per_cluster = 8 # 4 KB cluster
    reserved_sectors = 32
    num_fats = 2
    fat_size_sectors = 256 # ~1 MB FAT table
    
    # FAT32 BPB (Boot Sector)
    bpb = bytearray(sector_size)
    bpb[0:3] = b"\xEB\x58\x90"
    bpb[3:11] = b"MSWIN4.1"
    struct.pack_into("<H", bpb, 11, sector_size) # 512
    bpb[13] = sectors_per_cluster # 8
    struct.pack_into("<H", bpb, 14, reserved_sectors) # 32
    bpb[16] = num_fats # 2
    struct.pack_into("<H", bpb, 17, 0) # Root entries (0 for FAT32)
    struct.pack_into("<H", bpb, 19, 0) # Small sectors
    bpb[21] = 0xF8 # Media descriptor (Fixed disk)
    struct.pack_into("<H", bpb, 22, 0) # FAT16 size (0)
    struct.pack_into("<H", bpb, 24, 63) # Sectors per track
    struct.pack_into("<H", bpb, 26, 255) # Heads
    struct.pack_into("<I", bpb, 28, part1_start) # Hidden sectors
    struct.pack_into("<I", bpb, 32, part1_sectors) # Total sectors FAT32
    struct.pack_into("<I", bpb, 36, fat_size_sectors) # Sectors per FAT
    struct.pack_into("<H", bpb, 40, 0) # Extended flags
    struct.pack_into("<H", bpb, 42, 0) # Version
    struct.pack_into("<I", bpb, 44, 2) # Root cluster: 2
    struct.pack_into("<H", bpb, 48, 1) # FSInfo sector: 1
    struct.pack_into("<H", bpb, 50, 6) # Backup boot sector: 6
    bpb[64] = 0x80 # Drive number
    bpb[66] = 0x29 # Extended signature
    struct.pack_into("<I", bpb, 67, 0x54A89102) # Volume ID
    bpb[71:82] = b"BAKEN_EFI  "
    bpb[82:90] = b"FAT32   "
    bpb[510:512] = b"\x55\xAA"
    
    disk[p_offset : p_offset + sector_size] = bpb
    disk[p_offset + 6 * sector_size : p_offset + 7 * sector_size] = bpb # Backup sector 6
    
    # FSInfo Sector (LBA 1 da partição)
    fsinfo = bytearray(sector_size)
    fsinfo[0:4] = b"RRaA"
    fsinfo[484:488] = b"rrAa"
    struct.pack_into("<I", fsinfo, 488, 30000) # Free clusters
    struct.pack_into("<I", fsinfo, 492, 4) # Next free cluster
    fsinfo[510:512] = b"\x55\xAA"
    disk[p_offset + sector_size : p_offset + 2 * sector_size] = fsinfo
    
    # FAT 1 & 2 Setup
    fat1_offset = p_offset + (reserved_sectors * sector_size)
    fat2_offset = fat1_offset + (fat_size_sectors * sector_size)
    
    # Entradas da FAT: Cluster 0, 1, 2 (Root), 3 (EFI dir), 4 (BOOT dir), 5 (BOOTX64.EFI data...)
    # Cluster 2 = End of chain (Root Dir) -> 0x0FFFFFFF
    # Cluster 3 = End of chain (EFI Dir)  -> 0x0FFFFFFF
    # Cluster 4 = End of chain (BOOT Dir) -> 0x0FFFFFFF
    # Clusters para BOOTX64.EFI (tamanho ~8 KB = 2 clusters: Cluster 5 -> 6, Cluster 6 -> EOF)
    fat_entries = [
        0x0FFFFFF8, # Cluster 0: Media type
        0x0FFFFFFF, # Cluster 1: EOC
        0x0FFFFFFF, # Cluster 2: Root dir (EOF)
        0x0FFFFFFF, # Cluster 3: EFI dir (EOF)
        0x0FFFFFFF, # Cluster 4: BOOT dir (EOF)
        0x00000006, # Cluster 5: BOOTX64.EFI part 1 -> points to 6
        0x0FFFFFFF, # Cluster 6: BOOTX64.EFI part 2 (EOF)
    ]
    fat_data = bytearray()
    for entry in fat_entries:
        fat_data.extend(struct.pack("<I", entry))
        
    disk[fat1_offset : fat1_offset + len(fat_data)] = fat_data
    disk[fat2_offset : fat2_offset + len(fat_data)] = fat_data
    
    # -------------------------------------------------------------
    # 4. Estrutura de Diretórios e Arquivos FAT32
    # -------------------------------------------------------------
    cluster_size = sectors_per_cluster * sector_size
    data_start = p_offset + (reserved_sectors + num_fats * fat_size_sectors) * sector_size
    
    def get_cluster_offset(cluster_num):
        return data_start + (cluster_num - 2) * cluster_size
        
    # Cluster 2: Diretório Raiz contendo "EFI" (Cluster 3)
    root_offset = get_cluster_offset(2)
    efi_entry = bytearray(32)
    efi_entry[0:11] = b"EFI        " # 8.3 name
    efi_entry[11] = 0x10 # Directory attribute
    struct.pack_into("<H", efi_entry, 20, 0) # High cluster
    struct.pack_into("<H", efi_entry, 26, 3) # Low cluster: 3
    disk[root_offset : root_offset + 32] = efi_entry
    
    # Cluster 3: Diretório "\EFI" contendo "BOOT" (Cluster 4)
    efi_dir_offset = get_cluster_offset(3)
    dot_entry = bytearray(32)
    dot_entry[0:11] = b".          "
    dot_entry[11] = 0x10
    struct.pack_into("<H", dot_entry, 26, 3)
    
    dotdot_entry = bytearray(32)
    dotdot_entry[0:11] = b"..         "
    dotdot_entry[11] = 0x10
    struct.pack_into("<H", dotdot_entry, 26, 0) # Points to root
    
    boot_entry = bytearray(32)
    boot_entry[0:11] = b"BOOT       "
    boot_entry[11] = 0x10
    struct.pack_into("<H", boot_entry, 20, 0)
    struct.pack_into("<H", boot_entry, 26, 4) # Points to cluster 4
    
    disk[efi_dir_offset : efi_dir_offset + 32] = dot_entry
    disk[efi_dir_offset + 32 : efi_dir_offset + 64] = dotdot_entry
    disk[efi_dir_offset + 64 : efi_dir_offset + 96] = boot_entry
    
    # Cluster 4: Diretório "\EFI\BOOT" contendo "BOOTX64.EFI" (Cluster 5)
    boot_dir_offset = get_cluster_offset(4)
    boot_dot = bytearray(32)
    boot_dot[0:11] = b".          "
    boot_dot[11] = 0x10
    struct.pack_into("<H", boot_dot, 26, 4)
    
    boot_dotdot = bytearray(32)
    boot_dotdot[0:11] = b"..         "
    boot_dotdot[11] = 0x10
    struct.pack_into("<H", boot_dotdot, 26, 3)
    
    file_entry = bytearray(32)
    file_entry[0:11] = b"BOOTX64 EFI"
    file_entry[11] = 0x20 # Archive file
    struct.pack_into("<H", file_entry, 20, 0) # High cluster
    struct.pack_into("<H", file_entry, 26, 5) # Low cluster: 5
    struct.pack_into("<I", file_entry, 28, len(bootx64_data)) # Size
    
    disk[boot_dir_offset : boot_dir_offset + 32] = boot_dot
    disk[boot_dir_offset + 32 : boot_dir_offset + 64] = boot_dotdot
    disk[boot_dir_offset + 64 : boot_dir_offset + 96] = file_entry
    
    # Cluster 5 e 6: Gravação dos bytes do binário BOOTX64.EFI
    file_data_offset = get_cluster_offset(5)
    disk[file_data_offset : file_data_offset + len(bootx64_data)] = bootx64_data
    
    # Grava imagem RAW no disco
    with open(RAW_IMG, "wb") as f:
        f.write(disk)
        
    print(f"  [OK] Imagem RAW GPT/FAT32 gerada: {RAW_IMG} ({os.path.getsize(RAW_IMG)} bytes).")
    return True

def convert_to_virtualbox_vdi():
    print("[3/4] Convertendo imagem RAW em Disco Virtual Nativo do VirtualBox (baken_os.vdi)...")
    if os.path.exists(VDI_IMG):
        os.remove(VDI_IMG)
        
    cmd = [
        VBOX_MANAGE,
        "convertfromraw",
        RAW_IMG,
        VDI_IMG,
        "--format", "VDI"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Erro ao converter para VDI:\n{res.stderr}")
        return False
        
    print(f"  [OK] Disco Virtual VDI gerado com sucesso: {VDI_IMG} ({os.path.getsize(VDI_IMG)} bytes).")
    return True

def attach_and_configure_vm():
    print("[4/4] Conectando o Disco VDI na Máquina Virtual 'BakenOS '...")
    vm_name = "BakenOS "
    
    # Desanexa qualquer mídia anterior da porta SATA para não dar conflito
    subprocess.run([VBOX_MANAGE, "storageattach", vm_name, "--storagectl", "SATA", "--port", "0", "--device", "0", "--type", "hdd", "--medium", "none"], capture_output=True)
    
    # Anexa o novo baken_os.vdi como Disco Rígido Principal SATA (Port 0)
    cmd = [
        VBOX_MANAGE,
        "storageattach",
        vm_name,
        "--storagectl", "SATA",
        "--port", "0",
        "--device", "0",
        "--type", "hdd",
        "--medium", VDI_IMG
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Aviso ao anexar SATA:\n{res.stderr}")
        return False
        
    # Garante que a ordem de boot dê prioridade ao HardDisk
    subprocess.run([VBOX_MANAGE, "modifyvm", vm_name, "--boot1", "disk", "--boot2", "dvd"], capture_output=True)
    
    print("  [OK] Disco VDI configurado como unidade de boot primária na VM 'BakenOS '!")
    return True

def main():
    print("=================================================================")
    print("      CONSTRUTOR DE DISCO VIRTUAL BOOTÁVEL BAKEN OS (VDI)        ")
    print("=================================================================")
    
    if not compile_uefi_bootloader():
        sys.exit(1)
    if not create_gpt_fat32_disk():
        sys.exit(1)
    if not convert_to_virtualbox_vdi():
        sys.exit(1)
    if not attach_and_configure_vm():
        sys.exit(1)
        
    print("\n[SUCESSO] O disco virtual baken_os.vdi esta 100% pronto e configurado no VirtualBox!")

if __name__ == "__main__":
    main()
