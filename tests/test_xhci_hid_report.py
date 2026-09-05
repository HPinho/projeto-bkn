#!/usr/bin/env python3
"""Guardrails do produtor e parser de HID Boot Interrupt IN."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciHidReportTests(unittest.TestCase):
    def test_report_path_requires_configured_hid_endpoint(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("xhci_hid_context_is_ready()", text)
        self.assertIn("xhci_set_configuration_is_ready()", text)
        self.assertIn("xhci_hid_context_dci() <= 1", text)

    def test_normal_trb_publication_precedes_doorbell_wait(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_poll_once()", 1)[1]
        write = body.index("*slot = xhci_trb_normal")
        barrier = body.index("x86_read_cr3_raw()")
        doorbell = body.index("xhci_hid_report_ring_doorbell")
        advance = body.index("xhci_hid_report_advance()")
        wait = body.index("xhci_transfer_wait_completion")
        self.assertLess(write, barrier)
        self.assertLess(barrier, doorbell)
        self.assertLess(doorbell, advance)
        self.assertLess(advance, wait)

    def test_report_ring_uses_link_trb_and_toggles_cycle(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("XHCI_HID_RING_TRBS - XHCI_RING_RESERVED_LINK_TRBS", text)
        self.assertIn("xhci_hid_report_publish_link(cycle)", text)
        self.assertIn("XHCI_HID_REPORT_PRODUCER_CYCLE = !XHCI_HID_REPORT_PRODUCER_CYCLE", text)

    def test_transfer_event_uses_hid_dci(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("xhci_transfer_wait_completion(slot_id, dci, physical)", text)
        self.assertIn("xhci_transfer_last_residual_length()", text)

    def test_boot_keyboard_and_mouse_parsers_exist(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("USB_HID_PROTOCOL_KEYBOARD", text)
        self.assertIn("XHCI_HID_BOOT_KEYBOARD_LENGTH", text)
        self.assertIn("USB_HID_PROTOCOL_MOUSE", text)
        self.assertIn("XHCI_HID_BOOT_MOUSE_MIN_LENGTH", text)
        self.assertIn("XHCI_HID_KEYBOARD_MODIFIERS", text)
        self.assertIn("XHCI_HID_MOUSE_BUTTONS", text)

    def test_post_cutover_gate_runs_only_after_set_configuration(self):
        text = POST.read_text(encoding="utf-8")
        set_config = text.index("post_cutover_set_first_usb_configuration()")
        report = text.index("post_cutover_prove_first_usb_hid_keyboard_report()")
        marker_o = text.index("x86_serial_write_stage_marker('O' as u8)")
        marker_w = text.index("x86_serial_write_stage_marker('W' as u8)")
        self.assertLess(set_config, marker_o)
        self.assertLess(marker_o, report)
        self.assertLess(report, marker_w)

    def test_post_cutover_gate_requires_real_qemu_key_a_report(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_prove_first_usb_hid_keyboard_report()", 1)[1]
        body = body.split("@system\n@export", 1)[0]
        self.assertIn("xhci_hid_report_prepare()", body)
        self.assertIn("xhci_hid_report_poll_once()", body)
        self.assertIn("xhci_hid_report_last_length() >= XHCI_HID_BOOT_KEYBOARD_LENGTH", body)
        self.assertIn("xhci_hid_keyboard_key0() == USB_HID_USAGE_KEYBOARD_A", body)
        self.assertIn("POST_CUTOVER_HID_REPORT_ATTEMPTS", body)

    def test_main_registers_hid_report_path(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_hid_report::*;", text)


if __name__ == "__main__":
    unittest.main()
