#!/usr/bin/env python3
"""Guardrails do gate real do backup GPT Partition Entry Array."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CRC = ROOT / "kernel/src/storage/crc32.sotlas"
GPT = ROOT / "kernel/src/storage/gpt.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class GptEntryArrayTests(unittest.TestCase):
    def test_crc32_layer_supports_streaming_without_changing_polynomial(self):
        text = CRC.read_text(encoding="utf-8")
        for token in (
            "pub fn crc32_ieee_begin() -> u32",
            "pub fn crc32_ieee_update(crc: u32, data: *const u8, length: usize) -> u32",
            "pub fn crc32_ieee_finish(crc: u32) -> u32",
            "CRC32_POLYNOMIAL: u32 = 0xEDB88320",
            "current = (current >> 1) ^ CRC32_POLYNOMIAL",
        ):
            self.assertIn(token, text)

    def test_header_publishes_partition_entry_array_crc(self):
        text = GPT.read_text(encoding="utf-8")
        body = text.split("pub fn gpt_probe_backup_header()", 1)[1]
        body = body.split("pub fn gpt_probe_backup_entries()", 1)[0]
        for token in (
            "let entries_crc32 = gpt_read_u32(base, 88)",
            "GPT_RUNTIME_ENTRIES_CRC32 = entries_crc32",
            "GPT_RUNTIME_ENTRIES_READY = false",
        ):
            self.assertIn(token, body)

    def test_entry_array_is_read_sector_by_sector_and_crc_checked(self):
        text = GPT.read_text(encoding="utf-8")
        body = text.split("pub fn gpt_probe_backup_entries()", 1)[1]
        body = body.split("pub fn gpt_runtime_is_ready", 1)[0]
        for token in (
            "while block < entries_blocks",
            "block_device_read_sector(lba, sector)",
            "crc32_ieee_begin()",
            "crc32_ieee_update(crc, sector as *const u8, bytes_this_sector as usize)",
            "let computed = crc32_ieee_finish(crc)",
            "if computed != expected { return false; }",
            "GPT_RUNTIME_ENTRIES_READY = true",
        ):
            self.assertIn(token, body)
        self.assertNotIn("block_device_write", body)
        self.assertNotIn("WriteBlocks", body)

    def test_post_cutover_requires_entry_crc_after_header_before_storage_done(self):
        text = POST.read_text(encoding="utf-8")
        helper = text.split("pub fn post_cutover_probe_backup_gpt_entries()", 1)[1]
        helper = helper.split("pub fn sotlas_x86_post_cutover_entry", 1)[0]
        self.assertIn("gpt_probe_backup_entries()", helper)
        self.assertIn("gpt_runtime_entries_are_ready()", helper)
        self.assertIn("gpt_runtime_entries_crc32_computed() != gpt_runtime_entries_crc32()", helper)

        entry = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        marker_i = entry.index("x86_serial_write_stage_marker('i' as u8)")
        entries = entry.index("post_cutover_probe_backup_gpt_entries()")
        marker_m = entry.index("x86_serial_write_stage_marker('m' as u8)")
        marker_j = entry.index("x86_serial_write_stage_marker('J' as u8)")
        self.assertLess(marker_i, entries)
        self.assertLess(entries, marker_m)
        self.assertLess(marker_m, marker_j)

    def test_ci_uses_nonempty_entry_array_and_requires_marker_m(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            'type_guid = bytes.fromhex(',
            '"BAKEN TEST".encode("utf-16le")',
            "entries_crc = zlib.crc32(entries) & 0xFFFFFFFF",
            "assert entries[:16] != bytes(16)",
            "assert zlib.crc32(entries) & 0xFFFFFFFF == expected_crc",
        ):
            self.assertIn(token, text)
        markers = text.split("for marker in ", 1)[1].split("; do", 1)[0]
        self.assertLess(markers.index("STEP=i"), markers.index("STEP=m"))
        self.assertLess(markers.index("STEP=m"), markers.index("STEP=J"))


if __name__ == "__main__":
    unittest.main()
