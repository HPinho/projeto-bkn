#!/usr/bin/env python3
"""Guardrails do alias operacional xHCI durante a finalização HID-4d.5."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "kernel/src/drivers/xhci_device_table.sotlas"
SLOT = ROOT / "kernel/src/drivers/xhci_slot.sotlas"


class XhciSlotActiveAliasTests(unittest.TestCase):
    def test_set_active_rejects_terminal_non_operational_states(self):
        text = TABLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_device_table_set_active", 1)[1].split("@system", 1)[0]
        self.assertIn("XHCI_DEVICE_STATE_FAILED", body)
        self.assertIn("XHCI_DEVICE_STATE_DETACH_PENDING", body)
        assignment = body.index("XHCI_DEVICE_ACTIVE_SLOT_ID = slot_id")
        self.assertLess(body.index("XHCI_DEVICE_STATE_FAILED"), assignment)
        self.assertLess(body.index("XHCI_DEVICE_STATE_DETACH_PENDING"), assignment)

    def test_release_reselects_only_operational_candidate(self):
        text = TABLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_device_table_release", 1)[1].split("@system", 1)[0]
        self.assertIn("candidate.valid", body)
        self.assertIn("candidate.state != XHCI_DEVICE_STATE_FAILED", body)
        self.assertIn("candidate.state != XHCI_DEVICE_STATE_DETACH_PENDING", body)
        assignment = body.index("XHCI_DEVICE_ACTIVE_SLOT_ID = scan as u8")
        self.assertLess(body.index("candidate.state != XHCI_DEVICE_STATE_FAILED"), assignment)
        self.assertLess(body.index("candidate.state != XHCI_DEVICE_STATE_DETACH_PENDING"), assignment)

    def test_slot_readiness_rejects_failed_and_detach_pending(self):
        text = SLOT.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_slot_is_ready_for", 1)[1].split("@system", 1)[0]
        self.assertIn("XHCI_DEVICE_STATE_FAILED", body)
        self.assertIn("XHCI_DEVICE_STATE_DETACH_PENDING", body)

    def test_alias_filter_keeps_enumeration_states_eligible(self):
        text = TABLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_device_table_set_active", 1)[1].split("@system", 1)[0]
        self.assertNotIn("== XHCI_DEVICE_STATE_HID_READY", body)
        self.assertNotIn("== XHCI_DEVICE_STATE_ADDRESSED", body)
        self.assertNotIn("== XHCI_DEVICE_STATE_CONTEXT_READY", body)


if __name__ == "__main__":
    unittest.main()
