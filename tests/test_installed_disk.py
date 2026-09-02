"""Valida o disco GPT/FAT32 usado como instalação virtual do Baken OS."""

import importlib.util
import struct
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installed_disk", ROOT / "tools/scripts/create_installed_disk.py")
assert spec is not None and spec.loader is not None
installed_disk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installed_disk)


class InstalledDiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / "build").mkdir(parents=True, exist_ok=True)

    def test_builder_creates_bootable_gpt_fat32_layout(self):
        efi = ROOT / "build" / "installed-disk-contract.efi"
        output = ROOT / "build" / "installed-disk-contract.img"
        efi.write_bytes(b"MZ" + b"Baken EFI test payload")
        try:
            installed_disk.create_installed_disk(output, efi)
            disk = output.read_bytes()
        finally:
            output.unlink(missing_ok=True)
            efi.unlink(missing_ok=True)

        self.assertEqual(len(disk), installed_disk.TOTAL_SECTORS * installed_disk.SECTOR_SIZE)
        self.assertEqual(disk[510:512], b"\x55\xaa")
        self.assertEqual(disk[512:520], b"EFI PART")
        header = bytearray(disk[512:604])
        header_crc = struct.unpack_from("<I", header, 16)[0]
        struct.pack_into("<I", header, 16, 0)
        self.assertEqual(zlib.crc32(header) & 0xFFFFFFFF, header_crc)
        self.assertEqual(struct.unpack_from("<Q", disk, 512 + 72)[0], 2)
        esp = installed_disk.ESP_FIRST_LBA * installed_disk.SECTOR_SIZE
        self.assertEqual(disk[esp + 82 : esp + 90], b"FAT32   ")
        data = installed_disk.DATA_FIRST_LBA * installed_disk.SECTOR_SIZE
        self.assertEqual(disk[data : data + len(installed_disk.BAKENFS_MAGIC)], installed_disk.BAKENFS_MAGIC)
        header = disk[data : data + 512]
        self.assertEqual(struct.unpack_from("<II", header, 8), (1, 4))
        self.assertIn(b"/home", header)
        self.assertIn(b"/config", header)
        self.assertIn(b"/home/notas.txt", header)
        self.assertIn(b"/config/theme.cfg", header)
        preferences = data + installed_disk.SECTOR_SIZE
        self.assertEqual(struct.unpack_from("<I", disk, preferences)[0], 0)
        notes = data + 2 * installed_disk.SECTOR_SIZE
        self.assertEqual(struct.unpack_from("<QII", disk, notes), (0x31544E4E454B4142, 1, 1))

    def test_builder_refuses_output_outside_build_directory(self):
        efi = ROOT / "build" / "installed-disk-contract.efi"
        efi.write_bytes(b"MZtest")
        try:
            with self.assertRaises(ValueError):
                installed_disk.create_installed_disk(ROOT.parent / "unsafe.img", efi)
        finally:
            efi.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
