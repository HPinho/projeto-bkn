#!/usr/bin/env python3
"""Contratos da geometria e do primeiro probe GPT nativo."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GPT = ROOT / "kernel/src/storage/gpt.sotlas"


class GptLayoutTests(unittest.TestCase):
    def test_layout_is_computed_from_block_size_not_fixed_lbas(self):
        text = GPT.read_text(encoding="utf-8")
        self.assertIn("entries_bytes", text)
        self.assertIn("gpt_div_ceil_u64(entries_bytes, block_size as u64)", text)
        self.assertIn("backup_entries = last_lba - entries_blocks", text)
        self.assertNotIn("lba <= 33", text)
        self.assertNotIn("LBAs 2–33", text)

    def test_primary_and_backup_gpt_are_both_planned(self):
        text = GPT.read_text(encoding="utf-8")
        for token in (
            "primary_header_lba",
            "primary_entries_lba",
            "backup_entries_lba",
            "backup_header_lba",
            "first_usable_lba",
            "last_usable_lba",
        ):
            self.assertIn(token, text)

    def test_protective_mbr_saturates_32_bit_sector_count(self):
        text = GPT.read_text(encoding="utf-8")
        self.assertIn("pub fn gpt_protective_mbr_sector_count", text)
        self.assertIn("if last_lba >= 0xFFFFFFFF", text)
        self.assertIn("return 0xFFFFFFFF;", text)

    def test_runtime_probe_reads_backup_header_only_through_block_api(self):
        text = GPT.read_text(encoding="utf-8")
        self.assertIn("import kernel::storage::block_device::*;", text)
        self.assertIn("import kernel::memory::dma::*;", text)
        body = text.split("pub fn gpt_probe_backup_header()", 1)[1]
        body = body.split("pub fn gpt_runtime_is_ready", 1)[0]
        for token in (
            "block_device_has_native_target()",
            "block_device_block_size() != GPT_RUNTIME_BLOCK_SIZE",
            "let last_lba = block_device_last_lba()",
            "block_device_read_sector(last_lba, sector)",
            "gpt_runtime_sector_buffer()",
            "dma_alloc(GPT_RUNTIME_BUFFER_SIZE, DMA_DEFAULT_ALIGNMENT)",
        ):
            self.assertIn(token, text if token.startswith("dma_alloc") else body)
        self.assertNotIn("block_device_write", text)
        self.assertNotIn("WriteBlocks", text)

    def test_runtime_probe_validates_signature_header_crc_and_geometry(self):
        text = GPT.read_text(encoding="utf-8")
        body = text.split("pub fn gpt_probe_backup_header()", 1)[1]
        body = body.split("pub fn gpt_runtime_is_ready", 1)[0]
        for token in (
            "('E' as u8)", "('F' as u8)", "('I' as u8)", "('P' as u8)",
            "('A' as u8)", "('R' as u8)", "('T' as u8)",
            "revision != GPT_REVISION_1_0",
            "header_size < GPT_HEADER_MIN_SIZE",
            "let expected_crc = gpt_read_u32(base, 16)",
            "*crc0 = 0", "*crc1 = 0", "*crc2 = 0", "*crc3 = 0",
            "let computed_crc = gpt_crc32(base, header_size as usize)",
            "computed_crc != expected_crc",
            "current_lba != last_lba", "backup_lba != 1",
            "entries_lba + entries_blocks != current_lba",
            "GPT_RUNTIME_READY = true",
        ):
            self.assertIn(token, body)

    def test_runtime_metadata_is_published_only_after_validation(self):
        text = GPT.read_text(encoding="utf-8")
        for token in (
            "pub fn gpt_runtime_is_ready() -> bool",
            "pub fn gpt_runtime_current_lba() -> u64",
            "pub fn gpt_runtime_backup_lba() -> u64",
            "pub fn gpt_runtime_first_usable_lba() -> u64",
            "pub fn gpt_runtime_last_usable_lba() -> u64",
            "pub fn gpt_runtime_entries_lba() -> u64",
            "pub fn gpt_runtime_entry_count() -> u32",
            "pub fn gpt_runtime_entry_size() -> u32",
        ):
            self.assertIn(token, text)

    def test_planner_and_runtime_probe_do_not_write_storage(self):
        text = GPT.read_text(encoding="utf-8")
        self.assertNotIn("WriteBlocks", text)
        self.assertNotIn("block_device_write", text)
        self.assertNotIn("__out", text)


if __name__ == "__main__":
    unittest.main()
