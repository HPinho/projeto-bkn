#!/usr/bin/env python3
"""Contratos do BakenFS persistente na imagem instalada."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class StorageInstallerTests(unittest.TestCase):
    def test_kernel_and_installed_builder_share_the_bakenfs_layout(self):
        bridge_c = (ROOT / "kernel/src/baken_kernel_all.c").read_text(encoding="utf-8")
        disk_builder = (ROOT / "tools/scripts/create_installed_disk.py").read_text(encoding="utf-8")
        self.assertRegex(bridge_c, r"BAKENFS_DATA_LBA\s+86016")
        self.assertIn("BAKENFS_MAGIC", bridge_c)
        self.assertIn("bakenfs_mount", bridge_c)
        self.assertIn("bakenfs_save_preferences", bridge_c)
        self.assertIn("bakenfs_save_notes", bridge_c)
        self.assertIn("DATA_FIRST_LBA = ESP_LAST_LBA + 1", disk_builder)
        self.assertIn('BAKENFS_MAGIC = b"BAKENFS1"', disk_builder)
        self.assertIn('"/home/notas.txt"', disk_builder)

    def test_installer_initializes_bakenfs_data(self):
        bridge_c = (ROOT / "kernel/src/baken_kernel_all.c").read_text(encoding="utf-8")
        self.assertIn("BakenFsHeader", bridge_c)
        self.assertIn("g_bakenfs.magic=BAKENFS_MAGIC", bridge_c)
        self.assertIn("INSTALL_DATA_FIRST+2", bridge_c)
        self.assertIn("/config/theme.cfg", bridge_c)
        self.assertIn("/home/notas.txt", bridge_c)

    def test_bootloader_recognizes_installed_gpt_as_its_own_boot_media(self):
        bootloader = (ROOT / "boot/uefi_bootloader.cq").read_text(encoding="utf-8")
        self.assertIn("GUID de tipo Baken Data", bootloader)
        self.assertIn("sector[0]!='E'", bootloader)
        self.assertIn("data_guid", bootloader)


if __name__ == "__main__":
    unittest.main()
