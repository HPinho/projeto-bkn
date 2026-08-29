#!/usr/bin/env python3
"""Cria uma instalação Baken OS em um disco virtual descartável.

O arquivo produzido possui GPT, ESP FAT32 e uma partição de dados Baken. Ele
é deliberadamente um artefato de build: este script só aceita caminhos dentro
do diretório ``build`` para nunca particionar um disco físico por engano.
"""

from __future__ import annotations

import argparse
import os
import struct
import uuid
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build"
SECTOR_SIZE = 512
TOTAL_SECTORS = 131_072  # 64 MiB
ESP_FIRST_LBA = 2_048
ESP_LAST_LBA = 86_015    # 41 MiB, suficiente para FAT32 válida
DATA_FIRST_LBA = ESP_LAST_LBA + 1
DATA_LAST_LBA = TOTAL_SECTORS - 34
GPT_ENTRY_FIRST_LBA = 2
GPT_ENTRY_COUNT = 128
GPT_ENTRY_SIZE = 128
GPT_ENTRIES_SECTORS = 32
ESP_TYPE_GUID = uuid.UUID("c12a7328-f81f-11d2-ba4b-00a0c93ec93b")
BAKEN_DATA_GUID = uuid.UUID("7f3c7258-2f1c-4e03-bf20-42414b454e31")
BAKENFS_MAGIC = b"BAKENFS1"


def guid_le(value: uuid.UUID) -> bytes:
    return value.bytes_le


def put_utf16_name(target: bytearray, offset: int, name: str) -> None:
    encoded = name.encode("utf-16le")[:72]
    target[offset : offset + len(encoded)] = encoded


def assert_build_output(path: Path) -> None:
    resolved = path.resolve()
    build = BUILD.resolve()
    if resolved != build and build not in resolved.parents:
        raise ValueError(f"por segurança, a imagem deve ficar dentro de {build}")


def write_gpt(disk: bytearray) -> None:
    disk[446 + 4] = 0xEE
    struct.pack_into("<II", disk, 446 + 8, 1, min(TOTAL_SECTORS - 1, 0xFFFFFFFF))
    disk[510:512] = b"\x55\xaa"

    entries = bytearray(GPT_ENTRY_COUNT * GPT_ENTRY_SIZE)
    entries[0:16] = guid_le(ESP_TYPE_GUID)
    entries[16:32] = guid_le(uuid.uuid5(uuid.NAMESPACE_URL, "baken-os-esp-v1"))
    struct.pack_into("<QQQ", entries, 32, ESP_FIRST_LBA, ESP_LAST_LBA, 0)
    put_utf16_name(entries, 56, "Baken ESP")
    base = GPT_ENTRY_SIZE
    entries[base : base + 16] = guid_le(BAKEN_DATA_GUID)
    entries[base + 16 : base + 32] = guid_le(uuid.uuid5(uuid.NAMESPACE_URL, "baken-os-data-v1"))
    struct.pack_into("<QQQ", entries, base + 32, DATA_FIRST_LBA, DATA_LAST_LBA, 0)
    put_utf16_name(entries, base + 56, "Baken Data")
    entries_crc = zlib.crc32(entries) & 0xFFFFFFFF
    disk[GPT_ENTRY_FIRST_LBA * SECTOR_SIZE : (GPT_ENTRY_FIRST_LBA + GPT_ENTRIES_SECTORS) * SECTOR_SIZE] = entries
    backup_entries_lba = TOTAL_SECTORS - 33
    disk[backup_entries_lba * SECTOR_SIZE : (backup_entries_lba + GPT_ENTRIES_SECTORS) * SECTOR_SIZE] = entries

    disk_guid = guid_le(uuid.uuid5(uuid.NAMESPACE_URL, "baken-os-disk-v1"))

    def header(current_lba: int, backup_lba: int, entries_lba: int) -> bytes:
        header = bytearray(SECTOR_SIZE)
        header[0:8] = b"EFI PART"
        struct.pack_into("<IIII", header, 8, 0x00010000, 92, 0, 0)
        struct.pack_into("<QQ", header, 24, current_lba, backup_lba)
        struct.pack_into("<QQ", header, 40, 34, TOTAL_SECTORS - 34)
        header[56:72] = disk_guid
        struct.pack_into("<QIII", header, 72, entries_lba, GPT_ENTRY_COUNT, GPT_ENTRY_SIZE, entries_crc)
        struct.pack_into("<I", header, 16, zlib.crc32(header[:92]) & 0xFFFFFFFF)
        return bytes(header)

    disk[SECTOR_SIZE : 2 * SECTOR_SIZE] = header(1, TOTAL_SECTORS - 1, GPT_ENTRY_FIRST_LBA)
    disk[(TOTAL_SECTORS - 1) * SECTOR_SIZE : TOTAL_SECTORS * SECTOR_SIZE] = header(TOTAL_SECTORS - 1, 1, backup_entries_lba)


