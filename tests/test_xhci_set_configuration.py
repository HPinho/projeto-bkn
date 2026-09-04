#!/usr/bin/env python3
"""Guardrails do SET_CONFIGURATION USB sobre EP0."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "kernel/src/drivers/xhci_set_configuration.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciSetConfigurationTests(unittest.TestCase):
    def test_stage_requires_parsed_configuration_and_configured_endpoint(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("xhci_configuration_is_ready()", text)
        self.assertIn("xhci_configure_endpoint_is_ready()", text)
        self.assertIn("xhci_ep0_is_ready()", text)

    def test_setup_is_standard_host_to_device_set_configuration(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("USB_REQUEST_TYPE_HOST_TO_DEVICE_STANDARD_DEVICE: u8 = 0x00", text)
        self.assertIn("USB_REQUEST_SET_CONFIGURATION: u8 = 9", text)
        self.assertIn("configuration_value as u16", text)
        self.assertIn("XHCI_SETUP_TRT_NO_DATA", text)

    def test_no_data_transfer_uses_status_in_with_ioc(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("xhci_trb_status_stage(true, true", text)
        self.assertIn("xhci_ep0_submit_control_td", text)
        self.assertIn("false\n    );", text)

    def test_stage_requires_real_transfer_event_success(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("xhci_transfer_wait_ep0_completion", text)
        self.assertIn("xhci_transfer_last_residual_length() != 0", text)

    def test_stage_does_not_publish_hid_reports(self):
        text = STAGE.read_text(encoding="utf-8").lower()
        self.assertNotIn("hid_report", text)
        self.assertNotIn("interrupt_in", text)
        self.assertNotIn("doorbell", text)

    def test_main_registers_set_configuration(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_set_configuration::*;", text)


if __name__ == "__main__":
    unittest.main()
