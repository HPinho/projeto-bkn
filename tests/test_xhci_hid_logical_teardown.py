#!/usr/bin/env python3
"""Guardrails for HID-4d.3b1 logical teardown transaction gate."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "kernel/src/drivers/xhci_hid_lifecycle.sotlas"


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


def ordered_positions(body: str, *tokens: str) -> list[int]:
    positions: list[int] = []
    start = 0
    for token in tokens:
        position = body.find(token, start)
        if position < 0:
            raise AssertionError(f"missing ordered token: {token}")
        positions.append(position)
        start = position + len(token)
    return positions


class HidLogicalTeardownGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = LIFECYCLE.read_text(encoding="utf-8")

    def test_function_parser_ignores_comments_and_strings(self) -> None:
        sample = 'fn demo() -> bool {\n// } ignored\nlet text = "{ }";\nif true { return true; }\n}\n'
        body = function_body(sample, "demo")
        self.assertIn("return true", body)
        self.assertIn('"{ }"', body)

    def test_lifecycle_tracks_transaction_per_epoch(self) -> None:
        self.assertRegex(self.source, r"\bpub\s+logical_teardown_started\s*:\s*bool\s*;")
        self.assertRegex(self.source, r"\blogical_teardown_started\s*:\s*false\b")
        publish = function_body(self.source, "xhci_hid_lifecycle_publish_detach")
        ordered_positions(
            publish,
            ".epoch = epoch;",
            ".detach_detected = true;",
            ".endpoint_stopped = false;",
            ".logical_teardown_started = false;",
        )

    def test_quiescence_uses_exact_epoch_pending_apis_with_revalidation(self) -> None:
        body = function_body(self.source, "xhci_hid_lifecycle_quiescent_for")
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

    def test_stop_endpoint_uses_exact_pending_and_revalidates_slot_only_drain(self) -> None:
        body = function_body(self.source, "xhci_hid_lifecycle_stop_endpoint_for")
        exact = "xhci_hid_lifecycle_is_detach_pending_for(slot_id, epoch)"
        pending = "xhci_hid_report_transfer_pending_for_epoch(slot_id, epoch)"
        command_wait = "xhci_command_wait_completion(command_physical)"
        drain = "xhci_hid_report_drain_cancelled_for_slot(slot_id)"
        quiescent = "xhci_hid_lifecycle_quiescent_for(slot_id, epoch)"

        pending_pos = body.find(pending)
        self.assertGreaterEqual(pending_pos, 0)
        self.assertGreater(body.find(exact, pending_pos + len(pending)), pending_pos)
        self.assertNotIn("xhci_hid_report_transfer_pending_for(slot_id)", body)

        wait_pos = body.find(command_wait)
        drain_pos = body.find(drain)
        self.assertGreaterEqual(wait_pos, 0)
        self.assertGreater(drain_pos, wait_pos)
        before_drain = body.rfind(exact, wait_pos, drain_pos)
        after_drain = body.find(exact, drain_pos + len(drain))
        self.assertGreaterEqual(before_drain, wait_pos)
        self.assertGreater(after_drain, drain_pos)
        self.assertGreater(body.find(quiescent, after_drain), after_drain)

    def test_begin_requires_finalize_gate_before_mutation(self) -> None:
        body = function_body(
            self.source, "xhci_hid_lifecycle_begin_logical_teardown_for"
        )
        gate = body.find("xhci_hid_lifecycle_can_finalize_for(slot_id, epoch)")
        mutation = body.find(".logical_teardown_started = true;")
        self.assertGreaterEqual(gate, 0)
        self.assertGreater(mutation, gate)
        self.assertRegex(body, r"\.epoch\s*!=\s*epoch")
        self.assertIn("detach_detected", body)
        self.assertIn("endpoint_stopped", body)

    def test_begin_is_idempotent_for_same_generation(self) -> None:
        body = function_body(
            self.source, "xhci_hid_lifecycle_begin_logical_teardown_for"
        )
        self.assertRegex(
            body,
            r"if\s+XHCI_HID_LIFECYCLE_STATES\s*\[\s*index\s*\]"
            r"\.logical_teardown_started\s*\{\s*return\s+true\s*;\s*\}",
        )

    def test_query_revalidates_exact_current_generation(self) -> None:
        body = function_body(
            self.source, "xhci_hid_lifecycle_logical_teardown_started_for"
        )
        self.assertIn("xhci_hid_lifecycle_is_detach_pending_for(slot_id, epoch)", body)
        self.assertRegex(body, r"\.epoch\s*==\s*epoch")
        self.assertIn("logical_teardown_started", body)

    def test_can_finalize_uses_epoch_scoped_quiescence_gate(self) -> None:
        body = function_body(self.source, "xhci_hid_lifecycle_can_finalize_for")
        ordered_positions(
            body,
            "xhci_hid_lifecycle_endpoint_stopped_for(slot_id, epoch)",
            "xhci_hid_lifecycle_quiescent_for(slot_id, epoch)",
        )
        self.assertNotIn("xhci_hid_report_transfer_pending_for(slot_id)", body)
        self.assertNotIn("xhci_transfer_pending_is_ready_for(slot_id)", body)

    def test_lifecycle_rejects_global_or_singleton_legacy_apis(self) -> None:
        forbidden_patterns = (
            r"\bxhci_hid_report_active_slot_id\s*\(",
            r"\bxhci_transfer_active_slot_id\s*\(",
            r"\bxhci_hid_report_is_ready\s*\(\s*\)",
            r"\bxhci_transfer_last_residual_length\s*\(\s*\)",
            r"\bxhci_transfer_last_completion_code\s*\(\s*\)",
            r"\bxhci_address_slot_id\s*\(",
        )
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, self.source), pattern)

    def test_3b1_scope_does_not_release_physical_resources(self) -> None:
        forbidden = (
            "dma_release",
            "dma_unshare_from_device",
            "drop_endpoint",
            "disable_slot",
            "input_device_detach",
            "xhci_hid_context_release",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)


if __name__ == "__main__":
    unittest.main()
