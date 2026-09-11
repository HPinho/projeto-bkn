#!/usr/bin/env python3
"""Guardrails HID-4c.3 do SET_CONFIGURATION USB por Slot ID."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "kernel/src/drivers/xhci_set_configuration.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class XhciSetConfigurationTests(unittest.TestCase):
    def test_state_is_partitioned_by_slot_and_epoch(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("XHCI_SET_CONFIGURATION_SLOT_CAPACITY: usize = XHCI_DEVICE_SLOT_CAPACITY", text)
        self.assertIn("static mut XHCI_SET_CONFIGURATION_STATES: [XhciSetConfigurationState;", text)
        self.assertIn("xhci_device_table_slot_epoch(slot_id)", text)
        self.assertIn("pub fn xhci_set_configuration_for_slot(slot_id: u8)", text)
        self.assertIn("pub fn xhci_set_configuration_is_ready_for(slot_id: u8)", text)
        self.assertIn("pub fn xhci_set_configuration_value_for(slot_id: u8)", text)
        self.assertNotIn("static mut XHCI_SET_CONFIGURATION_READY:", text)
        self.assertNotIn("static mut XHCI_SET_CONFIGURATION_VALUE:", text)

    def test_stage_requires_matching_slot_prerequisites(self):
        text = STAGE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_set_configuration_for_slot(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_set_first_configuration()", 1)[0]
        for token in (
            "xhci_device_table_slot_is_valid(slot_id)",
            "xhci_address_is_ready_for(slot_id)",
            "xhci_configuration_is_ready_for(slot_id)",
            "xhci_configure_endpoint_is_ready_for(slot_id)",
            "xhci_ep0_is_ready_for(slot_id)",
            "xhci_configuration_value_for(slot_id)",
        ):
            self.assertIn(token, body)

    def test_setup_is_standard_host_to_device_set_configuration(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("USB_REQUEST_TYPE_HOST_TO_DEVICE_STANDARD_DEVICE: u8 = 0x00", text)
        self.assertIn("USB_REQUEST_SET_CONFIGURATION: u8 = 9", text)
        self.assertIn("configuration_value as u16", text)
        self.assertIn("XHCI_SETUP_TRT_NO_DATA", text)
        self.assertIn("let cycle = xhci_ep0_producer_cycle_for(slot_id)", text)

    def test_no_data_transfer_uses_same_slot_ep0_and_status_in(self):
        text = STAGE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_set_configuration_for_slot(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_set_first_configuration()", 1)[0]
        self.assertIn("xhci_trb_status_stage(true, true, cycle)", body)
        self.assertIn("xhci_ep0_submit_control_td_for_slot(", body)
        self.assertIn("slot_id,\n        setup,", body)
        self.assertIn("false\n    );", body)
        self.assertNotIn("xhci_ep0_submit_control_td(\n", body)

    def test_stage_requires_real_transfer_event_from_same_slot(self):
        text = STAGE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_set_configuration_for_slot(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_set_first_configuration()", 1)[0]
        self.assertIn("xhci_transfer_wait_ep0_completion(slot_id, status_physical)", body)
        self.assertIn("xhci_transfer_last_residual_length_for(slot_id) != 0", body)
        self.assertNotIn("xhci_transfer_last_residual_length()", body)

    def test_report_descriptor_is_initialized_for_same_slot_before_ready(self):
        text = STAGE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_set_configuration_for_slot(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_set_first_configuration()", 1)[0]
        init = body.index("xhci_hid_descriptor_initialize_for_slot(slot_id)")
        ready_check = body.index("!xhci_hid_descriptor_is_ready_for(slot_id)", init)
        publish = body.rindex("XHCI_SET_CONFIGURATION_STATES[index].ready = true")
        self.assertLess(init, ready_check)
        self.assertLess(ready_check, publish)
        self.assertNotIn("xhci_hid_descriptor_initialize()", body)

    def test_stage_does_not_publish_interrupt_in_reports(self):
        text = STAGE.read_text(encoding="utf-8").lower()
        self.assertNotIn("xhci_hid_report_poll", text)
        self.assertNotIn("interrupt_in", text)
        self.assertNotIn("doorbell", text)

    def test_legacy_first_device_wrappers_delegate_to_active_slot(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("let slot_id = xhci_configure_endpoint_active_slot_id()", text)
        self.assertIn("return xhci_set_configuration_for_slot(slot_id)", text)
        self.assertIn(
            "return xhci_set_configuration_is_ready_for(xhci_set_configuration_active_slot_id())",
            text,
        )
        self.assertIn(
            "return xhci_set_configuration_value_for(xhci_set_configuration_active_slot_id())",
            text,
        )

    def test_post_cutover_single_keyboard_contract_is_unchanged(self):
        text = POST.read_text(encoding="utf-8")
        helper = text.split("pub fn post_cutover_set_first_usb_configuration()", 1)[1]
        helper = helper.split("pub fn sotlas_x86_post_cutover_entry", 1)[0]
        self.assertIn("xhci_configure_endpoint_is_ready()", helper)
        self.assertIn("xhci_configuration_is_ready()", helper)
        self.assertIn("xhci_set_first_configuration()", helper)
        self.assertIn("xhci_set_configuration_is_ready()", helper)
        self.assertIn("xhci_set_configuration_value() == configuration_value", helper)

        entry = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        configure = entry.index("post_cutover_configure_first_usb_hid_endpoint()")
        marker_l = entry.index("x86_serial_write_stage_marker('L' as u8)")
        set_configuration = entry.index("post_cutover_set_first_usb_configuration()")
        marker_o = entry.index("x86_serial_write_stage_marker('O' as u8)")
        self.assertLess(configure, marker_l)
        self.assertLess(marker_l, set_configuration)
        self.assertLess(set_configuration, marker_o)

    def test_main_registers_set_configuration(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_set_configuration::*;", text)


if __name__ == "__main__":
    unittest.main()
