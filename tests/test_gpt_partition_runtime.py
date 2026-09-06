#!/usr/bin/env python3
"""Guardrails do parser GPT nativo que publica a primeira ESP real."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
REDUNDANCY = ROOT / "kernel/src/storage/gpt_redundancy.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class GptPartitionRuntimeTests(unittest.TestCase):
    def test_parser_recognizes_esp_guid_in_ondisk_little_endian_form(self):
        text = REDUNDANCY.read_text(encoding="utf-8")
        for token in (
            "GPT_ESP_TYPE_GUID0: u32 = 0xC12A7328",
            "GPT_ESP_TYPE_GUID1: u32 = 0x11D2F81F",
            "GPT_ESP_TYPE_GUID2: u32 = 0xA0004BBA",
            "GPT_ESP_TYPE_GUID3: u32 = 0x3BC93EC9",
            "type0 != GPT_ESP_TYPE_GUID0",
            "type3 != GPT_ESP_TYPE_GUID3",
        ):
            self.assertIn(token, text)

    def test_parser_runs_only_after_redundancy_and_reads_primary_pea(self):
        text = REDUNDANCY.read_text(encoding="utf-8")
        body = text.split("pub fn gpt_probe_first_esp_partition", 1)[1]
        body = body.split("pub fn gpt_redundancy_is_ready", 1)[0]
        for token in (
            "gpt_redundancy_is_ready()",
            "gpt_primary_entries_lba()",
            "while index < entry_count",
            "block_device_read_sector(sector_lba, sector)",
            "block_device_read_sector(sector_lba + 1",
            "GPT_PARTITION_MANDATORY_BYTES",
        ):
            self.assertIn(token, body)
        self.assertNotIn("block_device_write", body)
        self.assertNotIn("WriteBlocks", body)

    def test_parser_publishes_valid_partition_geometry_before_marker(self):
        text = REDUNDANCY.read_text(encoding="utf-8")
        body = text.split("pub fn gpt_probe_first_esp_partition", 1)[1]
        body = body.split("pub fn gpt_redundancy_is_ready", 1)[0]
        for token in (
            "let unique0 = gpt_redundancy_read_u32(entry, 16)",
            "let first_lba = gpt_redundancy_read_u64(entry, 32)",
            "let last_lba = gpt_redundancy_read_u64(entry, 40)",
            "let attributes = gpt_redundancy_read_u64(entry, 48)",
            "first_lba < first_usable_lba",
            "last_lba > last_usable_lba",
            "GPT_PARTITION_READY = true",
            "x86_serial_write_stage_marker('t' as u8)",
        ):
            self.assertIn(token, body)
        self.assertLess(
            body.index("GPT_PARTITION_READY = true"),
            body.index("x86_serial_write_stage_marker('t' as u8)"),
        )

    def test_partition_gate_is_chained_after_redundancy_marker(self):
        text = REDUNDANCY.read_text(encoding="utf-8")
        body = text.split("pub fn gpt_probe_primary_backup_redundancy", 1)[1]
        body = body.split("@system\npub fn gpt_probe_first_esp_partition", 1)[0]
        marker_n = body.index("x86_serial_write_stage_marker('n' as u8)")
        parser = body.index("gpt_probe_first_esp_partition(")
        ready = body.index("gpt_partition_is_ready()")
        self.assertLess(marker_n, parser)
        self.assertLess(parser, ready)

    def test_ci_fixture_and_marker_prove_real_esp_entry(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            'type_guid = bytes.fromhex("28732ac11ff8d211ba4b00a0c93ec93b")',
            'unique_guid = bytes.fromhex("78563412341278569abcdef012345678")',
            'esp_first = 2048',
            'esp_last = 100000',
            '"<16s16sQQQ72s", entries, 0',
            "type_guid, unique_guid, esp_first, esp_last, 0, name",
            "assert primary_entries[:16] == esp_type_guid",
            "assert esp_first == 2048",
            "assert esp_last == 100000",
        ):
            self.assertIn(token, text)
        markers = text.split("for marker in ", 1)[1].split("; do", 1)[0]
        self.assertLess(markers.index("STEP=n"), markers.index("STEP=t"))
        self.assertLess(markers.index("STEP=t"), markers.index("STEP=y"))
        self.assertLess(markers.index("STEP=y"), markers.index("STEP=m"))
        self.assertLess(markers.index("STEP=m"), markers.index("STEP=J"))


if __name__ == "__main__":
    unittest.main()
