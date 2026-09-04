#!/usr/bin/env python3
"""Guardrails do discovery PCI read-only para AHCI/NVMe."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "kernel/src/drivers/storage_discovery.sotlas"
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

    def test_discovery_never_enables_device_or_writes_config(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertNotIn("pci_enable_device", text)
        self.assertNotIn("pci_enable_command_bits", text)
        self.assertNotIn("pci_write_config", text)
        self.assertNotIn("pci_write_command", text)
        self.assertNotIn("block_device_register_native", text)

    def test_bar_choice_matches_controller_abi(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("(*dev).bars[5].base_address", text)
        self.assertIn("(*dev).bars[0].base_address", text)

    def test_installer_requires_discovery_but_not_treats_it_as_driver(self):
        text = ENGINE.read_text(encoding="utf-8")
        self.assertIn("storage_discovery_scan()", text)
        self.assertIn("block_device_has_writable_native_target()", text)
        self.assertLess(
            text.index("storage_discovery_scan()"),
            text.index("block_device_has_writable_native_target()"),
        )


if __name__ == "__main__":
    unittest.main()
