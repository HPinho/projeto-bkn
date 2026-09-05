#!/usr/bin/env python3
"""Guardrails do discovery PCI e primeiro probe MMIO AHCI/NVMe."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "kernel/src/drivers/storage_discovery.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
ENGINE = ROOT / "kernel/src/install_engine.sotlas"


class StorageDiscoveryTests(unittest.TestCase):
    def test_ahci_and_nvme_class_tuples_are_explicit(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        for token in (
            "PCI_CLASS_MASS_STORAGE: u8 = 0x01",
            "PCI_SUBCLASS_SATA: u8 = 0x06",
            "PCI_PROGIF_AHCI: u8 = 0x01",
            "PCI_SUBCLASS_NVM: u8 = 0x08",
            "PCI_PROGIF_NVME: u8 = 0x02",
        ):
            self.assertIn(token, text)

    def test_bar_choice_matches_controller_abi(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("(*dev).bars[5].base_address", text)
        self.assertIn("(*dev).bars[0].base_address", text)

    def test_mmio_probe_only_enables_memory_space_and_preserves_bus_master(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("fn storage_probe_mmio_after_cutover()", 1)[1]
        body = body.split("pub fn storage_discovery_scan()", 1)[0]
        self.assertIn("active_page_tables_is_ready()", body)
        self.assertIn("PCI_COMMAND_MEMORY_SPACE", body)
        self.assertIn("pci_enable_command_bits", body)
        self.assertIn("PCI_COMMAND_BUS_MASTER", body)
        self.assertIn("command_before", body)
        self.assertIn("command_after", body)
        self.assertNotIn("PCI_COMMAND_MEMORY_SPACE | PCI_COMMAND_BUS_MASTER", body)
        self.assertNotIn("pci_enable_device", body)
        self.assertNotIn("block_device_register_native", body)

    def test_mmio_probe_maps_uc_identity_and_reads_structural_registers(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("active_page_tables_map_mmio_identity_4k", text)
        for token in (
            "AHCI_REG_CAP",
            "AHCI_REG_GHC",
            "AHCI_REG_PI",
            "AHCI_REG_VS",
            "NVME_REG_CAP_LO",
            "NVME_REG_CAP_HI",
            "NVME_REG_VS",
            "NVME_REG_CSTS",
            "x86_mmio_read32",
            "STORAGE_MMIO_READY = true",
            "x86_serial_write_stage_marker('a' as u8)",
        ):
            self.assertIn(token, text)

    def test_no_reset_dma_or_block_registration_in_mmio_stage(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        for forbidden in (
            "block_device_register_native",
            "dma_alloc",
            "pmm_alloc",
            "MSI",
            "MSIX",
            "AHCI_GHC_HR",
            "NVME_CC_EN",
        ):
            self.assertNotIn(forbidden, text)

    def test_installer_requires_discovery_but_not_treats_it_as_driver(self):
        text = ENGINE.read_text(encoding="utf-8")
        self.assertIn("storage_discovery_scan()", text)
        self.assertIn("block_device_has_writable_native_target()", text)
        self.assertLess(
            text.index("storage_discovery_scan()"),
            text.index("block_device_has_writable_native_target()"),
        )

    def test_post_cutover_storage_gate_is_after_real_hid_report(self):
        text = POST.read_text(encoding="utf-8")
        entry = text.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        marker_w = entry.index("x86_serial_write_stage_marker('W' as u8)")
        storage = entry.index("post_cutover_discover_first_storage_controller()")
        marker_j = entry.index("x86_serial_write_stage_marker('J' as u8)")
        self.assertLess(marker_w, storage)
        self.assertLess(storage, marker_j)

    def test_post_cutover_helper_does_not_directly_program_storage(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_discover_first_storage_controller()", 1)[1]
        body = body.split("@system\n@export", 1)[0]
        self.assertIn("storage_discovery_scan()", body)
        self.assertIn("storage_discovery_candidate()", body)
        self.assertIn("STORAGE_CONTROLLER_AHCI", body)
        self.assertIn("STORAGE_CONTROLLER_NVME", body)
        self.assertIn("abar_or_mmio_base", body)
        for forbidden in (
            "pci_enable_device",
            "pci_enable_command_bits",
            "pci_write_config",
            "pci_write_command",
            "block_device_register_native",
        ):
            self.assertNotIn(forbidden, body)


if __name__ == "__main__":
    unittest.main()
