#!/usr/bin/env python3
"""Guardrails do gate de redundância GPT primary/backup."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REDUNDANCY = ROOT / "kernel/src/storage/gpt_redundancy.sotlas"
GPT = ROOT / "kernel/src/storage/gpt.sotlas"
AHCI = ROOT / "kernel/src/drivers/ahci_block_read.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class GptRedundancyTests(unittest.TestCase):
    def test_redundancy_reads_primary_and_backup_headers_through_block_api(self):
        text = REDUNDANCY.read_text(encoding="utf-8")
        for token in (
            "GPT_PRIMARY_HEADER_LBA: u64 = 1",
            "block_device_read_sector(expected_last_lba, sector)",
            "block_device_read_sector(GPT_PRIMARY_HEADER_LBA, sector)",
            "gpt_redundancy_header_crc_valid(sector)",
            "primary_current != GPT_PRIMARY_HEADER_LBA",
            "primary_peer != expected_last_lba",
            "backup_current != expected_last_lba",
            "backup_peer != GPT_PRIMARY_HEADER_LBA",
        ):
            self.assertIn(token, text)
        self.assertNotIn("block_device_write", text)
        self.assertNotIn("WriteBlocks", text)

    def test_headers_must_share_guid_geometry_and_entry_metadata(self):
        text = REDUNDANCY.read_text(encoding="utf-8")
        for token in (
            "primary_first != backup_first",
            "primary_last != backup_last",
            "gpt_redundancy_read_u32(primary, 56) != backup_guid0",
            "gpt_redundancy_read_u32(primary, 68) != backup_guid3",
            "primary_entry_count != backup_entry_count",
            "primary_entry_size != backup_entry_size",
            "primary_entries_crc != backup_entries_crc",
        ):
            self.assertIn(token, text)

    def test_primary_partition_entry_array_is_streamed_and_crc_checked(self):
        text = REDUNDANCY.read_text(encoding="utf-8")
        body = text.split("pub fn gpt_probe_primary_backup_redundancy", 1)[1]
        body = body.split("@system\npub fn gpt_probe_first_esp_partition", 1)[0]
        for token in (
            "while block < entries_blocks",
            "block_device_read_sector(lba, sector)",
            "crc32_ieee_begin()",
            "crc32_ieee_update(crc, sector as *const u8, bytes_this_sector as usize)",
            "let computed = crc32_ieee_finish(crc)",
            "computed != primary_entries_crc",
            "computed != expected_entries_crc32",
            "GPT_REDUNDANCY_READY = true",
            "x86_serial_write_stage_marker('n' as u8)",
        ):
            self.assertIn(token, body)
        self.assertLess(
            body.index("GPT_REDUNDANCY_READY = true"),
            body.index("x86_serial_write_stage_marker('n' as u8)"),
        )

    def test_backup_entry_probe_requires_redundancy_before_returning(self):
        text = GPT.read_text(encoding="utf-8")
        self.assertIn("import kernel::storage::gpt_redundancy::*;", text)
        body = text.split("pub fn gpt_probe_backup_entries()", 1)[1]
        body = body.split("pub fn gpt_runtime_is_ready", 1)[0]
        backup_ready = body.index("GPT_RUNTIME_ENTRIES_READY = true")
        redundancy = body.index("gpt_probe_primary_backup_redundancy(")
        ready_check = body.index("gpt_redundancy_is_ready()")
        self.assertLess(backup_ready, redundancy)
        self.assertLess(redundancy, ready_check)

    def test_write_probe_no_longer_collides_with_primary_gpt_metadata(self):
        text = AHCI.read_text(encoding="utf-8")
        self.assertIn("AHCI_WRITE_TEST_LBA: u64 = 1024", text)
        self.assertNotIn("AHCI_WRITE_TEST_LBA: u64 = 1;", text)

    def test_ci_seeds_both_gpt_copies_and_requires_redundancy_marker(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            "primary_entries_lba = 2",
            "primary_header = make_header(1, last_lba, primary_entries_lba)",
            "backup_header = make_header(last_lba, 1, entries_lba)",
            "image.seek(primary_entries_lba * block_size)",
            "image.write(primary_header)",
            "assert primary_entries == entries",
            "assert zlib.crc32(primary_entries) & 0xFFFFFFFF == expected_crc",
        ):
            self.assertIn(token, text)
        markers = text.split("for marker in ", 1)[1].split("; do", 1)[0]
        self.assertLess(markers.index("STEP=i"), markers.index("STEP=n"))
        self.assertLess(markers.index("STEP=n"), markers.index("STEP=t"))
        self.assertLess(markers.index("STEP=t"), markers.index("STEP=m"))
        self.assertLess(markers.index("STEP=m"), markers.index("STEP=J"))


if __name__ == "__main__":
    unittest.main()
