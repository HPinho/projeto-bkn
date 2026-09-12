#!/usr/bin/env python3
"""Guardrails HID-4d.3b para preflight fail-closed de estado transfer."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRANSFER = ROOT / "kernel/src/drivers/xhci_transfer.sotlas"
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
    while index < len(source):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
        index += 1
    raise AssertionError(f"unterminated function {name}")


class XhciHidTeardownPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.transfer = TRANSFER.read_text(encoding="utf-8")
        cls.lifecycle = LIFECYCLE.read_text(encoding="utf-8")
        cls.preflight = function_body(
            cls.transfer, "xhci_transfer_teardown_state_safe_for_epoch"
        )
        cls.complete = function_body(
            cls.lifecycle, "xhci_hid_lifecycle_complete_logical_teardown_for"
        )

    def test_preflight_requires_exact_detach_pending_epoch(self):
        self.assertGreaterEqual(
            self.preflight.count("xhci_transfer_teardown_epoch_matches(slot_id, epoch)"),
            2,
        )

    def test_preflight_rejects_any_valid_mailbox(self):
        self.assertIn(
            "if XHCI_TRANSFER_PENDING_EVENTS[index].valid { return false; }",
            self.preflight,
        )
        self.assertNotIn(
            "XHCI_TRANSFER_PENDING_EVENTS[index].epoch == epoch",
            self.preflight,
        )

    def test_preflight_rejects_foreign_valid_result(self):
        self.assertIn("XHCI_TRANSFER_RESULTS[index].valid &&", self.preflight)
        self.assertIn("XHCI_TRANSFER_RESULTS[index].epoch != epoch", self.preflight)

    def test_preflight_is_side_effect_free(self):
        for forbidden in (
            "xhci_transfer_clear_pending_index",
            "XHCI_TRANSFER_RESULTS[index].valid = false",
            "xhci_event_consumer_consume",
            "dma_release",
            "dma_unshare_from_device",
            "xhci_ring",
            "disable_slot",
            "drop_endpoint",
        ):
            self.assertNotIn(forbidden, self.preflight)

    def test_lifecycle_preflight_runs_before_first_logical_cleanup(self):
        preflight = self.complete.find(
            "xhci_transfer_teardown_state_safe_for_epoch(slot_id, epoch)"
        )
        identity = self.complete.find(
            "xhci_hid_descriptor_teardown_input_device_for_epoch(slot_id, epoch)"
        )
        descriptor = self.complete.find(
            "xhci_hid_descriptor_teardown_dma_for_epoch(slot_id, epoch)"
        )
        report = self.complete.find(
            "xhci_hid_report_teardown_dma_for_epoch(slot_id, epoch)"
        )
        transfer = self.complete.find(
            "xhci_transfer_clear_slot_state_for_epoch(slot_id, epoch)"
        )
        self.assertGreaterEqual(preflight, 0)
        self.assertGreater(identity, preflight)
        self.assertGreater(descriptor, identity)
        self.assertGreater(report, descriptor)
        self.assertGreater(transfer, report)

    def test_preflight_is_inside_teardown_lock(self):
        lock = self.complete.find("xhci_hid_lifecycle_teardown_lock_irq()")
        preflight = self.complete.find(
            "xhci_transfer_teardown_state_safe_for_epoch(slot_id, epoch)"
        )
        unlock = self.complete.rfind("xhci_hid_lifecycle_teardown_unlock_irq(flags)")
        self.assertGreater(preflight, lock)
        self.assertGreater(unlock, preflight)


if __name__ == "__main__":
    unittest.main()
