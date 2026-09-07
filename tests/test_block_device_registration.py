#!/usr/bin/env python3
"""Guardrails da publicação AHCI/NVMe na Block Device API."""

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
        for token in ("BLOCK_DEVICE_AHCI", "BLOCK_DEVICE_NVME", "block_size == 0", "last_lba == 0", "!io_ready", "BLOCK_NATIVE_IO_READY = true"):
            self.assertIn(token, body)

    def test_ahci_registration_precedes_fixture_and_nvme_fallback(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        scan = text.split("pub fn storage_discovery_scan()", 1)[1]
        post_cutover = scan.index("let post_cutover = active_page_tables_is_ready();")
        pre_cutover = scan.index("if !post_cutover {")
        ahci_filter = scan.index("if kind != STORAGE_CONTROLLER_AHCI { continue; }")
        capacity = scan.index("storage_prepare_ahci_capacity_after_identify()")
        register = scan.index("storage_register_ahci_block_device()")
        certify = scan.index("storage_certify_ahci_fixture()")
        nvme_filter = scan.index("if kind != STORAGE_CONTROLLER_NVME { continue; }")
        nvme_register = scan.index("storage_register_nvme_block_device()")
        self.assertLess(post_cutover, pre_cutover)
        self.assertLess(pre_cutover, ahci_filter)
        self.assertLess(ahci_filter, capacity)
        self.assertLess(capacity, register)
        self.assertLess(register, certify)
        self.assertLess(certify, nvme_filter)
        self.assertLess(nvme_filter, nvme_register)

    def test_registration_uses_identify_capacity_not_ci_probe_flags(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("fn storage_register_ahci_block_device()", 1)[1].split("fn storage_register_nvme_block_device", 1)[0]
        for token in (
            "STORAGE_AHCI_IDENTIFY_READY", "ahci_runtime_is_ready()", "ahci_capacity_is_ready()", "ahci_total_sectors()",
            "let last_lba = total_sectors - 1", "block_device_register_native(BLOCK_DEVICE_AHCI", "AHCI_READ_SECTOR_SIZE as u32",
            "true, true", "block_device_has_native_target()", "block_device_has_writable_native_target()",
            "block_device_kind() != BLOCK_DEVICE_AHCI", "block_device_index() != STORAGE_CANDIDATE.pci_index",
            "block_device_last_lba() != last_lba", "STORAGE_BLOCK_DEVICE_READY = true", "x86_serial_write_stage_marker('k' as u8)",
        ):
            self.assertIn(token, body)
        self.assertNotIn("ahci_write_is_ready()", body)
        self.assertNotIn("AHCI_WRITE_TEST_LBA", body)

    def test_nvme_registration_uses_native_driver_capacity_and_context(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("fn storage_register_nvme_block_device()", 1)[1].split("fn storage_block_io_zero", 1)[0]
        for token in (
            "STORAGE_CONTROLLER_NVME", "nvme_initialize_first()", "nvme_last_lba()", "nvme_context()",
            "block_device_register_native(BLOCK_DEVICE_NVME, STORAGE_CANDIDATE.pci_index, 512, last_lba, true, true)",
            "block_device_bind_driver_context(context)", "block_device_kind() != BLOCK_DEVICE_NVME",
            "block_device_index() != STORAGE_CANDIDATE.pci_index", "block_device_driver_context() != context",
            "STORAGE_BLOCK_DEVICE_READY = true",
        ):
            self.assertIn(token, body)

    def test_scan_resets_registry_before_each_discovery(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        scan = text.split("pub fn storage_discovery_scan()", 1)[1]
        self.assertLess(scan.index("block_device_reset_registry()"), scan.index("let count = pci_get_device_count()"))

    def test_ci_requires_registration_fixture_and_generic_io_markers(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        markers = text.split("for marker in ", 1)[1].split("; do", 1)[0]
        for marker in ("STEP=k", "STEP=e", "STEP=f", "STEP=v", "STEP=J"):
            self.assertIn(marker, markers)


if __name__ == "__main__":
    unittest.main()
