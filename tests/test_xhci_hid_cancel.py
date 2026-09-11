#!/usr/bin/env python3
"""Guardrails HID-4d.2b para Stop Endpoint + drain terminal."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "kernel/src/drivers/xhci_event.sotlas"
TRANSFER = ROOT / "kernel/src/drivers/xhci_transfer.sotlas"
REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
LIFECYCLE = ROOT / "kernel/src/drivers/xhci_hid_lifecycle.sotlas"


def function_body(source: str, name: str) -> str:
    """Extract one Sotlas function body without depending on neighbor ordering."""
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", match.end())
    if brace < 0:
        raise AssertionError(f"missing function body {name}")

    depth = 0
    index = brace
    in_string = False
    escaped = False
    line_comment = False
    block_comment = False
    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 2
                continue
            index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
        index += 1

    raise AssertionError(f"unterminated function {name}")


def assert_order(test: unittest.TestCase, body: str, *tokens: str) -> None:
    cursor = 0
    previous = -1
    for token in tokens:
        position = body.find(token, cursor)
        test.assertGreaterEqual(position, 0, f"missing ordered token: {token}")
        test.assertGreater(position, previous)
        previous = position
        cursor = position + len(token)


class XhciHidCancelTests(unittest.TestCase):
    def test_stop_completion_codes_match_xhci_contract(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("XHCI_COMPLETION_CODE_STOPPED: u8 = 26", text)
        self.assertIn("XHCI_COMPLETION_CODE_STOPPED_LENGTH_INVALID: u8 = 27", text)
        self.assertIn("XHCI_COMPLETION_CODE_STOPPED_SHORT_PACKET: u8 = 28", text)

    def test_terminal_waiter_accepts_only_success_or_stop_family(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = function_body(text, "xhci_transfer_wait_stopped_or_completed")
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
        body = function_body(text, "xhci_hid_report_drain_cancelled_for_slot")
        self.assertIn("xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING", body)
        self.assertIn("xhci_transfer_wait_stopped_or_completed(slot_id, dci, physical)", body)
        self.assertIn("transfer_pending = false", body)
        self.assertIn("pending_trb_physical = 0", body)
        self.assertIn("pending_transfer_length = 0", body)
        self.assertIn("last_length = 0", body)
        self.assertNotIn("xhci_hid_report_parse_for_slot", body)
        self.assertNotIn("hid_input_events_process_report_for_device", body)

    def test_lifecycle_does_not_mark_stopped_before_command_drain_and_quiescence(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = function_body(text, "xhci_hid_lifecycle_stop_endpoint_for")
        exact = "xhci_hid_lifecycle_is_detach_pending_for(slot_id, epoch)"
        submit = "xhci_command_submit(command)"
        wait = "xhci_command_wait_completion(command_physical)"
        drain = "xhci_hid_report_drain_cancelled_for_slot(slot_id)"
        quiescent = "xhci_hid_lifecycle_quiescent_for(slot_id, epoch)"
        stopped = "XHCI_HID_LIFECYCLE_STATES[index].endpoint_stopped = true"

        assert_order(self, body, submit, wait, drain, quiescent, stopped)

        wait_pos = body.find(wait)
        drain_pos = body.find(drain)
        quiescent_pos = body.find(quiescent, drain_pos + len(drain))
        before_drain = body.rfind(exact, wait_pos, drain_pos)
        after_drain = body.find(exact, drain_pos + len(drain), quiescent_pos)
        self.assertGreaterEqual(before_drain, wait_pos)
        self.assertGreater(after_drain, drain_pos)

    def test_quiescence_is_generation_safe_and_checks_both_pending_sources(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = function_body(text, "xhci_hid_lifecycle_quiescent_for")
        exact = "xhci_hid_lifecycle_is_detach_pending_for(slot_id, epoch)"
        report = "xhci_hid_report_transfer_pending_for_epoch(slot_id, epoch)"
        mailbox = "xhci_transfer_pending_is_ready_for_epoch(slot_id, epoch)"

        first_exact = body.find(exact)
        report_pos = body.find(report)
        second_exact = body.find(exact, report_pos + len(report))
        mailbox_pos = body.find(mailbox, second_exact + len(exact))
        final_exact = body.find(exact, mailbox_pos + len(mailbox))

        self.assertGreaterEqual(first_exact, 0)
        self.assertGreater(report_pos, first_exact)
        self.assertGreater(second_exact, report_pos)
        self.assertGreater(mailbox_pos, second_exact)
        self.assertGreater(final_exact, mailbox_pos)
        self.assertNotIn("xhci_hid_report_transfer_pending_for(slot_id)", body)
        self.assertNotIn("xhci_transfer_pending_is_ready_for(slot_id)", body)


if __name__ == "__main__":
    unittest.main()
