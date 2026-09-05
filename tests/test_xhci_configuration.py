#!/usr/bin/env python3
"""Guardrails do Configuration/HID descriptor parser xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / "kernel/src/drivers/xhci_configuration.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


def code_only(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))


class XhciConfigurationTests(unittest.TestCase):
    def test_configuration_header_probe_is_separate_from_full_parse(self):
        text = CONF.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_probe_first_configuration_header()", 1)[1]
        body = body.split("pub fn xhci_configuration_header_is_ready()", 1)[0]
        self.assertIn("USB_CONFIGURATION_HEADER_LENGTH", body)
        self.assertIn("xhci_configuration_fetch(&mut buffer, USB_CONFIGURATION_HEADER_LENGTH)", body)
        self.assertIn("xhci_configuration_read16(base, 2)", body)
        self.assertIn("xhci_configuration_read8(base, 5)", body)
        self.assertNotIn("xhci_configuration_parse", body)
        self.assertNotIn("xhci_get_first_hid_configuration", body)

    def test_configuration_header_validates_identity_and_bounds(self):
        text = CONF.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_probe_first_configuration_header()", 1)[1]
        body = body.split("pub fn xhci_configuration_header_is_ready()", 1)[0]
        self.assertIn("descriptor_type != USB_DESCRIPTOR_TYPE_CONFIGURATION", body)
        self.assertIn("total_length < USB_CONFIGURATION_HEADER_LENGTH", body)
        self.assertIn("(total_length as u64) > XHCI_CONFIGURATION_DMA_SIZE", body)
        self.assertIn("configuration_value == 0", body)
        self.assertIn("XHCI_CONFIGURATION_HEADER_READY = true", body)

    def test_full_configuration_uses_header_total_length_without_parsing(self):
        text = CONF.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_read_first_configuration_full()", 1)[1]
        body = body.split("pub fn xhci_configuration_full_is_ready()", 1)[0]
        self.assertIn("xhci_configuration_header_is_ready()", body)
        self.assertIn("xhci_configuration_header_total_length()", body)
        self.assertIn("xhci_configuration_fetch(&mut buffer, total_length)", body)
        self.assertIn("xhci_configuration_read16(base, 2) != total_length", body)
        self.assertIn("XHCI_CONFIGURATION_FULL_READY = true", body)
        self.assertNotIn("xhci_configuration_parse", body)
        self.assertNotIn("xhci_get_first_hid_configuration", body)

    def test_hid_parser_consumes_already_fetched_full_configuration(self):
        text = CONF.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_get_first_hid_configuration()", 1)[1]
        self.assertIn("xhci_configuration_full_is_ready()", body)
        self.assertIn("XHCI_CONFIGURATION_BUFFER.virtual_address", body)
        self.assertIn("xhci_configuration_parse(base, total_length)", body)
        self.assertNotIn("xhci_configuration_fetch(&mut buffer", body)

    def test_parser_walks_variable_length_descriptors(self):
        text = CONF.read_text(encoding="utf-8")
        parser = text.split("fn xhci_configuration_parse", 1)[1].split(
            "pub fn xhci_get_first_hid_configuration", 1
        )[0]
        self.assertIn("let length = xhci_configuration_read8(base, offset)", parser)
        self.assertIn("offset += length", parser)
        self.assertIn("offset + length > (total_length as u64)", parser)

    def test_parser_requires_boot_hid_interrupt_in(self):
        text = CONF.read_text(encoding="utf-8")
        self.assertIn("USB_CLASS_HID", text)
        self.assertIn("USB_HID_SUBCLASS_BOOT", text)
        self.assertIn("USB_HID_PROTOCOL_KEYBOARD", text)
        self.assertIn("USB_HID_PROTOCOL_MOUSE", text)
        self.assertIn("USB_ENDPOINT_DIRECTION_IN", text)
        self.assertIn("USB_ENDPOINT_TRANSFER_INTERRUPT", text)
        self.assertIn("attributes & USB_ENDPOINT_TRANSFER_TYPE_MASK", text)

    def test_parser_tracks_hid_report_and_interrupt_endpoint(self):
        text = CONF.read_text(encoding="utf-8")
        self.assertIn("USB_DESCRIPTOR_TYPE_HID", text)
        self.assertIn("USB_DESCRIPTOR_TYPE_REPORT", text)
        self.assertIn("XHCI_HID_REPORT_DESCRIPTOR_LENGTH", text)
        self.assertIn("XHCI_HID_ENDPOINT_ADDRESS", text)
        self.assertIn("XHCI_HID_ENDPOINT_MAX_PACKET", text)
        self.assertIn("XHCI_HID_ENDPOINT_INTERVAL", text)

    def test_configuration_stage_does_not_configure_hardware_yet(self):
        text = code_only(CONF.read_text(encoding="utf-8")).lower()
        self.assertNotIn("configure_endpoint", text)
        self.assertNotIn("set_configuration", text)
        self.assertNotIn("xhci_command_submit", text)
        self.assertNotIn("x86_mmio_write32", text)

    def test_post_cutover_activates_hid_parser_only_after_full_descriptor(self):
        text = POST.read_text(encoding="utf-8")
        helper = text.split("pub fn post_cutover_parse_first_usb_hid_interface()", 1)[1]
        helper = helper.split("pub fn post_cutover_configure_first_usb_hid_endpoint()", 1)[0]
        self.assertIn("xhci_configuration_full_is_ready()", helper)
        self.assertIn("xhci_get_first_hid_configuration()", helper)
        self.assertIn("xhci_configuration_is_ready()", helper)
        self.assertIn("USB_HID_PROTOCOL_KEYBOARD", helper)
        self.assertIn("USB_HID_PROTOCOL_MOUSE", helper)
        self.assertIn("USB_ENDPOINT_DIRECTION_IN", helper)
        self.assertIn("xhci_hid_endpoint_max_packet() == 0", helper)
        self.assertIn("xhci_hid_endpoint_interval() == 0", helper)
        self.assertIn("xhci_hid_report_descriptor_length() == 0", helper)

        entry = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        full = entry.index("post_cutover_read_full_usb_configuration_descriptor()")
        parsed = entry.index("post_cutover_parse_first_usb_hid_interface()")
        marker_h = entry.index("x86_serial_write_stage_marker('H' as u8)")
        marker_m = entry.index("x86_serial_write_stage_marker('M' as u8)")
        self.assertLess(full, marker_h)
        self.assertLess(marker_h, parsed)
        self.assertLess(parsed, marker_m)

    def test_parser_gate_still_does_not_configure_endpoint_or_device(self):
        text = code_only(POST.read_text(encoding="utf-8")).lower()
        helper = text.split("pub fn post_cutover_parse_first_usb_hid_interface()", 1)[1]
        helper = helper.split("pub fn post_cutover_configure_first_usb_hid_endpoint()", 1)[0]
        self.assertNotIn("configure_endpoint", helper)
        self.assertNotIn("set_configuration", helper)
        self.assertNotIn("xhci_command_submit", helper)

    def test_main_registers_configuration_module(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_configuration::*;", text)


if __name__ == "__main__":
    unittest.main()
