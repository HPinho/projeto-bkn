#!/usr/bin/env python3
"""Guardrails HID-4d.3b para report DMA e estado lógico de transfer."""

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


def ordered_positions(body: str, *tokens: str) -> list[int]:
    positions: list[int] = []
    cursor = 0
    for token in tokens:
        position = body.find(token, cursor)
        if position < 0:
            raise AssertionError(f"missing ordered token: {token}")
        positions.append(position)
        cursor = position + len(token)
    return positions


class XhciHidReportTransferTeardownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = REPORT.read_text(encoding="utf-8")
        cls.transfer = TRANSFER.read_text(encoding="utf-8")
        cls.report_gate = function_body(
            cls.report, "xhci_hid_report_teardown_epoch_matches"
        )
        cls.report_quiescent = function_body(
            cls.report, "xhci_hid_report_teardown_quiescent_for_epoch"
        )
        cls.report_teardown = function_body(
            cls.report, "xhci_hid_report_teardown_dma_for_epoch"
        )
        cls.transfer_gate = function_body(
            cls.transfer, "xhci_transfer_teardown_epoch_matches"
        )
        cls.transfer_clear = function_body(
            cls.transfer, "xhci_transfer_clear_slot_state_for_epoch"
        )

    def test_report_gate_requires_exact_detach_pending_epoch(self):
        for token in (
            "epoch == 0",
            "xhci_device_table_slot_is_valid(slot_id)",
            "xhci_device_table_slot_epoch(slot_id) != epoch",
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING",
            "XHCI_HID_REPORT_STATES[state_index].epoch == epoch",
        ):
            self.assertIn(token, self.report_gate)

    def test_report_quiescence_rejects_all_td_pending_forms_and_exact_mailbox(self):
        for token in (
            "XHCI_HID_REPORT_STATES[state_index].transfer_pending",
            "XHCI_HID_REPORT_STATES[state_index].pending_trb_physical != 0",
            "XHCI_HID_REPORT_STATES[state_index].pending_transfer_length != 0",
            "xhci_transfer_pending_is_ready_for_epoch(slot_id, epoch)",
        ):
            self.assertIn(token, self.report_quiescent)
        self.assertGreaterEqual(
            self.report_quiescent.count(
                "xhci_hid_report_teardown_epoch_matches(slot_id, epoch)"
            ),
            2,
        )

    def test_report_teardown_requires_identity_and_descriptor_already_gone(self):
        ordered_positions(
            self.report_teardown,
            "xhci_hid_report_teardown_quiescent_for_epoch(slot_id, epoch)",
            "xhci_hid_descriptor_input_device_id_for(slot_id) != INPUT_DEVICE_ID_NONE",
            "xhci_hid_descriptor_input_device_generation_for(slot_id) != INPUT_DEVICE_GENERATION_INVALID",
            "xhci_hid_descriptor_is_ready_for(slot_id)",
        )

    def test_report_dma_unshares_then_releases_with_retry_safe_cpu_path(self):
        self.assertIn(
            "cpu_owned = dma_buffer_cpu_owned(&XHCI_HID_REPORT_STATES[state_index].buffer)",
            self.report_teardown,
        )
        self.assertIn("if !shared && !cpu_owned { return false; }", self.report_teardown)
        ordered_positions(
            self.report_teardown,
            "dma_buffer_shared(&XHCI_HID_REPORT_STATES[state_index].buffer)",
            "dma_unshare_from_device(&mut XHCI_HID_REPORT_STATES[state_index].buffer)",
            "dma_buffer_cpu_owned(&XHCI_HID_REPORT_STATES[state_index].buffer)",
            "dma_release(&mut XHCI_HID_REPORT_STATES[state_index].buffer)",
        )
        self.assertGreaterEqual(
            self.report_teardown.count(
                "xhci_hid_report_teardown_quiescent_for_epoch(slot_id, epoch)"
            ),
            4,
        )

    def test_report_logical_state_is_cleared_only_after_dma_release(self):
        release = self.report_teardown.find("dma_release(")
        ready_clear = self.report_teardown.rfind(
            "XHCI_HID_REPORT_STATES[state_index].ready = false"
        )
        buffer_clear = self.report_teardown.rfind(
            "XHCI_HID_REPORT_STATES[state_index].buffer = dma_invalid_buffer()"
        )
        self.assertGreater(release, 0)
        self.assertGreater(ready_clear, release)
        self.assertGreater(buffer_clear, ready_clear)
        self.assertNotIn("XHCI_HID_REPORT_STATES[state_index].epoch =", self.report_teardown)
        self.assertIn("XHCI_HID_REPORT_ACTIVE_SLOT_ID = 0", self.report_teardown)

    def test_report_teardown_does_not_touch_ring_context_or_slot(self):
        for forbidden in (
            "xhci_hid_report_ring_slot",
            "xhci_hid_report_ring_physical",
            "xhci_hid_context_release",
            "xhci_configure_endpoint",
            "drop_endpoint",
            "disable_slot",
            "pmm_free",
        ):
            self.assertNotIn(forbidden, self.report_teardown)

    def test_transfer_gate_requires_exact_detach_pending_epoch(self):
        for token in (
            "epoch == 0",
            "xhci_device_table_slot_is_valid(slot_id)",
            "xhci_device_table_slot_epoch(slot_id) != epoch",
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING",
        ):
            self.assertIn(token, self.transfer_gate)

    def test_transfer_clear_refuses_live_same_epoch_mailbox_before_mutation(self):
        valid_token = "XHCI_TRANSFER_PENDING_EVENTS[index].valid"
        epoch_token = "XHCI_TRANSFER_PENDING_EVENTS[index].epoch == epoch"
        clear_token = "xhci_transfer_clear_pending_index(index)"

        first_valid = self.transfer_clear.find(valid_token)
        first_epoch = self.transfer_clear.find(epoch_token, first_valid)
        second_valid = self.transfer_clear.find(valid_token, first_epoch + len(epoch_token))
        second_epoch = self.transfer_clear.find(epoch_token, second_valid)
        clear_pending = self.transfer_clear.find(clear_token, second_epoch)

        self.assertGreaterEqual(first_valid, 0)
        self.assertGreater(first_epoch, first_valid)
        self.assertGreater(second_valid, first_epoch)
        self.assertGreater(second_epoch, second_valid)
        self.assertGreater(clear_pending, second_epoch)
        self.assertGreaterEqual(
            self.transfer_clear.count(
                "xhci_transfer_teardown_epoch_matches(slot_id, epoch)"
            ),
            4,
        )

    def test_transfer_clear_invalidates_result_and_legacy_active_slot(self):
        clear_pending = self.transfer_clear.find("xhci_transfer_clear_pending_index(index)")
        result_clear = self.transfer_clear.find("XHCI_TRANSFER_RESULTS[index].valid = false")
        active_clear = self.transfer_clear.find("XHCI_TRANSFER_ACTIVE_SLOT_ID = 0")
        self.assertGreater(result_clear, clear_pending)
        self.assertGreater(active_clear, result_clear)
        for token in (
            "XHCI_TRANSFER_RESULTS[index].epoch = 0",
            "XHCI_TRANSFER_RESULTS[index].endpoint_id = 0",
            "XHCI_TRANSFER_RESULTS[index].residual_length = 0",
            "XHCI_TRANSFER_RESULTS[index].completion_code = 0",
        ):
            self.assertIn(token, self.transfer_clear)

    def test_transfer_logical_clear_never_consumes_event_ring_or_touches_physical_ring(self):
        for forbidden in (
            "xhci_event_consumer_peek",
            "xhci_event_consumer_consume",
            "xhci_transfer_publish_pending_event",
            "xhci_ring",
            "xhci_hid_context",
            "drop_endpoint",
            "disable_slot",
            "dma_release",
            "pmm_free",
            "XHCI_TRANSFER_ROUTED_EVENT_COUNT",
        ):
            self.assertNotIn(forbidden, self.transfer_clear)


if __name__ == "__main__":
    unittest.main()
