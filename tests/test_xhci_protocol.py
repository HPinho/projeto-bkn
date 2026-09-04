#!/usr/bin/env python3
"""Guardrails da descoberta read-only de Supported Protocol xHCI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "kernel/src/drivers/xhci_protocol.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def code_only(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class XhciProtocolTests(unittest.TestCase):
    def test_supported_protocol_capability_is_explicit(self):
        text = PROTO.read_text(encoding="utf-8")
        self.assertIn("XHCI_EXT_CAP_SUPPORTED_PROTOCOL: u32 = 2", text)
        self.assertIn("XHCI_HCCPARAMS1", text)
        self.assertIn("(hccparams1 >> 16) & 0xFFFF", text)
        self.assertIn("let next = (header >> 8) & 0xFF", text)

    def test_protocol_ranges_expose_usb_major_port_range_and_slot_type(self):
        text = PROTO.read_text(encoding="utf-8")
        self.assertIn("pub struct XhciProtocolRange", text)
        self.assertIn("pub major: u8", text)
        self.assertIn("pub port_offset: u8", text)
        self.assertIn("pub port_count: u8", text)
        self.assertIn("pub slot_type: u8", text)
        self.assertIn("xhci_protocol_major_for_port", text)
        self.assertIn("xhci_protocol_slot_type_for_port", text)

    def test_protocol_discovery_is_read_only(self):
        code = code_only(PROTO).lower()
        self.assertIn("x86_mmio_read32", code)
        self.assertNotIn("x86_mmio_write32", code)
        self.assertNotIn("port_reset", code)
        self.assertNotIn("enable_slot", code)

    def test_ranges_must_fit_controller_port_count(self):
        text = PROTO.read_text(encoding="utf-8")
        self.assertIn("xhci_controller_max_ports()", text)
        self.assertIn("if last > (xhci_controller_max_ports() as u16)", text)

    def test_protocol_module_is_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_protocol::*;", text)


if __name__ == "__main__":
    unittest.main()
