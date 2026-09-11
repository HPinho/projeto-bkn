#!/usr/bin/env python3
"""Guardrails do reset de porta xHCI consciente de USB2/USB3 e HID-4c.4."""

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

    def test_explicit_port_api_exists_and_is_bounded(self):
        text = RESET.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_port_reset_for(port_id: u8)", 1)[1]
        body = body.split("pub fn xhci_port_reset_first_connected", 1)[0]
        self.assertIn("if port_id == 0", body)
        self.assertIn("let port_count = xhci_port_scan()", body)
        self.assertIn("(port_id as u16) > port_count", body)
        self.assertIn("xhci_protocol_major_for_port(port_id)", body)
        self.assertIn("xhci_port_reset_address(port_id)", body)
        self.assertIn("(before & XHCI_PORTSC_CCS) == 0", body)

    def test_first_port_wrapper_delegates_to_explicit_port_reset(self):
        text = RESET.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_port_reset_first_connected()", 1)[1]
        body = body.split("pub fn xhci_port_reset_is_ready", 1)[0]
        self.assertIn("let port_id = xhci_first_connected_port()", body)
        self.assertIn("return xhci_port_reset_for(port_id);", body)

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
        body = text.split("fn xhci_port_reset_usb3", 1)[1].split("pub fn xhci_port_reset_for", 1)[0]
        self.assertIn("XHCI_PORTSC_WRC", body)
        self.assertIn("XHCI_PORTSC_PED", body)
        self.assertIn("xhci_port_reset_ack_change(address, XHCI_PORTSC_WRC)", body)

    def test_last_reset_state_is_diagnostic_not_multi_device_identity(self):
        text = RESET.read_text(encoding="utf-8")
        self.assertIn("última operação de reset concluída", text)
        self.assertNotIn("XHCI_PORT_RESET_STATES", text)

    def test_reset_is_compiled_but_not_called_directly_from_post_cutover(self):
        main = MAIN.read_text(encoding="utf-8")
        post = POST.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_port_reset::*;", main)
        self.assertNotIn("xhci_port_reset_first_connected()", post)
        self.assertNotIn("xhci_port_reset_for(", post)


if __name__ == "__main__":
    unittest.main()
