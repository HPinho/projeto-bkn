#!/usr/bin/env python3
"""Guardrails do gate FAT32 BPB lido da ESP GPT pelo Block Device nativo."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAT32 = ROOT / "kernel/src/storage/fat32.sotlas"
GPT = ROOT / "kernel/src/storage/gpt.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class Fat32RuntimeTests(unittest.TestCase):
    def test_probe_reads_gpt_published_esp_through_native_block_api(self):
        text = FAT32.read_text(encoding="utf-8")
        body = text.split("pub fn fat32_probe_esp_bpb()", 1)[1]
        body = body.split("pub fn fat32_runtime_is_ready", 1)[0]
        for token in (
            "gpt_partition_is_ready()",
            "gpt_partition_first_lba()",
            "gpt_partition_last_lba()",
            "block_device_has_native_target()",
            "block_device_block_size() != FAT32_RUNTIME_BLOCK_SIZE",
            "block_device_read_sector(first_lba, sector)",
        ):
            self.assertIn(token, body)
        self.assertNotIn("block_device_write", body)
        self.assertNotIn("WriteBlocks", body)

    def test_probe_validates_bpb_signature_and_fat32_geometry(self):
        text = FAT32.read_text(encoding="utf-8")
        self.assertIn("fn fat32_read_u8(base: *const u8, offset: usize) -> u8", text)
        body = text.split("pub fn fat32_probe_esp_bpb()", 1)[1]
        body = body.split("pub fn fat32_runtime_is_ready", 1)[0]
        for token in (
            "fat32_read_u8(base, 510) != 0x55",
            "fat32_read_u8(base, 511) != 0xAA",
            "let bytes_per_sector = fat32_read_u16(base, 11)",
            "let sectors_per_cluster = fat32_read_u8(base, 13) as u32",
            "let reserved_sectors = fat32_read_u16(base, 14)",
            "let fat_count = fat32_read_u8(base, 16) as u32",
            "let root_entry_count = fat32_read_u16(base, 17)",
            "let total_sectors16 = fat32_read_u16(base, 19)",
            "let fat_size16 = fat32_read_u16(base, 22)",
            "let total_sectors32 = fat32_read_u32(base, 32)",
            "let fat_size32 = fat32_read_u32(base, 36)",
            "let fs_version = fat32_read_u16(base, 42)",
            "let root_cluster = fat32_read_u32(base, 44)",
            "let fsinfo_sector = fat32_read_u16(base, 48)",
            "let backup_boot_sector = fat32_read_u16(base, 50)",
            "cluster_count < FAT32_MIN_CLUSTERS",
            "cluster_count > FAT32_MAX_CLUSTERS",
            "total_sectors > partition_sectors",
        ):
            self.assertIn(token, body)
        self.assertNotIn("let sectors_per_cluster = unsafe", body)
        self.assertNotIn("let fat_count = unsafe", body)

    def test_runtime_state_is_published_only_before_fat32_marker(self):
        text = FAT32.read_text(encoding="utf-8")
        body = text.split("pub fn fat32_probe_esp_bpb()", 1)[1]
        body = body.split("pub fn fat32_runtime_is_ready", 1)[0]
        for token in (
            "FAT32_RUNTIME_PARTITION_FIRST_LBA = first_lba",
            "FAT32_RUNTIME_PARTITION_LAST_LBA = last_lba",
            "FAT32_RUNTIME_FAT_SIZE_SECTORS = fat_size32",
            "FAT32_RUNTIME_CLUSTER_COUNT = cluster_count",
            "FAT32_RUNTIME_READY = true",
            "x86_serial_write_stage_marker('y' as u8)",
        ):
            self.assertIn(token, body)
        self.assertLess(
            body.index("FAT32_RUNTIME_READY = true"),
            body.index("x86_serial_write_stage_marker('y' as u8)"),
        )

    def test_gpt_chain_requires_fat32_probe_after_partition_gate(self):
        text = GPT.read_text(encoding="utf-8")
        self.assertIn("import kernel::storage::fat32::*;", text)
        body = text.split("pub fn gpt_probe_backup_entries()", 1)[1]
        body = body.split("pub fn gpt_runtime_is_ready", 1)[0]
        redundancy = body.index("gpt_probe_primary_backup_redundancy(")
        partition_ready = body.index("gpt_partition_is_ready()")
        fat_probe = body.index("fat32_probe_esp_bpb()")
        fat_ready = body.index("fat32_runtime_is_ready()")
        first_match = body.index("fat32_runtime_partition_first_lba() != gpt_partition_first_lba()")
        self.assertLess(redundancy, partition_ready)
        self.assertLess(partition_ready, fat_probe)
        self.assertLess(fat_probe, fat_ready)
        self.assertLess(fat_ready, first_match)

    def test_ci_seeds_valid_fat32_and_requires_runtime_marker(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            "esp_first = 2048",
            "esp_last = 100000",
            "reserved_sectors = 32",
            "fat_count = 2",
            "sectors_per_cluster = 1",
            "assert cluster_count >= 65525",
            "assert fat_size == 754",
            'boot[82:90] = b"FAT32   "',
            'boot[510:512] = b"\\x55\\xAA"',
            "image.seek(esp_first * block_size)",
            "image.write(boot)",
            "image.seek((esp_first + 6) * block_size)",
            "image.write(fsinfo)",
        ):
            self.assertIn(token, text)
        markers = text.split("for marker in ", 1)[1].split("; do", 1)[0]
        self.assertLess(markers.index("STEP=t"), markers.index("STEP=y"))
        self.assertLess(markers.index("STEP=y"), markers.index("STEP=m"))
        self.assertLess(markers.index("STEP=m"), markers.index("STEP=J"))


if __name__ == "__main__":
    unittest.main()
