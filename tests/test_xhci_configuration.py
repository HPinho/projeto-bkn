#!/usr/bin/env python3
"""Guardrails do Configuration/HID descriptor parser xHCI por Slot ID."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / "kernel/src/drivers/xhci_configuration.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


def code_only(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))


class XhciConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.text = CONF.read_text(encoding="utf-8")

    def test_configuration_state_is_partitioned_by_slot_and_epoch(self):
        for token in (
            "XHCI_CONFIGURATION_STATES",
            "XHCI_CONFIGURATION_SLOT_CAPACITY: usize = XHCI_DEVICE_SLOT_CAPACITY",
            "xhci_device_table_slot_epoch(slot_id)",
            "xhci_configuration_state_is_current(slot_id)",
        ):
            self.assertIn(token, self.text)
        for legacy_singleton in (
            "static mut XHCI_CONFIGURATION_HEADER_READY:",
            "static mut XHCI_CONFIGURATION_FULL_READY:",
            "static mut XHCI_CONFIGURATION_READY:",
            "static mut XHCI_CONFIGURATION_BUFFER:",
            "static mut XHCI_HID_INTERFACE_NUMBER:",
        ):
            self.assertNotIn(legacy_singleton, self.text)

    def test_slot_state_requires_certified_transport_chain(self):
        body = self.text.split("fn xhci_configuration_prepare_state(slot_id: u8)", 1)[1]
        body = body.split("fn xhci_configuration_state_is_current", 1)[0]
        for token in (
            "xhci_device_table_slot_is_valid(slot_id)",
            "xhci_address_is_ready_for(slot_id)",
            "xhci_context_is_ready_for(slot_id)",
            "xhci_ep0_is_ready_for(slot_id)",
            "xhci_device_descriptor_is_ready_for(slot_id)",
        ):
            self.assertIn(token, body)

    def test_configuration_fetch_uses_same_slot_ep0_and_transfer_result(self):
        body = self.text.split("fn xhci_configuration_fetch_for_slot", 1)[1]
        body = body.split("pub fn xhci_probe_configuration_header_for_slot", 1)[0]
        self.assertIn("xhci_ep0_producer_cycle_for(slot_id)", body)
        self.assertIn("xhci_ep0_submit_control_td_for_slot(", body)
        self.assertIn("slot_id, setup, data, status, true", body)
        self.assertIn("xhci_transfer_wait_ep0_completion(slot_id, status_physical)", body)
        self.assertIn("xhci_transfer_last_residual_length_for(slot_id) == 0", body)
        self.assertNotIn("xhci_ep0_submit_control_td(setup", body)
        self.assertNotIn("xhci_transfer_last_residual_length()", body)

    def test_configuration_header_probe_is_separate_from_full_parse(self):
        body = self.text.split("pub fn xhci_probe_configuration_header_for_slot", 1)[1]
        body = body.split("pub fn xhci_probe_first_configuration_header", 1)[0]
        self.assertIn("USB_CONFIGURATION_HEADER_LENGTH", body)
        self.assertIn("xhci_configuration_fetch_for_slot(", body)
        self.assertIn("slot_id, &mut buffer, USB_CONFIGURATION_HEADER_LENGTH", body)
        self.assertIn("xhci_configuration_read16(base, 2)", body)
        self.assertIn("xhci_configuration_read8(base, 5)", body)
        self.assertIn("descriptor_type != USB_DESCRIPTOR_TYPE_CONFIGURATION", body)
        self.assertIn("total_length < USB_CONFIGURATION_HEADER_LENGTH", body)
        self.assertIn("(total_length as u64) > XHCI_CONFIGURATION_DMA_SIZE", body)
        self.assertIn("configuration_value == 0", body)
        self.assertNotIn("xhci_configuration_parse_for_slot", body)

    def test_full_configuration_reuses_header_of_same_slot(self):
        body = self.text.split("pub fn xhci_read_configuration_full_for_slot", 1)[1]
        body = body.split("pub fn xhci_read_first_configuration_full", 1)[0]
        self.assertIn("xhci_configuration_header_is_ready_for(slot_id)", body)
        self.assertIn("xhci_configuration_header_total_length_for(slot_id)", body)
        self.assertIn("xhci_configuration_header_value_for(slot_id)", body)
        self.assertIn("xhci_configuration_fetch_for_slot(slot_id, &mut buffer, total_length)", body)
        self.assertIn("xhci_configuration_read16(base, 2) != total_length", body)
        self.assertIn(".full_ready = true", body)
        self.assertNotIn("xhci_configuration_parse_for_slot", body)

    def test_hid_parser_consumes_full_configuration_of_same_slot(self):
        body = self.text.split("pub fn xhci_get_hid_configuration_for_slot", 1)[1]
        body = body.split("pub fn xhci_get_first_hid_configuration", 1)[0]
        self.assertIn("xhci_configuration_full_is_ready_for(slot_id)", body)
        self.assertIn("XHCI_CONFIGURATION_STATES[index].buffer.virtual_address", body)
        self.assertIn("xhci_configuration_parse_for_slot(slot_id, base, total_length)", body)
        self.assertNotIn("xhci_configuration_fetch_for_slot(slot_id, &mut buffer", body)

    def test_parser_walks_variable_length_boot_hid_descriptors(self):
        parser = self.text.split("fn xhci_configuration_parse_for_slot", 1)[1].split(
            "pub fn xhci_get_hid_configuration_for_slot", 1
        )[0]
        self.assertIn("let length = xhci_configuration_read8(base, offset)", parser)
        self.assertIn("offset += length", parser)
        self.assertIn("offset + length > (total_length as u64)", parser)
        self.assertIn("USB_CLASS_HID", parser)
        self.assertIn("USB_HID_SUBCLASS_BOOT", parser)
        self.assertIn("USB_HID_PROTOCOL_KEYBOARD", parser)
        self.assertIn("USB_HID_PROTOCOL_MOUSE", parser)
        self.assertIn("USB_ENDPOINT_DIRECTION_IN", parser)
        self.assertIn("USB_ENDPOINT_TRANSFER_INTERRUPT", parser)
        self.assertIn("hid_report_length == 0", parser)

    def test_parsed_hid_binding_is_written_only_to_matching_slot(self):
        parser = self.text.split("fn xhci_configuration_parse_for_slot", 1)[1].split(
            "pub fn xhci_get_hid_configuration_for_slot", 1
        )[0]
        for field in (
            "hid_interface_number",
            "hid_protocol",
            "hid_report_descriptor_length",
            "hid_endpoint_address",
            "hid_endpoint_max_packet",
            "hid_endpoint_interval",
        ):
            self.assertIn(f"XHCI_CONFIGURATION_STATES[index].{field}", parser)

    def test_per_slot_accessors_exist_for_next_hid_stages(self):
        for signature in (
            "pub fn xhci_configuration_header_is_ready_for(slot_id: u8)",
            "pub fn xhci_configuration_header_total_length_for(slot_id: u8)",
            "pub fn xhci_configuration_header_value_for(slot_id: u8)",
            "pub fn xhci_configuration_full_is_ready_for(slot_id: u8)",
            "pub fn xhci_configuration_full_total_length_for(slot_id: u8)",
            "pub fn xhci_configuration_full_value_for(slot_id: u8)",
            "pub fn xhci_configuration_is_ready_for(slot_id: u8)",
            "pub fn xhci_configuration_value_for(slot_id: u8)",
            "pub fn xhci_hid_interface_number_for(slot_id: u8)",
            "pub fn xhci_hid_protocol_for(slot_id: u8)",
            "pub fn xhci_hid_endpoint_address_for(slot_id: u8)",
            "pub fn xhci_hid_endpoint_max_packet_for(slot_id: u8)",
            "pub fn xhci_hid_endpoint_interval_for(slot_id: u8)",
            "pub fn xhci_hid_report_descriptor_length_for(slot_id: u8)",
        ):
            self.assertIn(signature, self.text)

    def test_legacy_first_device_wrappers_are_preserved(self):
        for signature in (
            "pub fn xhci_probe_first_configuration_header()",
            "pub fn xhci_read_first_configuration_full()",
            "pub fn xhci_get_first_hid_configuration()",
            "pub fn xhci_configuration_header_is_ready()",
            "pub fn xhci_configuration_full_is_ready()",
            "pub fn xhci_configuration_is_ready()",
            "pub fn xhci_configuration_value()",
            "pub fn xhci_hid_interface_number()",
            "pub fn xhci_hid_protocol()",
            "pub fn xhci_hid_endpoint_address()",
            "pub fn xhci_hid_endpoint_max_packet()",
            "pub fn xhci_hid_endpoint_interval()",
            "pub fn xhci_hid_report_descriptor_length()",
        ):
            self.assertIn(signature, self.text)
        self.assertGreaterEqual(self.text.count("xhci_address_slot_id()"), 13)

    def test_configuration_stage_does_not_configure_hardware_yet(self):
        text = code_only(self.text).lower()
        self.assertNotIn("configure_endpoint", text)
        self.assertNotIn("set_configuration", text)
        self.assertNotIn("xhci_command_submit", text)
        self.assertNotIn("x86_mmio_write32", text)

    def test_post_cutover_keeps_certified_first_device_order(self):
        text = POST.read_text(encoding="utf-8")
        helper = text.split("pub fn post_cutover_parse_first_usb_hid_interface()", 1)[1]
        helper = helper.split("pub fn post_cutover_configure_first_usb_hid_endpoint()", 1)[0]
        self.assertIn("xhci_configuration_full_is_ready()", helper)
        self.assertIn("xhci_get_first_hid_configuration()", helper)
        self.assertIn("xhci_configuration_is_ready()", helper)
        self.assertIn("xhci_hid_report_descriptor_length() == 0", helper)

        entry = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        full = entry.index("post_cutover_read_full_usb_configuration_descriptor()")
        parsed = entry.index("post_cutover_parse_first_usb_hid_interface()")
        marker_h = entry.index("x86_serial_write_stage_marker('H' as u8)")
        marker_m = entry.index("x86_serial_write_stage_marker('M' as u8)")
        self.assertLess(full, marker_h)
        self.assertLess(marker_h, parsed)
        self.assertLess(parsed, marker_m)

    def test_main_registers_configuration_module(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_configuration::*;", text)


if __name__ == "__main__":
    unittest.main()
