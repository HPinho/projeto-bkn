#!/usr/bin/env python3
"""Create the synthetic 64MiB GPT/FAT32 disk used only by Baken CI.

The image is a regular file created by this script. It is never pointed at a
physical block device. `--nvme` places the guarded BAKENNV1 sentinel at LBA
1024 after the common GPT/FAT32 foundation fixture is built.
"""

import argparse
from pathlib import Path
import struct
import zlib

from extend_foundation_fixture import extend

BLOCK_SIZE = 512
IMAGE_SIZE = 64 * 1024 * 1024
ESP_FIRST = 2048
ESP_LAST = 100000


def build_base(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as image:
        image.truncate(IMAGE_SIZE)

    last_lba = IMAGE_SIZE // BLOCK_SIZE - 1
    entry_count = 128
    entry_size = 128
    entries = bytearray(entry_count * entry_size)
    type_guid = bytes.fromhex("28732ac11ff8d211ba4b00a0c93ec93b")
    unique_guid = bytes.fromhex("78563412341278569abcdef012345678")
    disk_guid = bytes.fromhex("00112233445566778899aabbccddeeff")
    name = "BAKEN TEST".encode("utf-16le")
    name += bytes(72 - len(name))
    struct.pack_into(
        "<16s16sQQQ72s", entries, 0,
        type_guid, unique_guid, ESP_FIRST, ESP_LAST, 0, name,
    )
    entry_blocks = len(entries) // BLOCK_SIZE
    primary_entries_lba = 2
    backup_entries_lba = last_lba - entry_blocks
    first_usable = ESP_FIRST
    last_usable = backup_entries_lba - 1
    if ESP_LAST > last_usable:
        raise ValueError("ESP does not fit fixture")
    entries_crc = zlib.crc32(entries) & 0xFFFFFFFF

    def header(current_lba: int, backup_lba: int, entries_lba: int) -> bytearray:
        data = bytearray(BLOCK_SIZE)
        struct.pack_into(
            "<8sIIIIQQQQ16sQIII", data, 0,
            b"EFI PART", 0x00010000, 92, 0, 0,
            current_lba, backup_lba, first_usable, last_usable,
            disk_guid, entries_lba, entry_count, entry_size, entries_crc,
        )
        struct.pack_into("<I", data, 16, zlib.crc32(data[:92]) & 0xFFFFFFFF)
        return data

    primary_header = header(1, last_lba, primary_entries_lba)
    backup_header = header(last_lba, 1, backup_entries_lba)

    esp_total = ESP_LAST - ESP_FIRST + 1
    reserved = 32
    fat_count = 2
    sectors_per_cluster = 1
    fat_size = 1
    for _ in range(16):
        data_sectors = esp_total - reserved - fat_count * fat_size
        cluster_count = data_sectors // sectors_per_cluster
        needed = ((cluster_count + 2) * 4 + BLOCK_SIZE - 1) // BLOCK_SIZE
        if needed == fat_size:
            break
        fat_size = needed
    data_sectors = esp_total - reserved - fat_count * fat_size
    cluster_count = data_sectors // sectors_per_cluster
    if cluster_count < 65525 or fat_size != 754:
        raise ValueError("unexpected FAT32 fixture geometry")
    data_start_lba = ESP_FIRST + reserved + fat_count * fat_size

    boot = bytearray(BLOCK_SIZE)
    boot[0:3] = b"\xEB\x58\x90"
    boot[3:11] = b"BAKENOS "
    struct.pack_into("<H", boot, 11, BLOCK_SIZE)
    boot[13] = sectors_per_cluster
    struct.pack_into("<H", boot, 14, reserved)
    boot[16] = fat_count
    boot[21] = 0xF8
    struct.pack_into("<H", boot, 24, 63)
    struct.pack_into("<H", boot, 26, 255)
    struct.pack_into("<I", boot, 28, ESP_FIRST)
    struct.pack_into("<I", boot, 32, esp_total)
    struct.pack_into("<I", boot, 36, fat_size)
    struct.pack_into("<I", boot, 44, 2)
    struct.pack_into("<H", boot, 48, 1)
    struct.pack_into("<H", boot, 50, 6)
    boot[64] = 0x80
    boot[66] = 0x29
    struct.pack_into("<I", boot, 67, 0xBA4E2026)
    boot[71:82] = b"BAKEN ESP  "
    boot[82:90] = b"FAT32   "
    boot[510:512] = b"\x55\xAA"

    fsinfo = bytearray(BLOCK_SIZE)
    struct.pack_into("<I", fsinfo, 0, 0x41615252)
    struct.pack_into("<I", fsinfo, 484, 0x61417272)
    struct.pack_into("<I", fsinfo, 488, 0xFFFFFFFF)
    struct.pack_into("<I", fsinfo, 492, 0xFFFFFFFF)
    struct.pack_into("<I", fsinfo, 508, 0xAA550000)

    fat_head = bytearray(BLOCK_SIZE)
    struct.pack_into("<I", fat_head, 0, 0x0FFFFFF8)
    struct.pack_into("<I", fat_head, 4, 0xFFFFFFFF)
    struct.pack_into("<I", fat_head, 8, 0x0FFFFFFF)
    struct.pack_into("<I", fat_head, 12, 0x0FFFFFFF)

    root = bytearray(BLOCK_SIZE)
    root[0:11] = b"BAKEN   TXT"
    root[11] = 0x20
    struct.pack_into("<H", root, 26, 3)
    struct.pack_into("<I", root, 28, 8)
    root[32] = 0

    file_data = bytearray(BLOCK_SIZE)
    file_data[:8] = b"BAKENOS\n"

    with path.open("r+b") as image:
        image.seek(primary_entries_lba * BLOCK_SIZE)
        image.write(entries)
        image.seek(BLOCK_SIZE)
        image.write(primary_header)
        image.seek(backup_entries_lba * BLOCK_SIZE)
        image.write(entries)
        image.seek(last_lba * BLOCK_SIZE)
        image.write(backup_header)
        image.seek(ESP_FIRST * BLOCK_SIZE)
        image.write(boot)
        image.seek((ESP_FIRST + 1) * BLOCK_SIZE)
        image.write(fsinfo)
        image.seek((ESP_FIRST + 6) * BLOCK_SIZE)
        image.write(boot)
        image.seek((ESP_FIRST + 7) * BLOCK_SIZE)
        image.write(fsinfo)
        image.seek((ESP_FIRST + reserved) * BLOCK_SIZE)
        image.write(fat_head)
        image.seek((ESP_FIRST + reserved + fat_size) * BLOCK_SIZE)
        image.write(fat_head)
        image.seek(data_start_lba * BLOCK_SIZE)
        image.write(root)
        image.seek((data_start_lba + sectors_per_cluster) * BLOCK_SIZE)
        image.write(file_data)


def build(path: Path, nvme: bool) -> None:
    build_base(path)
    extend(path)
    if nvme:
        with path.open("r+b") as image:
            image.seek(1024 * BLOCK_SIZE)
            image.write(b"BAKENNV1")
    with path.open("rb") as image:
        image.seek(BLOCK_SIZE)
        if image.read(8) != b"EFI PART":
            raise ValueError("primary GPT missing")
        image.seek(ESP_FIRST * BLOCK_SIZE + 82)
        if image.read(8) != b"FAT32   ":
            raise ValueError("FAT32 fixture missing")
        if nvme:
            image.seek(1024 * BLOCK_SIZE)
            if image.read(8) != b"BAKENNV1":
                raise ValueError("NVMe sentinel missing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--nvme", action="store_true")
    args = parser.parse_args()
    build(args.image, args.nvme)
