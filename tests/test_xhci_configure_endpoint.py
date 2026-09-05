#!/usr/bin/env python3
"""Guardrails do Configure Endpoint xHCI para HID."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "kernel/src/drivers/xhci_configure_endpoint.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class XhciConfigureEndpointTests(unittest.TestCase):
    def test_stage_requires_hid_context_and_command_ring(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("xhci_hid_context_is_ready()", text)
        self.assertIn("xhci_context_is_ready()", text)
        self.assertIn("xhci_command_is_ready()", text)

    def test_stage_submits_configure_endpoint_without_deconfigure(self):
        text = STAGE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_configure_first_hid_endpoint()", 1)[1]
        self.assertIn("xhci_trb_configure_endpoint", body)
        self.assertIn("xhci_command_submit", body)
        self.assertIn("xhci_command_wait_completion", body)
        self.assertIn("xhci_command_last_slot_id() != slot_id", body)
        self.assertIn("false,", body)

    def test_output_context_must_report_endpoint_running(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("(dci as u64) * (context_size as u64)", text)
        self.assertIn("XHCI_ENDPOINT_STATE_MASK", text)
        self.assertIn("XHCI_ENDPOINT_STATE_RUNNING", text)
        self.assertIn("endpoint_state != XHCI_ENDPOINT_STATE_RUNNING", text)

    def test_stage_does_not_set_usb_configuration_or_ring_endpoint(self):
        text = STAGE.read_text(encoding="utf-8").lower()
        self.assertNotIn("set_configuration", text)
        self.assertNotIn("doorbell", text)
        self.assertNotIn("xhci_transfer_wait", text)

    def test_post_cutover_activates_context_then_configure_endpoint_after_parser(self):
        text = POST.read_text(encoding="utf-8")
        helper = text.split("pub fn post_cutover_configure_first_usb_hid_endpoint()", 1)[1]
        helper = helper.split("pub fn sotlas_x86_post_cutover_entry", 1)[0]
        self.assertIn("xhci_configuration_is_ready()", helper)
        self.assertIn("xhci_hid_context_prepare()", helper)
        self.assertIn("xhci_hid_context_is_ready()", helper)
        self.assertIn("xhci_configure_first_hid_endpoint()", helper)
        self.assertIn("xhci_configure_endpoint_is_ready()", helper)
        self.assertIn("xhci_configure_endpoint_dci() != dci", helper)

        entry = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        parser_pos = entry.index("post_cutover_parse_first_usb_hid_interface()")
        configure_pos = entry.index("post_cutover_configure_first_usb_hid_endpoint()")
        marker_pos = entry.index("x86_serial_write_stage_marker('L' as u8)")
        self.assertLess(parser_pos, configure_pos)
        self.assertLess(configure_pos, marker_pos)
        self.assertNotIn("xhci_set_first_configuration()", entry)

    def test_main_registers_configure_endpoint_stage(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_configure_endpoint::*;", text)


if __name__ == "__main__":
    unittest.main()
