#!/usr/bin/env python3
"""Guardrails HID-4c.3 do produtor HID Interrupt IN por slot."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciHidReportTests(unittest.TestCase):
    def test_report_state_is_partitioned_by_slot_and_epoch(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("XHCI_HID_REPORT_SLOT_CAPACITY: usize = XHCI_DEVICE_SLOT_CAPACITY", text)
        self.assertIn("static mut XHCI_HID_REPORT_STATES: [XhciHidReportState;", text)
        self.assertIn("pub fn xhci_hid_report_prepare_for_slot(slot_id: u8)", text)
        self.assertIn("pub fn xhci_hid_report_poll_slot_once(slot_id: u8)", text)
        self.assertIn("xhci_device_table_slot_epoch(slot_id)", text)
        self.assertNotIn("static mut XHCI_HID_REPORT_BUFFER:", text)
        self.assertNotIn("static mut XHCI_HID_REPORT_ENQUEUE_INDEX:", text)
        self.assertNotIn("static mut XHCI_HID_REPORT_PRODUCER_CYCLE:", text)

    def test_report_path_requires_configured_endpoint_device_map_events_and_identity(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_prepare_for_slot", 1)[1]
        for token in (
            "xhci_hid_context_is_ready_for(slot_id)",
            "xhci_configure_endpoint_is_ready_for(slot_id)",
            "xhci_set_configuration_is_ready()",
            "xhci_hid_descriptor_input_map_is_ready_for(slot_id)",
            "hid_input_events_is_ready()",
            "input_event_queue_is_ready()",
            "xhci_hid_report_identity_matches_slot(slot_id)",
        ):
            self.assertIn(token, body)
        self.assertNotIn("hid_input_report_map_is_ready()", text)

    def test_transport_identity_must_match_slot_before_report(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_report_identity_matches_slot", 1)[1]
        body = body.split("fn xhci_hid_report_ring_slot", 1)[0]
        self.assertIn("xhci_hid_descriptor_input_device_id_for(slot_id)", body)
        self.assertIn("xhci_hid_descriptor_input_device_generation_for(slot_id)", body)
        self.assertIn("xhci_hid_descriptor_input_device_is_active_for(slot_id)", body)
        self.assertIn("input_device_snapshot(device_id, generation)", body)
        self.assertIn("record.transport_kind == INPUT_TRANSPORT_USB", body)
        self.assertIn("record.transport_address == slot_id as u32", body)

    def test_normal_trb_publication_precedes_doorbell_wait(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_poll_slot_once(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_hid_report_poll_once", 1)[0]
        write = body.index("*slot = xhci_trb_normal")
        barrier = body.index("x86_read_cr3_raw()")
        doorbell = body.index("xhci_hid_report_ring_doorbell(slot_id, dci)")
        advance = body.index("xhci_hid_report_advance(slot_id)")
        wait = body.index("xhci_transfer_wait_completion(slot_id, dci, physical)")
        self.assertLess(write, barrier)
        self.assertLess(barrier, doorbell)
        self.assertLess(doorbell, advance)
        self.assertLess(advance, wait)

    def test_report_ring_uses_slot_specific_base_link_and_cycle(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("xhci_hid_context_ring_physical_for(slot_id)", text)
        self.assertIn("xhci_hid_report_publish_link(slot_id, cycle)", text)
        self.assertIn("XHCI_HID_REPORT_STATES[state_index].producer_cycle =", text)
        self.assertIn("!XHCI_HID_REPORT_STATES[state_index].producer_cycle", text)

    def test_transfer_event_uses_slot_specific_hid_dci_and_result(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_poll_slot_once", 1)[1]
        self.assertIn("xhci_hid_context_dci_for(slot_id)", body)
        self.assertIn("xhci_transfer_wait_completion(slot_id, dci, physical)", body)
        self.assertIn("xhci_transfer_last_residual_length_for(slot_id)", body)
        self.assertNotIn("xhci_transfer_last_residual_length()", body)

    def test_real_report_is_attributed_then_validated_against_its_device_map(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_report_parse_for_slot", 1)[1]
        body = body.split("pub fn xhci_hid_report_is_ready_for", 1)[0]
        identity = body.index("xhci_hid_report_identity_matches_slot(slot_id)")
        validate = body.index("hid_input_device_map_validate(")
        translate = body.index("hid_input_events_process_report_for_device(")
        keyboard = body.index("protocol == USB_HID_PROTOCOL_KEYBOARD")
        self.assertLess(identity, validate)
        self.assertLess(validate, translate)
        self.assertLess(translate, keyboard)
        self.assertIn("xhci_hid_descriptor_input_device_id_for(slot_id)", body)
        self.assertIn("xhci_hid_descriptor_input_device_generation_for(slot_id)", body)
        self.assertIn("device_id, device_generation, base as *const u8", body)
        self.assertIn("hid_input_device_map_has_report_ids(device_id, device_generation)", body)
        self.assertIn("let protocol = xhci_hid_protocol_for(slot_id)", body)
        self.assertNotIn("xhci_hid_protocol()", body)
        self.assertNotIn("hid_input_report_validate(", body)

    def test_runtime_has_no_legacy_global_descriptor_identity_calls(self):
        text = HID.read_text(encoding="utf-8")
        for legacy in (
            "xhci_hid_descriptor_input_device_id()",
            "xhci_hid_descriptor_input_device_generation()",
            "xhci_hid_descriptor_input_device_is_active()",
            "xhci_hid_descriptor_input_map_is_ready()",
        ):
            self.assertNotIn(legacy, text)

    def test_runtime_event_marker_is_per_slot_and_requires_new_event(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_report_parse_for_slot", 1)[1]
        body = body.split("pub fn xhci_hid_report_is_ready_for", 1)[0]
        self.assertIn("let before_events = hid_input_events_events_published()", body)
        self.assertIn("let after_events = hid_input_events_events_published()", body)
        self.assertIn("XHCI_HID_REPORT_STATES[state_index].event_marker_emitted", body)
        self.assertIn("after_events > before_events", body)
        self.assertIn("xhci_hid_report_emit_event_ready_marker()", body)

    def test_boot_keyboard_and_mouse_fallbacks_remain_per_slot(self):
        text = HID.read_text(encoding="utf-8")
        for token in (
            "USB_HID_PROTOCOL_KEYBOARD", "XHCI_HID_BOOT_KEYBOARD_LENGTH",
            "USB_HID_PROTOCOL_MOUSE", "XHCI_HID_BOOT_MOUSE_MIN_LENGTH",
            ".keyboard_modifiers", ".keyboard_key0", ".mouse_buttons",
        ):
            self.assertIn(token, text)

    def test_legacy_wrappers_delegate_to_active_slot(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("return xhci_hid_report_poll_slot_once(xhci_hid_report_active_slot_id())", text)
        self.assertIn("return xhci_hid_report_last_length_for(xhci_hid_report_active_slot_id())", text)
        self.assertIn("return xhci_hid_keyboard_key0_for(xhci_hid_report_active_slot_id())", text)

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
