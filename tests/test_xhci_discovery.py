#!/usr/bin/env python3
"""Guardrails do discovery PCI read-only de xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
XHCI = ROOT / "kernel/src/drivers/xhci_discovery.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciDiscoveryTests(unittest.TestCase):
    def test_xhci_identity_is_pci_class_0c_03_30(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("PCI_CLASS_SERIAL_BUS: u8 = 0x0C", text)
        self.assertIn("PCI_SUBCLASS_USB: u8 = 0x03", text)
        self.assertIn("PCI_PROGIF_XHCI: u8 = 0x30", text)
        self.assertIn("(*dev).class_code == PCI_CLASS_SERIAL_BUS", text)
        self.assertIn("(*dev).subclass == PCI_SUBCLASS_USB", text)
        self.assertIn("(*dev).prog_if == PCI_PROGIF_XHCI", text)

    def test_discovery_is_read_only_and_does_not_promote_driver(self):
        text = XHCI.read_text(encoding="utf-8")
        forbidden = (
            "pci_enable", "pci_write", "baken_pci_out", "__out",
            "mmio_read", "mmio_write", "volatile", "bus_master",
            "command_ring", "event_ring", "dma_alloc", "xhci_reset",
        )
        body = text.split("module kernel::drivers::xhci_discovery;", 1)[1]
        for token in forbidden:
            self.assertNotIn(token, body.lower(), token)
        self.assertIn("command_before_driver", text)
        self.assertIn("let bar0 = &(*dev).bars[0]", text)
        self.assertIn("mmio_usable", text)

    def test_bar0_must_be_memory_and_nonzero_to_be_usable(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("let mmio_usable = !bar0.is_io && bar0.base_address != 0", text)
        self.assertIn("bar_is_64bit", text)
        self.assertIn("bar_prefetchable", text)
        self.assertIn("xhci_discovery_usable_mmio_count", text)

    def test_multiple_controllers_are_inventory_only(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("XHCI_MAX_CANDIDATES: usize = 8", text)
        self.assertIn("XHCI_CANDIDATE_COUNT", text)
        self.assertIn("xhci_discovery_candidate(index: u32)", text)

    def test_main_scans_xhci_only_after_pci_inventory(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_discovery::*;", text)
        pci_pos = text.index("pci_scan_all();")
        xhci_pos = text.index("xhci_discovery_scan();")
        self.assertLess(pci_pos, xhci_pos)


if __name__ == "__main__":
    unittest.main()
