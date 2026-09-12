#!/usr/bin/env python3
"""Guardrails dos GET_DESCRIPTOR(Device) via EP0, incluindo isolamento por Slot ID."""

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

    def test_descriptor_state_is_bounded_per_slot_and_epoch(self):
        text = DESC.read_text(encoding="utf-8")
        self.assertIn("XHCI_DESCRIPTOR_SLOT_CAPACITY: usize = XHCI_DEVICE_SLOT_CAPACITY", text)
        self.assertIn("pub struct XhciDeviceDescriptorState", text)
        self.assertIn("static mut XHCI_DEVICE_DESCRIPTOR_STATES:", text)
        self.assertIn("pub epoch: u32", text)
        self.assertIn("xhci_device_table_slot_epoch(slot_id)", text)
        self.assertIn("XHCI_DEVICE_DESCRIPTOR_STATES[index].epoch != epoch", text)
        self.assertNotIn("static mut XHCI_DEVICE_DESCRIPTOR_PROBE_READY:", text)
        self.assertNotIn("static mut XHCI_DEVICE_DESCRIPTOR_READY:", text)

    def test_slot_probe_requests_exactly_eight_bytes(self):
        text = DESC.read_text(encoding="utf-8")
        self.assertIn("USB_DEVICE_DESCRIPTOR_PROBE_LENGTH: u16 = 8", text)
        body = text.split("pub fn xhci_probe_device_descriptor_8_for_slot(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_probe_first_device_descriptor_8()", 1)[0]
        self.assertIn("USB_DEVICE_DESCRIPTOR_PROBE_LENGTH", body)
        self.assertIn("xhci_trb_setup_stage", body)
        self.assertIn("xhci_trb_data_stage", body)
        self.assertIn("xhci_trb_status_stage(false, true", body)
        self.assertIn("xhci_ep0_producer_cycle_for(slot_id)", body)
        self.assertIn("xhci_ep0_submit_control_td_for_slot(slot_id", body)
        self.assertIn("xhci_transfer_wait_ep0_completion(slot_id", body)
        self.assertIn("xhci_transfer_last_residual_length_for(slot_id) != 0", body)

    def test_probe_validates_header_and_captures_bmaxpacketsize0_for_same_slot(self):
        text = DESC.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_probe_device_descriptor_8_for_slot(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_probe_first_device_descriptor_8()", 1)[0]
        self.assertIn("descriptor_type != USB_DESCRIPTOR_TYPE_DEVICE", body)
        self.assertIn("let max_packet0 = xhci_descriptor_read8(base, 7)", body)
        self.assertIn("max_packet0 == 0", body)
        self.assertIn("XHCI_DEVICE_DESCRIPTOR_STATES[index].probe_max_packet0 = max_packet0", body)
        self.assertIn("xhci_descriptor_state_is_current(slot_id)", body)

    def test_legacy_probe_wrapper_delegates_to_addressed_first_slot(self):
        text = DESC.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_probe_first_device_descriptor_8()", 1)[1]
        body = body.split("pub fn xhci_device_descriptor_probe_is_ready_for", 1)[0]
        self.assertIn("let slot_id = xhci_address_slot_id()", body)
        self.assertIn("xhci_probe_device_descriptor_8_for_slot(slot_id)", body)

    def test_full_descriptor_uses_same_slot_ep0_and_transfer_result(self):
        text = DESC.read_text(encoding="utf-8")
        publish_helper = text.split("fn xhci_descriptor_publish_candidate_buffer", 1)[1]
        publish_helper = publish_helper.split("fn xhci_descriptor_read8", 1)[0]
        self.assertIn("XHCI_DEVICE_DESCRIPTOR_STATES[index].buffer = buffer", publish_helper)

        body = text.split("pub fn xhci_get_device_descriptor_for_slot(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_get_first_device_descriptor()", 1)[0]
        self.assertIn("xhci_ep0_producer_cycle_for(slot_id)", body)
        self.assertIn("xhci_ep0_submit_control_td_for_slot(slot_id", body)
        self.assertIn("xhci_transfer_wait_ep0_completion(slot_id", body)
        self.assertIn("xhci_transfer_last_residual_length_for(slot_id)", body)
        self.assertIn("xhci_descriptor_publish_candidate_buffer(slot_id, epoch, buffer)", body)

        publish = body.index("xhci_descriptor_publish_candidate_buffer(slot_id, epoch, buffer)")
        submit = body.index("xhci_ep0_submit_control_td_for_slot(slot_id", publish)
        ready = body.index("XHCI_DEVICE_DESCRIPTOR_STATES[index].ready = true", submit)
        self.assertLess(publish, submit)
        self.assertLess(submit, ready)

    def test_descriptor_exposes_per_slot_core_fields_and_legacy_wrappers(self):
        text = DESC.read_text(encoding="utf-8")
        for token in (
            "xhci_device_usb_version_for(slot_id: u8)",
            "xhci_device_vendor_id_for(slot_id: u8)",
            "xhci_device_product_id_for(slot_id: u8)",
            "xhci_device_class_for(slot_id: u8)",
            "xhci_device_subclass_for(slot_id: u8)",
            "xhci_device_protocol_for(slot_id: u8)",
            "xhci_device_max_packet0_for(slot_id: u8)",
            "pub fn xhci_device_usb_version()",
            "pub fn xhci_device_max_packet0()",
        ):
            self.assertIn(token, text)

    def test_full_descriptor_is_activated_only_after_ep0_reconciliation(self):
        text = POST.read_text(encoding="utf-8")
        self.assertIn("pub fn post_cutover_read_full_usb_device_descriptor()", text)
        full = text.split("pub fn post_cutover_read_full_usb_device_descriptor()", 1)[1]
        full = full.split("pub fn sotlas_x86_post_cutover_entry", 1)[0]
        self.assertIn("xhci_evaluate_context_last_ep0_max_packet() != target", full)
        self.assertIn("xhci_get_first_device_descriptor()", full)
        self.assertIn("xhci_device_descriptor_is_ready()", full)
        self.assertIn("xhci_device_usb_version() == 0", full)
        self.assertIn("xhci_device_max_packet0() != raw_max_packet0", full)

    def test_runtime_orders_probe_reconcile_then_full_descriptor(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        probe = body.index("post_cutover_probe_first_usb_descriptor()")
        reconcile = body.index("post_cutover_reconcile_first_usb_ep0()")
        full = body.index("post_cutover_read_full_usb_device_descriptor()")
        self.assertLess(probe, reconcile)
        self.assertLess(reconcile, full)
        self.assertIn("x86_serial_write_stage_marker('F' as u8)", body)

    def test_stage_does_not_cross_into_configuration_or_hid(self):
        text = DESC.read_text(encoding="utf-8").lower()
        code = "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))
        self.assertNotIn("configure_endpoint", code)
        self.assertNotIn("hid_descriptor", code)
        self.assertNotIn("interrupt_in", code)


if __name__ == "__main__":
    unittest.main()
