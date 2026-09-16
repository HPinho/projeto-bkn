#!/usr/bin/env python3
"""DF-5c: capability walkers PCI/PCIe devem ser bounded, cycle-safe e read-only."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPS = ROOT / "kernel/src/drivers/pci_capabilities.sotlas"


class PciCapabilityWalkerTests(unittest.TestCase):
    def setUp(self):
        self.text = CAPS.read_text(encoding="utf-8")

    def test_module_uses_config_core_and_is_read_only(self):
        self.assertIn("module kernel::drivers::pci_capabilities;", self.text)
        self.assertIn("import kernel::drivers::pci_config::*;", self.text)
        self.assertIn("pci_config_read16", self.text)
        self.assertIn("pci_config_read32", self.text)
        self.assertNotIn("pci_config_write", self.text)
        self.assertNotIn("x86_mmio_write", self.text)
        self.assertNotIn("baken_pci_out32", self.text)

    def test_conventional_walker_honors_status_and_header_type_pointer(self):
        self.assertIn("PCI_STATUS_CAPABILITIES_LIST: u16 = 0x0010", self.text)
        self.assertIn("PCI_CAPABILITY_POINTER_TYPE0_1: u16 = 0x0034", self.text)
        self.assertIn("PCI_CAPABILITY_POINTER_CARDBUS: u16 = 0x0014", self.text)
        self.assertIn("pci_config_read8(segment, bus, slot, func, 0x000E) & 0x7F", self.text)
        self.assertIn("(status & PCI_STATUS_CAPABILITIES_LIST) == 0", self.text)

    def test_conventional_walker_is_bounded_and_cycle_safe(self):
        self.assertIn("PCI_CAPABILITY_MIN_OFFSET: u16 = 0x0040", self.text)
        self.assertIn("PCI_CAPABILITY_MAX_OFFSET: u16 = 0x00FC", self.text)
        self.assertIn("PCI_CAPABILITY_MAX_STEPS: u16 = 48", self.text)
        self.assertIn("let mut visited: u64 = 0", self.text)
        self.assertIn("(visited & bit) != 0", self.text)
        self.assertIn("while current != 0 && steps < PCI_CAPABILITY_MAX_STEPS", self.text)

    def test_extended_walker_decodes_pcie_header_and_requires_ecam(self):
        self.assertIn("PCI_EXT_CAPABILITY_FIRST_OFFSET: u16 = 0x0100", self.text)
        self.assertIn("PCI_EXT_CAPABILITY_MAX_OFFSET: u16 = 0x0FFC", self.text)
        self.assertIn("pci_config_supports_extended_space()", self.text)
        self.assertIn("(header & 0x0000FFFF) as u16", self.text)
        self.assertIn("((header >> 16) & 0x0000000F) as u8", self.text)
        self.assertIn("((header >> 20) & 0x00000FFF) as u16", self.text)

    def test_extended_walker_uses_floyd_cycle_detection_and_hard_bound(self):
        self.assertIn("PCI_EXT_CAPABILITY_MAX_STEPS: u16 = 960", self.text)
        self.assertIn("let mut slow: u16 = PCI_EXT_CAPABILITY_FIRST_OFFSET", self.text)
        self.assertIn("let mut fast: u16 = PCI_EXT_CAPABILITY_FIRST_OFFSET", self.text)
        self.assertGreaterEqual(
            self.text.count("fast = pci_extended_capability_next"), 2
        )
        self.assertIn("if slow == fast { return false; }", self.text)
        self.assertIn("while steps < PCI_EXT_CAPABILITY_MAX_STEPS", self.text)

    def test_msi_msix_and_pcie_ids_are_canonical(self):
        self.assertIn("PCI_CAP_ID_MSI: u8 = 0x05", self.text)
        self.assertIn("PCI_CAP_ID_PCIE: u8 = 0x10", self.text)
        self.assertIn("PCI_CAP_ID_MSIX: u8 = 0x11", self.text)

    def test_public_find_api_returns_offset_without_programming_device(self):
        self.assertIn("pub struct PciCapability", self.text)
        self.assertIn("pub fn pci_capability_find", self.text)
        self.assertIn("pub fn pci_extended_capability_find", self.text)
        for field in (
            "pub id: u16", "pub version: u8", "pub offset: u16",
            "pub next_offset: u16", "pub extended: bool", "pub valid: bool",
        ):
            self.assertIn(field, self.text)


if __name__ == "__main__":
    unittest.main()
