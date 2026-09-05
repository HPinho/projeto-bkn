#!/usr/bin/env python3
"""Guardrails do primeiro READ/WRITE genérico sobre a Block Device API nativa."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AHCI_IO = ROOT / "kernel/src/drivers/ahci_block_io.sotlas"
BLOCK = ROOT / "kernel/src/storage/block_device.sotlas"
DISCOVERY = ROOT / "kernel/src/drivers/storage_discovery.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class BlockDeviceIoTests(unittest.TestCase):
    def test_ahci_generic_io_accepts_arbitrary_lba_and_real_dma_commands(self):
        text = AHCI_IO.read_text(encoding="utf-8")
        body = text.split("fn ahci_block_io_issue", 1)[1]
        body = body.split("pub fn ahci_block_io_read_sector", 1)[0]
        for token in (
            "lba: u64", "write_to_disk", "header_flags |= 1 << 6",
            "AHCI_FIS_TYPE_REG_H2D", "AHCI_PX_TFD", "AHCI_PX_IS", "AHCI_PX_CI",
            "AHCI_PXIS_TFES", "AHCI_TFD_BSY", "AHCI_TFD_DRQ", "AHCI_TFD_ERR",
            "ahci_runtime_command_list_physical", "ahci_runtime_command_table_physical",
            "x86_mmio_write32(port_base + AHCI_PX_CI, 1)",
            "prdbc != (AHCI_READ_SECTOR_SIZE as u32)",
        ):
            self.assertIn(token, body)
        self.assertIn("lba > 0x0FFFFFFF", body)
        self.assertIn("((lba >> 24) & 0x0F) as u8", body)
        self.assertIn("((lba >> 40) & 0xFF) as u8", body)
        self.assertNotIn("AHCI_WRITE_TEST_LBA", body)

    def test_ahci_generic_read_and_write_copy_through_dedicated_dma_buffer(self):
        text = AHCI_IO.read_text(encoding="utf-8")
        self.assertIn("AHCI_BLOCK_IO_BUFFER", text)
        self.assertIn("dma_alloc(AHCI_RUNTIME_PAGE_SIZE, AHCI_RUNTIME_PAGE_SIZE)", text)
        self.assertIn("dma_share_with_device(&mut buffer)", text)

        read = text.split("pub fn ahci_block_io_read_sector", 1)[1]
        read = read.split("pub fn ahci_block_io_write_sector", 1)[0]
        self.assertIn("lba >= ahci_total_sectors()", read)
        self.assertIn("AHCI_ATA_READ_DMA_EXT", read)
        self.assertIn("ahci_block_io_copy(output", read)

        write = text.split("pub fn ahci_block_io_write_sector", 1)[1]
        self.assertIn("lba >= ahci_total_sectors()", write)
        self.assertIn("AHCI_ATA_WRITE_DMA_EXT", write)
        self.assertIn("ahci_block_io_copy(data, input", write)
        self.assertIn("ahci_block_io_issue(hba, lba, command, true)", write)

    def test_block_device_dispatch_checks_registry_context_capacity_and_writable_state(self):
        text = BLOCK.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::ahci_block_io::*;", text)
        self.assertIn("BLOCK_DRIVER_CONTEXT", text)
        self.assertIn("pub fn block_device_bind_driver_context", text)

        read = text.split("pub fn block_device_read_sector", 1)[1]
        read = read.split("pub fn block_device_write_sector", 1)[0]
        for token in (
            "!BLOCK_NATIVE_IO_READY", "BLOCK_DRIVER_CONTEXT == 0", "lba > BLOCK_LAST_LBA",
            "BLOCK_KIND == BLOCK_DEVICE_AHCI",
            "ahci_block_io_read_sector(BLOCK_DRIVER_CONTEXT, lba, output)",
        ):
            self.assertIn(token, read)

        write = text.split("pub fn block_device_write_sector", 1)[1]
        write = write.split("pub fn block_device_has_native_target", 1)[0]
        for token in (
            "!BLOCK_NATIVE_IO_READY", "!BLOCK_WRITABLE", "BLOCK_DRIVER_CONTEXT == 0",
            "lba > BLOCK_LAST_LBA", "BLOCK_KIND == BLOCK_DEVICE_AHCI",
            "ahci_block_io_write_sector(BLOCK_DRIVER_CONTEXT, lba, input)",
        ):
            self.assertIn(token, write)

    def test_discovery_binds_hba_then_proves_generic_write_and_readback(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        register = text.split("fn storage_register_ahci_block_device", 1)[1]
        register = register.split("fn storage_block_io_zero", 1)[0]
        self.assertIn("block_device_bind_driver_context(STORAGE_CANDIDATE.abar_or_mmio_base)", register)
        self.assertIn("block_device_driver_context() != STORAGE_CANDIDATE.abar_or_mmio_base", register)

        proof = text.split("fn storage_prove_generic_block_io", 1)[1]
        proof = proof.split("pub fn storage_discovery_scan", 1)[0]
        write = proof.index("block_device_write_sector(AHCI_WRITE_TEST_LBA")
        clear = proof.index("storage_block_io_zero(data)", write)
        read = proof.index("block_device_read_sector(AHCI_WRITE_TEST_LBA")
        verify = proof.index("storage_block_io_probe_matches")
        marker = proof.index("x86_serial_write_stage_marker('v' as u8)")
        self.assertLess(write, clear)
        self.assertLess(clear, read)
        self.assertLess(read, verify)
        self.assertLess(verify, marker)

    def test_scan_keeps_generic_gate_after_registry_and_before_return(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        scan = text.split("pub fn storage_discovery_scan()", 1)[1]
        register = scan.index("storage_register_ahci_block_device()")
        generic = scan.index("storage_prove_generic_block_io()")
        ret = scan.index("return kind;")
        self.assertLess(register, generic)
        self.assertLess(generic, ret)
        self.assertIn("block_device_reset_registry();", scan[generic:ret])

    def test_ci_requires_generic_block_io_gate(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        markers = text.split("for marker in ", 1)[1].split("; do", 1)[0]
        self.assertLess(markers.index("STEP=k"), markers.index("STEP=v"))
        self.assertLess(markers.index("STEP=v"), markers.index("STEP=J"))


if __name__ == "__main__":
    unittest.main()
