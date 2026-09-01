#!/usr/bin/env python3
"""Instala Baken OS em uma imagem virtual do diretório build com troca segura."""

from __future__ import annotations

import argparse
import importlib.util
import os
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build"
spec = importlib.util.spec_from_file_location("installed_disk", ROOT / "tools/scripts/create_installed_disk.py")
assert spec is not None and spec.loader is not None
installed_disk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installed_disk)


def verify(image: Path) -> None:
    data = image.read_bytes()
    if data[512:520] != b"EFI PART":
        raise ValueError("GPT primário ausente")
    header = bytearray(data[512:604])
    expected = struct.unpack_from("<I", header, 16)[0]
    struct.pack_into("<I", header, 16, 0)
    if zlib.crc32(header) & 0xFFFFFFFF != expected:
        raise ValueError("CRC do GPT inválido")
    esp = installed_disk.ESP_FIRST_LBA * installed_disk.SECTOR_SIZE
    if data[esp + 82 : esp + 90] != b"FAT32   ":
        raise ValueError("ESP FAT32 ausente")
    if b"BOOTX64 EFI" not in data[esp : esp + 2 * 1024 * 1024]:
        raise ValueError("BOOTX64.EFI ausente da ESP")
    data_lba = installed_disk.DATA_FIRST_LBA * installed_disk.SECTOR_SIZE
    if data[data_lba : data_lba + len(installed_disk.BAKENFS_MAGIC)] != installed_disk.BAKENFS_MAGIC:
        raise ValueError("volume BakenFS ausente")


def install(target: Path, efi: Path) -> Path:
    installed_disk.assert_build_output(target)
    staging = target.with_suffix(target.suffix + ".new")
    installed_disk.assert_build_output(staging)
    staging.unlink(missing_ok=True)
    installed_disk.create_installed_disk(staging, efi)
    verify(staging)
    os.replace(staging, target)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instala Baken OS em imagem virtual GPT/FAT32")
    parser.add_argument("--target", type=Path, default=BUILD / "baken_install_target.img")
    parser.add_argument("--efi", type=Path, default=BUILD / "iso_root" / "EFI" / "BOOT" / "BOOTX64.EFI")
    args = parser.parse_args()
    print(f"[OK] Instalação virtual concluída: {install(args.target, args.efi)}")
