#!/usr/bin/env python3
"""Guardrails da publicação do caminho AHCI provado na Block Device API."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "kernel/src/drivers/storage_discovery.sotlas"
BLOCK = ROOT / "kernel/src/storage/block_device.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class BlockDeviceRegistrationTests(unittest.TestCase):
    def test_registry_requires_real_native_io_contract(self):
        text = BLOCK.read_text(encoding="utf-8")
        body = text.split("pub fn block_device_register_native", 1)[1]
        body = body.split("pub fn block_device_has_native_target", 1)[0]
        for token in (
            "BLOCK_DEVICE_AHCI", "BLOCK_DEVICE_NVME", "block_size == 0",
            "last_lba == 0", "!io_ready", "BLOCK_NATIVE_IO_READY = true",
        ):
            self.assertIn(token, body)

    def test_ahci_registration_occurs_only_after_read_and_write_proofs(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        scan = text.split("pub fn storage_discovery_scan()", 1)[1]
        post_cutover = scan.index("let post_cutover = active_page_tables_is_ready();")
        boot_filter = scan.index("if post_cutover && kind != STORAGE_CONTROLLER_AHCI { continue; }")
        pre_cutover_return = scan.index("if !post_cutover { return kind; }")
        read = scan.index("storage_read_ahci_after_identify()")
        write = scan.index("ahci_write_probe_sector1")
        register = scan.index("storage_register_ahci_block_device()")
        self.assertLess(post_cutover, boot_filter)
        self.assertLess(boot_filter, pre_cutover_return)
        self.assertLess(pre_cutover_return, read)
        self.assertLess(read, write)
        self.assertLess(write, register)

    def test_registration_publishes_identify_capacity_and_writable_state(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("fn storage_register_ahci_block_device()", 1)[1]
        body = body.split("pub fn storage_discovery_scan()", 1)[0]
        for token in (
            "!STORAGE_AHCI_READ_READY", "!ahci_write_is_ready()",
            "ahci_total_sectors()", "let last_lba = total_sectors - 1",
            "block_device_register_native(BLOCK_DEVICE_AHCI",
            "AHCI_READ_SECTOR_SIZE as u32", "true, true",
            "block_device_has_native_target()",
            "block_device_has_writable_native_target()",
            "block_device_kind() != BLOCK_DEVICE_AHCI",
            "block_device_index() != STORAGE_CANDIDATE.pci_index",
            "block_device_last_lba() != last_lba",
            "STORAGE_BLOCK_DEVICE_READY = true",
            "x86_serial_write_stage_marker('k' as u8)",
        ):
            self.assertIn(token, body)

    def test_scan_resets_registry_before_each_discovery(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        scan = text.split("pub fn storage_discovery_scan()", 1)[1]
        self.assertLess(scan.index("block_device_reset_registry()"),
                        scan.index("let count = pci_get_device_count()"))

    def test_ci_requires_block_device_gate_after_write(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        markers = text.split("for marker in ", 1)[1].split("; do", 1)[0]
        self.assertLess(markers.index("STEP=e"), markers.index("STEP=f"))
        self.assertLess(markers.index("STEP=f"), markers.index("STEP=k"))
        self.assertLess(markers.index("STEP=k"), markers.index("STEP=v"))
        self.assertLess(markers.index("STEP=v"), markers.index("STEP=J"))


if __name__ == "__main__":
    unittest.main()
