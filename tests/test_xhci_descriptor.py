#!/usr/bin/env python3
"""Guardrails dos GET_DESCRIPTOR(Device) via EP0."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DESC = ROOT / "kernel/src/drivers/xhci_descriptor.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class XhciDescriptorTests(unittest.TestCase):
    def test_device_descriptor_request_keeps_full_18_byte_path(self):
        text = DESC.read_text(encoding="utf-8")
        self.assertIn("USB_REQUEST_TYPE_DEVICE_TO_HOST_STANDARD_DEVICE: u8 = 0x80", text)
        self.assertIn("USB_REQUEST_GET_DESCRIPTOR: u8 = 6", text)
        self.assertIn("USB_DESCRIPTOR_TYPE_DEVICE: u8 = 1", text)
        self.assertIn("USB_DEVICE_DESCRIPTOR_LENGTH: u16 = 18", text)
        self.assertIn("USB_DEVICE_DESCRIPTOR_VALUE: u16 = 0x0100", text)
        self.assertIn("XHCI_SETUP_TRT_IN_DATA", text)

    def test_first_probe_requests_exactly_eight_bytes(self):
        text = DESC.read_text(encoding="utf-8")
        self.assertIn("USB_DEVICE_DESCRIPTOR_PROBE_LENGTH: u16 = 8", text)
        body = text.split("pub fn xhci_probe_first_device_descriptor_8()", 1)[1]
        body = body.split("pub fn xhci_device_descriptor_probe_is_ready()", 1)[0]
        self.assertIn("USB_DEVICE_DESCRIPTOR_PROBE_LENGTH", body)
        self.assertIn("xhci_trb_setup_stage", body)
        self.assertIn("xhci_trb_data_stage", body)
        self.assertIn("xhci_trb_status_stage(false, true", body)
        self.assertIn("xhci_transfer_wait_ep0_completion", body)
        self.assertIn("xhci_transfer_last_residual_length() != 0", body)

    def test_probe_validates_header_and_captures_bmaxpacketsize0(self):
        text = DESC.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_probe_first_device_descriptor_8()", 1)[1]
        body = body.split("pub fn xhci_device_descriptor_probe_is_ready()", 1)[0]
        self.assertIn("descriptor_type != USB_DESCRIPTOR_TYPE_DEVICE", body)
        self.assertIn("let max_packet0 = xhci_descriptor_read8(base, 7)", body)
        self.assertIn("max_packet0 == 0", body)
        self.assertIn("XHCI_DEVICE_DESCRIPTOR_PROBE_MAX_PACKET0 = max_packet0", body)

    def test_td_uses_setup_data_status_and_shared_transfer_waiter(self):
        text = DESC.read_text(encoding="utf-8")
        self.assertIn("xhci_trb_setup_stage", text)
        self.assertIn("xhci_trb_data_stage", text)
        self.assertIn("xhci_trb_status_stage(false, true", text)
        self.assertIn("xhci_ep0_submit_control_td", text)
        self.assertIn("xhci_transfer_wait_ep0_completion", text)

    def test_descriptor_validates_identity_and_exposes_core_fields(self):
        text = DESC.read_text(encoding="utf-8")
        self.assertIn("descriptor_type != USB_DESCRIPTOR_TYPE_DEVICE", text)
        for token in (
            "XHCI_DEVICE_USB_VERSION",
            "XHCI_DEVICE_VENDOR_ID",
            "XHCI_DEVICE_PRODUCT_ID",
            "XHCI_DEVICE_CLASS",
            "XHCI_DEVICE_SUBCLASS",
            "XHCI_DEVICE_PROTOCOL",
            "XHCI_DEVICE_MAX_PACKET0",
        ):
            self.assertIn(token, text)

    def test_full_descriptor_is_not_activated_before_probe_gate(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        self.assertNotIn("xhci_get_first_device_descriptor()", body)

    def test_stage_does_not_cross_into_configuration_or_hid(self):
        text = DESC.read_text(encoding="utf-8").lower()
        code = "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))
        self.assertNotIn("configure_endpoint", code)
        self.assertNotIn("hid_descriptor", code)
        self.assertNotIn("interrupt_in", code)


if __name__ == "__main__":
    unittest.main()