def write_fat32_esp(disk: bytearray, efi_data: bytes) -> None:
    part_sectors = ESP_LAST_LBA - ESP_FIRST_LBA + 1
    fat_sectors, reserved, fats = 656, 32, 2
    first_data = reserved + fats * fat_sectors
    cluster_count = part_sectors - first_data
    if cluster_count < 65_525:
        raise RuntimeError("ESP pequena demais para FAT32")
    clusters_for_efi = (len(efi_data) + SECTOR_SIZE - 1) // SECTOR_SIZE
    if clusters_for_efi == 0 or 4 + clusters_for_efi >= cluster_count:
        raise ValueError("BOOTX64.EFI não cabe na ESP FAT32")
    part = ESP_FIRST_LBA * SECTOR_SIZE
    vbr = memoryview(disk)[part : part + SECTOR_SIZE]
    vbr[0:3], vbr[3:11] = b"\xeb\x58\x90", b"BAKENEFI"
    struct.pack_into("<H", vbr, 11, SECTOR_SIZE)
    vbr[13], = (1,)
    struct.pack_into("<H", vbr, 14, reserved)
    vbr[16] = fats
    struct.pack_into("<H", vbr, 17, 0)
    struct.pack_into("<H", vbr, 19, 0)
    vbr[21] = 0xF8
    struct.pack_into("<H", vbr, 22, 0)
    struct.pack_into("<I", vbr, 32, part_sectors)
    struct.pack_into("<I", vbr, 36, fat_sectors)
    struct.pack_into("<H", vbr, 40, 0)
    struct.pack_into("<H", vbr, 42, 0)
    struct.pack_into("<I", vbr, 44, 2)
    struct.pack_into("<H", vbr, 48, 1)
    struct.pack_into("<H", vbr, 50, 6)
    vbr[64], vbr[66] = 0x80, 0x29
    struct.pack_into("<I", vbr, 67, 0xBA1CE002)
    vbr[71:82], vbr[82:90] = b"BAKEN_ESP  ", b"FAT32   "
    vbr[510:512] = b"\x55\xaa"
    disk[(ESP_FIRST_LBA + 6) * SECTOR_SIZE : (ESP_FIRST_LBA + 7) * SECTOR_SIZE] = vbr

    fat_offset = (ESP_FIRST_LBA + reserved) * SECTOR_SIZE
    for fat_index in range(fats):
        fat = memoryview(disk)[fat_offset + fat_index * fat_sectors * SECTOR_SIZE : fat_offset + (fat_index + 1) * fat_sectors * SECTOR_SIZE]
        struct.pack_into("<III", fat, 0, 0x0FFFFFF8, 0xFFFFFFFF, 0x0FFFFFFF)
        struct.pack_into("<I", fat, 3 * 4, 0x0FFFFFFF)  # EFI
        struct.pack_into("<I", fat, 4 * 4, 0x0FFFFFFF)  # BOOT
        for cluster in range(5, 5 + clusters_for_efi):
            struct.pack_into("<I", fat, cluster * 4, 0x0FFFFFFF if cluster == 4 + clusters_for_efi else cluster + 1)

    data_lba = ESP_FIRST_LBA + first_data
    def entry(cluster: int, name: bytes, attr: int, first_cluster: int, size: int = 0) -> None:
        offset = (data_lba + cluster - 2) * SECTOR_SIZE
        disk[offset : offset + 11] = name
        disk[offset + 11] = attr
        struct.pack_into("<H", disk, offset + 20, first_cluster >> 16)
        struct.pack_into("<H", disk, offset + 26, first_cluster & 0xFFFF)
        struct.pack_into("<I", disk, offset + 28, size)
    entry(2, b"EFI        ", 0x10, 3)
    entry(3, b"BOOT       ", 0x10, 4)
    entry(4, b"BOOTX64 EFI", 0x20, 5, len(efi_data))
    file_offset = (data_lba + 5 - 2) * SECTOR_SIZE
    disk[file_offset : file_offset + len(efi_data)] = efi_data


