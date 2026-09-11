#!/usr/bin/env python3
"""Guardrails para queries e demux xHCI exact-epoch antes do teardown 4d.3b2."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
TRANSFER = ROOT / "kernel/src/drivers/xhci_transfer.sotlas"


def function_body(source: str, name: str) -> str:
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


class XhciExactEpochPendingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.transfer = TRANSFER.read_text(encoding="utf-8")

    def test_parser_ignores_comments_and_strings(self) -> None:
        sample = 'fn demo() -> bool {\n// }\nlet text = "{ }";\nif true { return true; }\n}\n'
        body = function_body(sample, "demo")
        self.assertIn("return true", body)

    def test_report_exact_query_requires_expected_epoch_before_and_after_read(self) -> None:
        body = function_body(self.report, "xhci_hid_report_transfer_pending_for_epoch")
        epoch_check = "xhci_device_table_slot_epoch(slot_id) != epoch"
        self.assertGreaterEqual(body.count(epoch_check), 2)
        for token in (
            "epoch == 0",
            "xhci_device_table_slot_is_valid(slot_id)",
            "XHCI_HID_REPORT_STATES[state_index].ready",
            "XHCI_HID_REPORT_STATES[state_index].epoch == epoch",
            "XHCI_HID_REPORT_STATES[state_index].transfer_pending",
            "pending_trb_physical != 0",
            "pending_transfer_length != 0",
        ):
            self.assertIn(token, body)
        first_epoch = body.find(epoch_check)
        state_read = body.find("XHCI_HID_REPORT_STATES[state_index].ready")
        last_epoch = body.rfind(epoch_check)
        self.assertLess(first_epoch, state_read)
        self.assertLess(state_read, last_epoch)

    def test_report_compatibility_wrapper_delegates_to_exact_query(self) -> None:
        body = function_body(self.report, "xhci_hid_report_transfer_pending_for")
        self.assertIn("let epoch = xhci_device_table_slot_epoch(slot_id)", body)
        self.assertIn("xhci_hid_report_transfer_pending_for_epoch(slot_id, epoch)", body)
        self.assertNotIn("XHCI_HID_REPORT_STATES[", body)

    def test_transfer_exact_query_is_generation_scoped_and_side_effect_free(self) -> None:
        body = function_body(self.transfer, "xhci_transfer_pending_is_ready_for_epoch")
        epoch_check = "xhci_device_table_slot_epoch(slot_id) != epoch"
        self.assertGreaterEqual(body.count(epoch_check), 2)
        for token in (
            "epoch == 0",
            "xhci_device_table_slot_is_valid(slot_id)",
            "XHCI_TRANSFER_PENDING_EVENTS[index].valid",
            "XHCI_TRANSFER_PENDING_EVENTS[index].epoch == epoch",
            "endpoint_id != 0",
            "trb_pointer != 0",
        ):
            self.assertIn(token, body)
        self.assertNotIn("xhci_transfer_clear_pending_index", body)
        first_epoch = body.find(epoch_check)
        state_read = body.find("XHCI_TRANSFER_PENDING_EVENTS[index].valid")
        last_epoch = body.rfind(epoch_check)
        self.assertLess(first_epoch, state_read)
        self.assertLess(state_read, last_epoch)

    def test_transfer_compatibility_wrapper_preserves_stale_cleanup_then_delegates(self) -> None:
        body = function_body(self.transfer, "xhci_transfer_pending_is_ready_for")
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].epoch != epoch", body)
        self.assertIn("xhci_transfer_clear_pending_index(index)", body)
        self.assertIn("xhci_transfer_pending_is_ready_for_epoch(slot_id, epoch)", body)
        self.assertLess(
            body.find("xhci_transfer_clear_pending_index(index)"),
            body.find("xhci_transfer_pending_is_ready_for_epoch(slot_id, epoch)"),
        )

    def test_exact_queries_never_depend_on_active_slot_singletons(self) -> None:
        report_body = function_body(self.report, "xhci_hid_report_transfer_pending_for_epoch")
        transfer_body = function_body(self.transfer, "xhci_transfer_pending_is_ready_for_epoch")
        for body in (report_body, transfer_body):
            self.assertNotIn("ACTIVE_SLOT_ID", body)
            self.assertNotRegex(body, r"\b[a-zA-Z0-9_]+_active_slot_id\s*\(")

    def test_demux_exact_match_uses_epoch_scoped_mailbox_only(self) -> None:
        body = function_body(self.transfer, "xhci_transfer_pending_matches_for_epoch")
        self.assertIn("xhci_transfer_pending_is_ready_for_epoch(slot_id, epoch)", body)
        self.assertGreaterEqual(
            body.count("xhci_transfer_pending_is_ready_for_epoch(slot_id, epoch)"), 2
        )
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].epoch == epoch", body)
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].endpoint_id == endpoint_id", body)
        self.assertIn(
            "XHCI_TRANSFER_PENDING_EVENTS[index].trb_pointer == completion_trb_physical",
            body,
        )
        self.assertNotIn("xhci_transfer_pending_is_ready_for(slot_id)", body)
        self.assertNotIn("xhci_transfer_clear_pending_index", body)

    def test_demux_compatibility_match_delegates_after_resolving_current_epoch(self) -> None:
        body = function_body(self.transfer, "xhci_transfer_pending_matches")
        self.assertIn("xhci_transfer_pending_is_ready_for(slot_id)", body)
        self.assertIn("let epoch = xhci_device_table_slot_epoch(slot_id)", body)
        self.assertIn("xhci_transfer_pending_matches_for_epoch(", body)
        self.assertNotIn("XHCI_TRANSFER_PENDING_EVENTS[", body)

    def test_take_pending_cannot_follow_reused_slot_generation(self) -> None:
        body = function_body(self.transfer, "xhci_transfer_take_pending")
        exact = "xhci_transfer_pending_matches_for_epoch("
        self.assertGreaterEqual(body.count(exact), 2)
        self.assertNotIn("xhci_transfer_pending_matches(slot_id", body)
        first_match = body.find(exact)
        snapshot = body.find("XHCI_TRANSFER_PENDING_EVENTS[index].residual_length")
        second_match = body.rfind(exact)
        publish = body.find("XHCI_TRANSFER_RESULTS[index].valid = true")
        self.assertLess(first_match, snapshot)
        self.assertLess(snapshot, second_match)
        self.assertLess(second_match, publish)

    def test_waiter_keeps_captured_epoch_for_mailbox_and_rollover_guard(self) -> None:
        body = function_body(self.transfer, "xhci_transfer_wait_completion")
        self.assertIn("let epoch = xhci_device_table_slot_epoch(slot_id)", body)
        self.assertIn("xhci_transfer_pending_is_ready_for_epoch(slot_id, epoch)", body)
        self.assertIn("xhci_transfer_pending_matches_for_epoch(", body)
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", body)
        self.assertNotIn("xhci_transfer_pending_is_ready_for(slot_id)", body)
        self.assertNotIn("xhci_transfer_pending_matches(slot_id", body)

    def test_event_ring_remains_single_global_consumer_and_routes_to_mailbox(self) -> None:
        route = function_body(self.transfer, "xhci_transfer_route_next_event")
        publish = function_body(self.transfer, "xhci_transfer_publish_pending_event")
        self.assertIn("xhci_event_consumer_peek()", route)
        self.assertIn("xhci_transfer_publish_pending_event(event)", route)
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].epoch = epoch", publish)
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].endpoint_id = endpoint_id", publish)
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].trb_pointer = trb_pointer", publish)
        self.assertIn("xhci_event_consumer_consume()", publish)
        self.assertNotRegex(self.transfer, r"xhci_event_consumer_(?:peek|consume)_for")

    def test_slot_reuse_requires_future_drain_barrier_before_epoch_rollover(self) -> None:
        publish = function_body(self.transfer, "xhci_transfer_publish_pending_event")
        self.assertIn("let epoch = xhci_device_table_slot_epoch(slot_id)", publish)
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].epoch = epoch", publish)
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].epoch == epoch", publish)
        self.assertIn("HID-4d.5", self.transfer)
        self.assertIn("drain/barrier", self.transfer)


if __name__ == "__main__":
    unittest.main()
