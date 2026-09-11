from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "kernel/src/drivers/xhci_hid_lifecycle.sotlas"
DEVICE_TABLE = ROOT / "kernel/src/drivers/xhci_device_table.sotlas"
REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


def function_body(source: str, name: str) -> str:
    """Extract one Sotlas function body without relying on neighboring functions."""
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


class XhciHidLifecycleTests(unittest.TestCase):
    def test_lifecycle_is_in_canonical_graph_not_legacy_post_cutover(self):
        main = MAIN.read_text(encoding="utf-8")
        post = POST.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_hid_lifecycle::*;", main)
        self.assertNotIn("xhci_hid_lifecycle_scan_detached(", post)
        self.assertNotIn("xhci_hid_lifecycle_stop_endpoint_for(", post)

    def test_detach_pending_has_dedicated_generation_safe_transition(self):
        text = DEVICE_TABLE.read_text(encoding="utf-8")
        self.assertIn("pub const XHCI_DEVICE_STATE_DETACH_PENDING: u8 = 6", text)
        body = function_body(text, "xhci_device_table_mark_detach_pending")
        self.assertIn("XHCI_DEVICE_SLOTS[index].epoch != epoch", body)
        self.assertIn("XHCI_DEVICE_SLOTS[index].state = XHCI_DEVICE_STATE_DETACH_PENDING", body)

    def test_detach_detection_is_read_only_and_same_epoch(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = function_body(text, "xhci_hid_lifecycle_mark_detached_for")
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", body)
        self.assertIn("xhci_port_snapshot(port_id)", body)
        self.assertIn("(*snapshot).connected", body)
        self.assertIn("xhci_device_table_mark_detach_pending(slot_id, epoch)", body)
        self.assertIn("xhci_hid_lifecycle_publish_detach(slot_id, epoch)", body)

    def test_stop_endpoint_is_generation_safe_and_ordered(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = function_body(text, "xhci_hid_lifecycle_stop_endpoint_for")
        for token in (
            "xhci_hid_lifecycle_is_detach_pending_for(slot_id, epoch)",
            "XHCI_HID_LIFECYCLE_STATES[index].epoch != epoch",
            "xhci_hid_context_dci_for(slot_id)",
            "xhci_hid_report_transfer_pending_for(slot_id)",
            "xhci_trb_stop_endpoint(",
            "xhci_command_submit(command)",
            "xhci_command_wait_completion(command_physical)",
            "xhci_command_last_slot_id() != slot_id",
            "xhci_hid_report_drain_cancelled_for_slot(slot_id)",
            "xhci_hid_lifecycle_quiescent_for(slot_id, epoch)",
            "XHCI_HID_LIFECYCLE_STATES[index].endpoint_stopped = true",
        ):
            self.assertIn(token, body)
        assert_order(
            self,
            body,
            "xhci_command_submit(command)",
            "xhci_command_wait_completion(command_physical)",
            "xhci_hid_report_drain_cancelled_for_slot(slot_id)",
            "xhci_hid_lifecycle_quiescent_for(slot_id, epoch)",
            "XHCI_HID_LIFECYCLE_STATES[index].endpoint_stopped = true",
        )

    def test_stop_cut_still_does_not_release_slot_or_identity(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        for forbidden in (
            "xhci_trb_disable_slot",
            "xhci_hid_descriptor_release_input_device_for_slot",
            "input_device_detach",
            "xhci_device_table_release(",
            "dma_release",
            "xhci_hid_context_release",
        ):
            self.assertNotIn(forbidden, text)

    def test_scan_is_bounded_and_refreshes_port_inventory_once(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = function_body(text, "xhci_hid_lifecycle_scan_detached")
        self.assertEqual(body.count("xhci_port_scan()"), 1)
        self.assertIn("while index < XHCI_DEVICE_SLOT_CAPACITY", body)

    def test_report_cancel_drain_does_not_parse_input(self):
        text = REPORT.read_text(encoding="utf-8")
        body = function_body(text, "xhci_hid_report_drain_cancelled_for_slot")
        self.assertIn("XHCI_DEVICE_STATE_DETACH_PENDING", body)
        self.assertIn("xhci_transfer_wait_stopped_or_completed(slot_id, dci, physical)", body)
        self.assertIn("transfer_pending = false", body)
        self.assertIn("pending_trb_physical = 0", body)
        self.assertIn("pending_transfer_length = 0", body)
        self.assertNotIn("xhci_hid_report_parse_for_slot", body)
        self.assertNotIn("hid_input_events_process_report_for_device", body)

    def test_finalize_requires_endpoint_stopped_then_generation_safe_quiescence(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = function_body(text, "xhci_hid_lifecycle_can_finalize_for")
        assert_order(
            self,
            body,
            "xhci_hid_lifecycle_endpoint_stopped_for(slot_id, epoch)",
            "xhci_hid_lifecycle_quiescent_for(slot_id, epoch)",
        )
        self.assertNotIn("xhci_hid_report_transfer_pending_for(slot_id)", body)
        self.assertNotIn("xhci_transfer_pending_is_ready_for(slot_id)", body)

        quiescent = function_body(text, "xhci_hid_lifecycle_quiescent_for")
        exact = "xhci_hid_lifecycle_is_detach_pending_for(slot_id, epoch)"
        report = "xhci_hid_report_transfer_pending_for(slot_id)"
        mailbox = "xhci_transfer_pending_is_ready_for(slot_id)"
        first_exact = quiescent.find(exact)
        report_pos = quiescent.find(report)
        second_exact = quiescent.find(exact, report_pos + len(report))
        mailbox_pos = quiescent.find(mailbox, second_exact + len(exact))
        final_exact = quiescent.find(exact, mailbox_pos + len(mailbox))
        self.assertGreaterEqual(first_exact, 0)
        self.assertGreater(report_pos, first_exact)
        self.assertGreater(second_exact, report_pos)
        self.assertGreater(mailbox_pos, second_exact)
        self.assertGreater(final_exact, mailbox_pos)

    def test_lifecycle_does_not_use_global_singleton_slot_apis(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        forbidden_patterns = (
            r"\bxhci_hid_report_active_slot_id\s*\(",
            r"\bxhci_transfer_active_slot_id\s*\(",
            r"\bxhci_address_slot_id\s*\(",
            r"\bxhci_hid_report_is_ready\s*\(\s*\)",
        )
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, text), pattern)


if __name__ == "__main__":
    unittest.main()
