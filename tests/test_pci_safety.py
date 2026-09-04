#!/usr/bin/env python3
"""PCI discovery must remain read-only until a device driver claims hardware."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PCI = ROOT / "kernel/src/drivers/pci_bus.sotlas"


class PciSafetyTests(unittest.TestCase):
    def test_global_scan_does_not_enable_devices(self):
        text = PCI.read_text(encoding="utf-8")
        scan = text.split("pub fn pci_scan_all()", 1)[1].split("pub fn pci_get_device_count", 1)[0]
        self.assertNotIn("pci_enable_device(", scan)
        self.assertNotIn("pci_enable_command_bits(", scan)

    def test_bar_discovery_does_not_write_all_ones(self):
        text = PCI.read_text(encoding="utf-8")
        probe = text.split("pub fn pci_probe_bar", 1)[1].split("pub fn pci_scan_all", 1)[0]
        # Reading 0xFFFFFFFF is valid and means an absent/unimplemented BAR.
        # What discovery must never do is write all ones to a live BAR just to
        # size it while the device may still be active.
        self.assertIsNone(
            re.search(r"pci_write_config32\s*\([^;]*0xFFFFFFFF", probe, re.DOTALL)
        )
        self.assertNotIn("pci_write_config32", probe)
        self.assertIn("size = 0", probe)

    def test_legacy_enable_does_not_force_io_space(self):
        text = PCI.read_text(encoding="utf-8")
        fn = text.split("pub fn pci_enable_device", 1)[1].split("pub fn pci_enable_command_bits", 1)[0]
        self.assertIn("PCI_COMMAND_MEMORY_SPACE | PCI_COMMAND_BUS_MASTER", fn)
        self.assertNotIn("PCI_COMMAND_IO_SPACE | PCI_COMMAND_MEMORY_SPACE | PCI_COMMAND_BUS_MASTER", fn)

    def test_command_bits_are_masked(self):
        text = PCI.read_text(encoding="utf-8")
        self.assertRegex(text, r"let\s+requested:\s*u16\s*=\s*bits\s*&\s*allowed")


if __name__ == "__main__":
    unittest.main()
