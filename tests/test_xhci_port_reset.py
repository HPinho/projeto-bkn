#!/usr/bin/env python3
"""Guardrails do reset de porta xHCI consciente de USB2/USB3."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RESET = ROOT / "kernel/src/drivers/xhci_port_reset.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class XhciPortResetTests(unittest.TestCase):
    def test_reset_requires_live_xhci_and_protocol_inventory(self):
        text = RESET.read_text(encoding="utf-8")
        self.assertIn("xhci_start_is_ready()", text)
        self.assertIn("xhci_start_noop_completed()", text)
        self.assertIn("xhci_protocol_scan()", text)
        self.assertIn("xhci_port_scan()", text)
        self.assertIn("xhci_protocol_major_for_port", text)

    def test_usb2_uses_pr_and_usb3_uses_wpr_only_when_needed(self):
        text = RESET.read_text(encoding="utf-8")
        self.assertIn("XHCI_PORTSC_PR", text)
        self.assertIn("XHCI_PORTSC_WPR", text)
        self.assertIn("xhci_port_reset_usb2", text)
        self.assertIn("xhci_port_reset_usb3", text)
        self.assertIn("if (before & XHCI_PORTSC_PED) != 0 { return true; }", text)

    def test_portsc_write_image_clears_ped_change_bits_and_reset_bits(self):
        text = RESET.read_text(encoding="utf-8")
        safe = text.split("fn xhci_port_reset_safe_base", 1)[1].split("fn xhci_port_reset_ack_change", 1)[0]
        self.assertIn("XHCI_PORTSC_PED", safe)
        self.assertIn("XHCI_PORTSC_PR", safe)
        self.assertIn("XHCI_PORTSC_LWS", safe)
        self.assertIn("XHCI_PORTSC_CHANGE_MASK", safe)
        self.assertIn("XHCI_PORTSC_WPR", safe)

    def test_usb2_requires_prc_and_enabled_port_after_reset(self):
        text = RESET.read_text(encoding="utf-8")
        body = text.split("fn xhci_port_reset_usb2", 1)[1].split("fn xhci_port_reset_usb3", 1)[0]
        self.assertIn("XHCI_PORTSC_PRC", body)
        self.assertIn("XHCI_PORTSC_PED", body)
        self.assertIn("xhci_port_reset_ack_change(address, XHCI_PORTSC_PRC)", body)

    def test_usb3_warm_reset_requires_wrc_and_enabled_port(self):
        text = RESET.read_text(encoding="utf-8")
        body = text.split("fn xhci_port_reset_usb3", 1)[1].split("pub fn xhci_port_reset_first_connected", 1)[0]
        self.assertIn("XHCI_PORTSC_WRC", body)
        self.assertIn("XHCI_PORTSC_PED", body)
        self.assertIn("xhci_port_reset_ack_change(address, XHCI_PORTSC_WRC)", body)

    def test_reset_is_compiled_but_not_called_from_post_cutover_yet(self):
        main = MAIN.read_text(encoding="utf-8")
        post = POST.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_port_reset::*;", main)
        self.assertNotIn("xhci_port_reset_first_connected()", post)


if __name__ == "__main__":
    unittest.main()
