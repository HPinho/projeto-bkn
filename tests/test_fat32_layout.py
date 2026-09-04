#!/usr/bin/env python3
"""Contratos do planejamento FAT32 da EFI System Partition."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAT32 = ROOT / "kernel/src/storage/fat32.sotlas"
ENGINE = ROOT / "kernel/src/install_engine.sotlas"


class Fat32LayoutTests(unittest.TestCase):
    def test_layout_contains_required_fat32_metadata(self):
        text = FAT32.read_text(encoding="utf-8")
        for token in (
            "FAT32_RESERVED_SECTORS",
            "FAT32_FAT_COUNT",
            "FAT32_ROOT_CLUSTER",
            "FAT32_FSINFO_SECTOR",
            "FAT32_BACKUP_BOOT_SECTOR",
            "fat_size_sectors",
        ):
            self.assertIn(token, text)

    def test_cluster_geometry_depends_on_bytes_per_sector(self):
        text = FAT32.read_text(encoding="utf-8")
        self.assertIn("cluster_bytes / bytes_per_sector", text)
        self.assertIn("bytes_per_sector > 4096", text)
        self.assertIn("fat32_is_power_of_two", text)

    def test_fat_size_is_solved_from_cluster_count(self):
        text = FAT32.read_text(encoding="utf-8")
        self.assertIn("fat_entries = clusters + 2", text)
        self.assertIn("fat_bytes = fat_entries * 4", text)
        self.assertIn("for mut pass in 0..16", text)

    def test_install_engine_requires_gpt_and_fat32_before_available(self):
        text = ENGINE.read_text(encoding="utf-8")
        self.assertIn("gpt_plan_default", text)
        self.assertIn("fat32_plan_layout", text)
        self.assertIn("INSTALL_ESP_BYTES", text)
        self.assertIn("if !fat.valid", text)

    def test_planner_does_not_claim_physical_formatting(self):
        text = FAT32.read_text(encoding="utf-8")
        self.assertNotIn("WriteBlocks", text)
        self.assertNotIn("block_device_write", text)


if __name__ == "__main__":
    unittest.main()