def write_baken_data_marker(disk: bytearray) -> None:
    offset = DATA_FIRST_LBA * SECTOR_SIZE
    # Cabeçalho BakenFS v1: duas pastas e dois arquivos em setores estáveis.
    disk[offset : offset + 8] = BAKENFS_MAGIC
    struct.pack_into("<II", disk, offset + 8, 1, 4)
    entries = (("/home", 0, 0, 1), ("/config", 0, 0, 1),
               ("/home/notas.txt", DATA_FIRST_LBA + 2, 512, 2),
               ("/config/theme.cfg", DATA_FIRST_LBA + 1, 512, 2))
    for index, (name, lba, size, kind) in enumerate(entries):
        entry = offset + 16 + index * 44
        disk[entry : entry + 32] = name.encode("utf-8").ljust(32, b"\0")
        struct.pack_into("<III", disk, entry + 32, lba, size, kind)
    # Preferências: tema 0 e usuário padrão.
    preferences = (DATA_FIRST_LBA + 1) * SECTOR_SIZE
    struct.pack_into("<I", disk, preferences, 0)
    disk[preferences + 4 : preferences + 36] = b"Usuario".ljust(32, b"\0")
    # notas.txt usa o mesmo layout de 512 bytes aceito pelo kernel.
    notes = (DATA_FIRST_LBA + 2) * SECTOR_SIZE
    struct.pack_into("<QII", disk, notes, 0x31544E4E454B4142, 1, 1)  # BAKENNT1
    disk[notes + 16 : notes + 48] = b"Notas".ljust(32, b"\0")


def create_installed_disk(output_img: str | Path, efi_bin_path: str | Path) -> Path:
    output, efi = Path(output_img), Path(efi_bin_path)
    assert_build_output(output)
    if not efi.is_file():
        raise FileNotFoundError(f"BOOTX64.EFI obrigatório não encontrado: {efi}")
    efi_data = efi.read_bytes()
    if not efi_data.startswith(b"MZ"):
        raise ValueError("BOOTX64.EFI não é um executável PE/COFF válido")
    disk = bytearray(TOTAL_SECTORS * SECTOR_SIZE)
    write_gpt(disk)
    write_fat32_esp(disk, efi_data)
    write_baken_data_marker(disk)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(disk)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cria uma instalação Baken OS em disco virtual GPT/FAT32")
    parser.add_argument("--output", type=Path, default=BUILD / "baken_installed.img")
    parser.add_argument("--efi", type=Path, default=BUILD / "iso_root" / "EFI" / "BOOT" / "BOOTX64.EFI")
    args = parser.parse_args()
    image = create_installed_disk(args.output, args.efi)
    print(f"[OK] Disco GPT/FAT32 instalado criado em: {image}")
