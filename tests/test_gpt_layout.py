#!/usr/bin/env python3
"""Contratos da geometria GPT nativa e independente de setor fixo."""

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

    def test_planner_does_not_write_storage(self):
        text = GPT.read_text(encoding="utf-8")
        self.assertNotIn("WriteBlocks", text)
        self.assertNotIn("block_device_write", text)
        self.assertNotIn("__out", text)


if __name__ == "__main__":
    unittest.main()
