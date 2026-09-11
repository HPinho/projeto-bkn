#!/usr/bin/env python3
"""Guardrails HID-4d.2b para Stop Endpoint + drain terminal."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "kernel/src/drivers/xhci_event.sotlas"
TRANSFER = ROOT / "kernel/src/drivers/xhci_transfer.sotlas"
REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
LIFECYCLE = ROOT / "kernel/src/drivers/xhci_hid_lifecycle.sotlas"


class XhciHidCancelTests(unittest.TestCase):
    def test_stop_completion_codes_match_xhci_contract(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("XHCI_COMPLETION_CODE_STOPPED: u8 = 26", text)
        self.assertIn("XHCI_COMPLETION_CODE_STOPPED_LENGTH_INVALID: u8 = 27", text)
        self.assertIn("XHCI_COMPLETION_CODE_STOPPED_SHORT_PACKET: u8 = 28", text)

    def test_terminal_waiter_accepts_only_success_or_stop_family(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_transfer_wait_stopped_or_completed", 1)[1]
        body = body.split("pub fn xhci_transfer_wait_ep0_completion", 1)[0]
        self.assertIn("xhci_transfer_wait_completion(slot_id, endpoint_id, completion_trb_physical)", body)
        self.assertIn("xhci_transfer_result_is_valid_for(slot_id)", body)
        self.assertIn("xhci_transfer_last_endpoint_id_for(slot_id) != endpoint_id", body)
        for code in (
            "XHCI_COMPLETION_CODE_STOPPED",
            "XHCI_COMPLETION_CODE_STOPPED_LENGTH_INVALID",
            "XHCI_COMPLETION_CODE_STOPPED_SHORT_PACKET",
        ):
            self.assertIn(code, body)
        self.assertNotIn("XHCI_COMPLETION_CODE_SHORT_PACKET", body)

    def test_cancel_drain_clears_pending_without_parsing_report(self):
        text = REPORT.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_drain_cancelled_for_slot", 1)[1]
        body = body.split("pub fn xhci_hid_report_poll_slot_once", 1)[0]
        self.assertIn("xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING", body)
        self.assertIn("xhci_transfer_wait_stopped_or_completed(slot_id, dci, physical)", body)
        self.assertIn("transfer_pending = false", body)
        self.assertIn("pending_trb_physical = 0", body)
        self.assertIn("pending_transfer_length = 0", body)
        self.assertIn("last_length = 0", body)
        self.assertNotIn("xhci_hid_report_parse_for_slot", body)
        self.assertNotIn("hid_input_events_process_report_for_device", body)

    def test_lifecycle_does_not_mark_stopped_before_command_and_drain(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_lifecycle_stop_endpoint_for", 1)[1]
        body = body.split("pub fn xhci_hid_lifecycle_can_finalize_for", 1)[0]
        submit = body.index("xhci_command_submit(command)")
        wait = body.index("xhci_command_wait_completion(command_physical)")
        drain = body.index("xhci_hid_report_drain_cancelled_for_slot(slot_id)")
        empty_report = body.index("xhci_hid_report_transfer_pending_for(slot_id)", drain)
        empty_mailbox = body.index("xhci_transfer_pending_is_ready_for(slot_id)", empty_report)
        stopped = body.index("XHCI_HID_LIFECYCLE_STATES[index].endpoint_stopped = true")
        self.assertLess(submit, wait)
        self.assertLess(wait, drain)
        self.assertLess(drain, empty_report)
        self.assertLess(empty_report, empty_mailbox)
        self.assertLess(empty_mailbox, stopped)


if __name__ == "__main__":
    unittest.main()
