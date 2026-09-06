#!/usr/bin/env python3
"""Guardrail do gate bare-metal de Protective MBR sobre a Block Device nativa."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "kernel" / "src" / "storage" / "foundation_probe.sotlas"
POST = ROOT / "kernel" / "src" / "arch" / "x86_64" / "post_cutover.sotlas"
FIXTURE = ROOT / "tools" / "scripts" / "extend_foundation_fixture.py"
WORKFLOW = ROOT / ".github" / "workflows" / "baken_ci.yml"


class FoundationProtectiveMbrGateTests(unittest.TestCase):
    def test_kernel_reads_and_validates_real_lba0_without_writing_it(self):
        text = PROBE.read_text(encoding="utf-8")
        body = text.split("pub fn foundation_protective_mbr()", 1)[1]
        body = body.split("pub fn foundation_fat_path_probe()", 1)[0]

        self.assertIn("block_device_read_sector(0, page.virtual_address)", body)
        self.assertNotIn("block_device_write_sector", body)
        self.assertIn("(base + 510) as *const u8", body)
        self.assertIn("(base + 511) as *const u8", body)
        self.assertIn("!= 0x55", body)
        self.assertIn("!= 0xAA", body)
        self.assertIn("(base + 446) as *const u8", body)
        self.assertIn("(base + 450) as *const u8", body)
        self.assertIn("!= 0xEE", body)
        self.assertIn("(base + 454) as *const u32", body)
        self.assertIn("!= 1", body)
        self.assertIn("block_device_last_lba()", body)
        self.assertIn("(base + 458) as *const u32", body)
        self.assertIn("let mut i: usize = 462", body)
        self.assertIn("while i < 510", body)
        self.assertIn("x86_serial_write_stage_marker('(' as u8);", body)

    def test_fixture_creates_one_spec_compliant_protective_partition(self):
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertIn("mbr = bytearray(512)", text)
        self.assertIn("mbr[446:462] = struct.pack('<B3sB3sII'", text)
        self.assertIn("0xEE", text)
        self.assertIn("1, path.stat().st_size // 512 - 1", text)
        self.assertIn("mbr[510:] = b'\\x55\\xaa'", text)
        self.assertIn("image.seek(0)", text)
        self.assertIn("image.write(mbr)", text)
        self.assertIn("if mbr[510:] != b'\\x55\\xaa' or mbr[450] != 0xEE", text)

    def test_mbr_gate_runs_after_real_irq_and_before_fat_path(self):
        text = POST.read_text(encoding="utf-8")
        irq = text.index("foundation_external_irq_probe()")
        mbr = text.index("foundation_protective_mbr()", irq)
        fat = text.index("foundation_fat_path_probe()", mbr)
        self.assertLess(irq, mbr)
        self.assertLess(mbr, fat)

    def test_qemu_harness_seeds_and_verifies_the_protective_mbr(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "python3 tools/scripts/extend_foundation_fixture.py build/storage-test.img",
            text,
        )
        self.assertIn(
            "python3 tools/scripts/extend_foundation_fixture.py build/storage-test.img --verify build/qemu-serial.log",
            text,
        )
        fixture = FIXTURE.read_text(encoding="utf-8")
        self.assertIn("'BAKEN:STEP=('", fixture)


if __name__ == "__main__":
    unittest.main()
