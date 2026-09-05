#!/usr/bin/env python3
"""Guardrails do primeiro WRITE DMA real e readback AHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AHCI = ROOT / "kernel/src/drivers/ahci_block_read.sotlas"
DISCOVERY = ROOT / "kernel/src/drivers/storage_discovery.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class AhciBlockWriteTests(unittest.TestCase):
    def test_write_commands_and_header_direction_are_explicit(self):
        text = AHCI.read_text(encoding="utf-8")
        self.assertIn("AHCI_ATA_WRITE_DMA_EXT: u8 = 0x35", text)
        self.assertIn("AHCI_ATA_WRITE_DMA: u8 = 0xCA", text)
        body = text.split("fn ahci_write_issue_dma", 1)[1]
        body = body.split("pub fn ahci_write_probe_sector1", 1)[0]
        for token in (
            "write_to_disk", "header_flags |= 1 << 6",
            "AHCI_WRITE_TEST_LBA", "AHCI_FIS_TYPE_REG_H2D",
            "AHCI_PX_TFD", "AHCI_PX_IS", "AHCI_PX_CI", "AHCI_PXIS_TFES",
            "x86_mmio_write32(port_base + AHCI_PX_CI, 1)",
            "prdbc != (AHCI_READ_SECTOR_SIZE as u32)",
        ):
            self.assertIn(token, body)

    def test_write_gate_uses_dedicated_shared_dma_buffer(self):
        text = AHCI.read_text(encoding="utf-8")
        prep = text.split("fn ahci_write_prepare_buffer", 1)[1]
        prep = prep.split("fn ahci_write_fill_magic", 1)[0]
        for token in (
            "AHCI_WRITE_BUFFER", "dma_alloc(", "dma_buffer_cpu_owned",
            "dma_share_with_device",
        ):
            self.assertIn(token, prep)
        probe = text.split("pub fn ahci_write_probe_sector1", 1)[1]
        probe = probe.split("fn ahci_read_magic_matches", 1)[0]
        self.assertIn("AHCI_WRITE_BUFFER.virtual_address", probe)
        self.assertNotIn("AHCI_READ_BUFFER.virtual_address", probe)

    def test_write_is_followed_by_buffer_clear_and_real_readback(self):
        text = AHCI.read_text(encoding="utf-8")
        body = text.split("pub fn ahci_write_probe_sector1", 1)[1]
        body = body.split("fn ahci_read_magic_matches", 1)[0]
        write = body.index("ahci_write_issue_dma(hba, write_command, true)")
        clear = body.index("ahci_block_zero(data, AHCI_READ_SECTOR_SIZE)")
        readback = body.index("ahci_write_issue_dma(hba, read_command, false)")
        verify = body.index("ahci_write_magic_matches")
        marker = body.index("x86_serial_write_stage_marker('f' as u8)")
        self.assertLess(write, clear)
        self.assertLess(clear, readback)
        self.assertLess(readback, verify)
        self.assertLess(verify, marker)

    def test_discovery_runs_write_only_after_proven_read(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("pub fn storage_discovery_scan()", 1)[1]
        early = body.index("if !active_page_tables_is_ready() { return kind; }")
        read = body.index("storage_read_ahci_after_identify()")
        write = body.index("ahci_write_probe_sector1")
        self.assertLess(early, read)
        self.assertLess(read, write)
        self.assertIn("ahci_write_is_ready()", body)

    def test_ci_uses_disposable_sector_and_verifies_persisted_write(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        baseline = "printf 'BAKENOLD' | dd of=build/storage-test.img bs=1 seek=512"
        verify = 'skip=512 count=8 status=none)" = "BAKENW01"'
        self.assertIn(baseline, text)
        self.assertIn(verify, text)
        self.assertIn("STEP=e STEP=f STEP=J", text)


if __name__ == "__main__":
    unittest.main()
