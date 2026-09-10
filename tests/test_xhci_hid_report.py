#!/usr/bin/env python3
"""Guardrails do produtor HID Interrupt IN com identidade HID-4a."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciHidReportTests(unittest.TestCase):
    def test_report_path_requires_configured_endpoint_map_events_and_active_identity(self):
        text = HID.read_text(encoding="utf-8")
        for token in (
            "xhci_hid_context_is_ready()", "xhci_set_configuration_is_ready()",
            "hid_input_report_map_is_ready()", "hid_input_events_is_ready()",
            "input_event_queue_is_ready()", "xhci_hid_descriptor_input_device_is_active()",
            "xhci_hid_context_dci() <= 1",
        ):
            self.assertIn(token, text)

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

    def test_real_report_is_validated_then_attributed_before_boot_fallback(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_report_parse(length: u32) -> bool", 1)[1]
        body = body.split("pub fn xhci_hid_report_prepare", 1)[0]
        validate = body.index("hid_input_report_validate(base as *const u8, length as usize)")
        identity = body.index("let device_id = xhci_hid_descriptor_input_device_id()")
        translate = body.index("hid_input_events_process_report_for_device(")
        keyboard = body.index("protocol == USB_HID_PROTOCOL_KEYBOARD")
        self.assertLess(validate, identity)
        self.assertLess(identity, translate)
        self.assertLess(translate, keyboard)
        self.assertIn("device_id, device_generation, base as *const u8", body)
        self.assertIn("if hid_input_report_has_report_ids() { return true; }", body)

    def test_runtime_event_marker_still_requires_a_new_published_event(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_report_parse(length: u32) -> bool", 1)[1]
        body = body.split("pub fn xhci_hid_report_prepare", 1)[0]
        self.assertIn("let before_events = hid_input_events_events_published()", body)
        self.assertIn("let after_events = hid_input_events_events_published()", body)
        self.assertIn("after_events > before_events", body)
        self.assertIn("xhci_hid_report_emit_event_ready_marker()", body)
        self.assertIn("xhci_hid_report_emit_event_failure_marker()", body)

    def test_boot_keyboard_and_mouse_fallbacks_remain(self):
        text = HID.read_text(encoding="utf-8")
        for token in (
            "USB_HID_PROTOCOL_KEYBOARD", "XHCI_HID_BOOT_KEYBOARD_LENGTH",
            "USB_HID_PROTOCOL_MOUSE", "XHCI_HID_BOOT_MOUSE_MIN_LENGTH",
            "XHCI_HID_KEYBOARD_MODIFIERS", "XHCI_HID_MOUSE_BUTTONS",
        ):
            self.assertIn(token, text)

    def test_post_cutover_gate_still_requires_real_qemu_key_a_report(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_prove_first_usb_hid_keyboard_report()", 1)[1]
        body = body.split("@system\npub fn post_cutover_discover_first_storage_controller", 1)[0]
        self.assertIn("xhci_hid_report_prepare()", body)
        self.assertIn("xhci_hid_report_poll_once()", body)
        self.assertIn("xhci_hid_report_last_length() >= XHCI_HID_BOOT_KEYBOARD_LENGTH", body)
        self.assertIn("xhci_hid_keyboard_key0() == USB_HID_USAGE_KEYBOARD_A", body)
        self.assertIn("POST_CUTOVER_HID_REPORT_ATTEMPTS", body)

    def test_main_registers_hid4_identity_and_transport(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::input_device::*;", text)
        self.assertIn("import kernel::drivers::input_event::*;", text)
        self.assertIn("import kernel::drivers::hid_input_events::*;", text)
        self.assertIn("import kernel::drivers::xhci_hid_report::*;", text)


if __name__ == "__main__":
    unittest.main()
