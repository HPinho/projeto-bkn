#!/usr/bin/env python3
"""Guardrail HID-4d.4b: Transfer Events antigos precisam estar drenados antes de Disable Slot."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEARDOWN = ROOT / "kernel/src/drivers/xhci_slot_teardown.sotlas"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", match.end())
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
    raise AssertionError(f"unterminated body {name}")


class XhciSlotDisableTransferPreconditionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = TEARDOWN.read_text(encoding="utf-8")
        cls.capture = function_body(
            cls.text, "xhci_slot_teardown_capture_physical_preconditions_for"
        )
        cls.orchestrate = function_body(
            cls.text, "xhci_slot_teardown_disable_and_release_context_for"
        )

    def test_uses_existing_transfer_layer_not_second_event_consumer(self):
        self.assertIn("import kernel::drivers::xhci_transfer::*;", self.text)
        self.assertNotIn("import kernel::drivers::xhci_event_consumer::*;", self.text)
        self.assertNotIn("xhci_event_consumer_", self.orchestrate)

    def test_capture_requires_transfer_state_safe(self):
        logical = self.capture.index(
            "xhci_slot_teardown_logical_state_complete_for(slot_id, epoch)"
        )
        transfer = self.capture.index(
            "xhci_transfer_teardown_state_safe_for_epoch(slot_id, epoch)", logical
        )
        publish = self.capture.index("preconditions_captured: true", transfer)
        self.assertLess(logical, transfer)
        self.assertLess(transfer, publish)

    def test_transfer_state_is_rechecked_after_reuse_block_and_before_disable(self):
        block = self.orchestrate.index("xhci_slot_reuse_guard_block_for")
        transfer = self.orchestrate.index(
            "xhci_transfer_teardown_state_safe_for_epoch(slot_id, epoch)", block
        )
        attempted = self.orchestrate.index("disable_attempted = true", transfer)
        command = self.orchestrate.index("xhci_trb_disable_slot", attempted)
        self.assertLess(block, transfer)
        self.assertLess(transfer, attempted)
        self.assertLess(attempted, command)

    def test_no_post_disable_stale_event_cleanup_is_added(self):
        command = self.orchestrate.index("xhci_trb_disable_slot")
        tail = self.orchestrate[command:]
        self.assertNotIn("xhci_transfer_route_next_event", tail)
        self.assertNotIn("xhci_event_consumer_consume", tail)
        self.assertNotIn("xhci_transfer_clear_slot_state_for_epoch", tail)


if __name__ == "__main__":
    unittest.main()
