#!/usr/bin/env python3
"""Guardrails do inventário read-only de portas xHCI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PORT = ROOT / "kernel/src/drivers/xhci_port.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def code_only(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class XhciPortTests(unittest.TestCase):
    def test_port_inventory_requires_live_xhci_start(self):
        text = PORT.read_text(encoding="utf-8")
        self.assertIn("xhci_start_is_ready()", text)
        self.assertIn("xhci_start_noop_completed()", text)
        self.assertIn("xhci_controller_max_ports()", text)

    def test_portsc_layout_and_connection_bits_are_explicit(self):
        text = PORT.read_text(encoding="utf-8")
        self.assertIn("XHCI_PORT_REGISTER_BASE: u64 = 0x400", text)
        self.assertIn("XHCI_PORT_REGISTER_STRIDE: u64 = 0x10", text)
        self.assertIn("XHCI_PORTSC_CCS", text)
        self.assertIn("XHCI_PORTSC_PED", text)
        self.assertIn("XHCI_PORTSC_PP", text)
        self.assertIn("XHCI_PORTSC_SPEED_SHIFT", text)

    def test_port_inventory_is_read_only(self):
        code = code_only(PORT).lower()
        for forbidden in (
            "x86_mmio_write32",
            "port_reset",
            "warm_reset",
            "xhci_portsc_pr",
            "xhci_portsc_wpr",
            "doorbell",
            "enable_slot",
        ):
            self.assertNotIn(forbidden, code, forbidden)
        self.assertIn("x86_mmio_read32", code)

    def test_port_inventory_tracks_first_connected_port(self):
        text = PORT.read_text(encoding="utf-8")
        self.assertIn("XHCI_CONNECTED_PORT_COUNT", text)
        self.assertIn("XHCI_FIRST_CONNECTED_PORT", text)
        self.assertIn("if connected", text)
        self.assertIn("xhci_first_connected_port()", text)
        self.assertIn("xhci_port_snapshot(port_id: u8)", text)

    def test_port_module_is_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_port::*;", text)


if __name__ == "__main__":
    unittest.main()
