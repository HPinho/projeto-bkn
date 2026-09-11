#!/usr/bin/env python3
"""Guardrails HID-4c.4e do produtor HID Interrupt IN por slot."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciHidReportTests(unittest.TestCase):
    def test_report_state_is_partitioned_by_slot_epoch_and_one_outstanding_td(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("XHCI_HID_REPORT_SLOT_CAPACITY: usize = XHCI_DEVICE_SLOT_CAPACITY", text)
        self.assertIn("static mut XHCI_HID_REPORT_STATES: [XhciHidReportState;", text)
        self.assertIn("pub transfer_pending: bool", text)
        self.assertIn("pub pending_trb_physical: u64", text)
        self.assertIn("pub pending_transfer_length: u32", text)
        self.assertIn("pub fn xhci_hid_report_submit_for_slot(slot_id: u8)", text)
        self.assertIn("pub fn xhci_hid_report_complete_for_slot(slot_id: u8)", text)
        self.assertIn("xhci_device_table_slot_epoch(slot_id)", text)
        self.assertNotIn("static mut XHCI_HID_REPORT_BUFFER:", text)

    def test_report_path_requires_same_slot_configuration_endpoint_map_events_and_identity(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_prepare_for_slot", 1)[1]
        body = body.split("pub fn xhci_hid_report_prepare()", 1)[0]
        for token in (
            "xhci_hid_context_is_ready_for(slot_id)",
            "xhci_configure_endpoint_is_ready_for(slot_id)",
            "xhci_set_configuration_is_ready_for(slot_id)",
            "xhci_set_configuration_value_for(slot_id) != xhci_configuration_value_for(slot_id)",
            "xhci_hid_descriptor_input_map_is_ready_for(slot_id)",
            "hid_input_events_is_ready()",
            "input_event_queue_is_ready()",
            "xhci_hid_report_identity_matches_slot(slot_id)",
        ):
            self.assertIn(token, body)
        self.assertNotIn("xhci_set_configuration_is_ready()", body)

    def test_transport_identity_must_match_slot_before_report(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_report_identity_matches_slot", 1)[1]
        body = body.split("fn xhci_hid_report_ring_slot", 1)[0]
        self.assertIn("xhci_hid_descriptor_input_device_id_for(slot_id)", body)
        self.assertIn("xhci_hid_descriptor_input_device_generation_for(slot_id)", body)
        self.assertIn("xhci_hid_descriptor_input_device_is_active_for(slot_id)", body)
        self.assertIn("record.transport_address == slot_id as u32", body)

    def test_submit_publishes_normal_trb_before_doorbell_and_records_pending_after_advance(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_submit_for_slot(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_hid_report_complete_for_slot", 1)[0]
        write = body.index("*slot = xhci_trb_normal")
        barrier = body.index("x86_read_cr3_raw()")
        doorbell = body.index("xhci_hid_report_ring_doorbell(slot_id, dci)")
        advance = body.index("xhci_hid_report_advance(slot_id)")
        pending = body.index("XHCI_HID_REPORT_STATES[state_index].transfer_pending = true")
        self.assertLess(write, barrier)
        self.assertLess(barrier, doorbell)
        self.assertLess(doorbell, advance)
        self.assertLess(advance, pending)
        self.assertIn("xhci_hid_report_transfer_pending_for(slot_id)", body)

    def test_complete_waits_for_exact_slot_dci_and_trb_then_parses(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_complete_for_slot(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_hid_report_poll_slot_once", 1)[0]
        self.assertIn("xhci_hid_context_dci_for(slot_id)", body)
        self.assertIn("xhci_transfer_wait_completion(slot_id, dci, physical)", body)
        self.assertIn("xhci_transfer_last_residual_length_for(slot_id)", body)
        self.assertIn("xhci_hid_report_parse_for_slot(slot_id, actual)", body)
        self.assertNotIn("xhci_transfer_last_residual_length()", body)
        wait = body.index("xhci_transfer_wait_completion(slot_id, dci, physical)")
        clear = body.index("transfer_pending = false")
        parse = body.index("xhci_hid_report_parse_for_slot(slot_id, actual)")
        self.assertLess(wait, clear)
        self.assertLess(clear, parse)

    def test_poll_wrapper_preserves_legacy_single_slot_semantics(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_poll_slot_once(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_hid_report_poll_once", 1)[0]
        self.assertIn("xhci_hid_report_submit_for_slot(slot_id)", body)
        self.assertIn("xhci_hid_report_complete_for_slot(slot_id)", body)
        self.assertIn("return xhci_hid_report_poll_slot_once(xhci_hid_report_active_slot_id())", text)

    def test_report_ring_uses_slot_specific_base_link_and_cycle(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("xhci_hid_context_ring_physical_for(slot_id)", text)
        self.assertIn("xhci_hid_report_publish_link(slot_id, cycle)", text)
        self.assertIn("!XHCI_HID_REPORT_STATES[state_index].producer_cycle", text)

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
        self.assertIn("let protocol = xhci_hid_protocol_for(slot_id)", body)
        self.assertNotIn("xhci_hid_protocol()", body)

    def test_runtime_has_no_legacy_global_descriptor_identity_calls(self):
        text = HID.read_text(encoding="utf-8")
        for legacy in (
            "xhci_hid_descriptor_input_device_id()",
            "xhci_hid_descriptor_input_device_generation()",
            "xhci_hid_descriptor_input_device_is_active()",
            "xhci_hid_descriptor_input_map_is_ready()",
        ):
            self.assertNotIn(legacy, text)

    def test_boot_keyboard_and_mouse_fallbacks_remain_per_slot(self):
        text = HID.read_text(encoding="utf-8")
        for token in (
            "USB_HID_PROTOCOL_KEYBOARD", "XHCI_HID_BOOT_KEYBOARD_LENGTH",
            "USB_HID_PROTOCOL_MOUSE", "XHCI_HID_BOOT_MOUSE_MIN_LENGTH",
            ".keyboard_modifiers", ".keyboard_key0", ".mouse_buttons",
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

    def test_main_registers_hid_transport(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_hid_report::*;", text)
        self.assertIn("import kernel::drivers::xhci_transfer::*;", text)


if __name__ == "__main__":
    unittest.main()
