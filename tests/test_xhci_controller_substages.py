#!/usr/bin/env python3
"""Guardrails dos subcheckpoints de bring-up xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "kernel/src/drivers/xhci_controller.sotlas"


class XhciControllerSubstageTests(unittest.TestCase):
    def test_parameter_checkpoint_follows_nonzero_slots_and_ports(self):
        text = CTRL.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_controller_prepare_first()", 1)[1]
        guard = body.index("if max_slots == 0 || max_ports == 0")
        marker = body.index("xhci_controller_checkpoint(51, 'h' as u8)")
        self.assertLess(guard, marker)

    def test_handoff_entry_and_success_are_distinct(self):
        text = CTRL.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_controller_prepare_first()", 1)[1]
        before = body.index("xhci_controller_checkpoint(52, 'j' as u8)")
        handoff = body.index("xhci_legacy_handoff(mmio, hccparams1)")
        success = body.index("xhci_controller_checkpoint(6, '9' as u8)")
        self.assertLess(before, handoff)
        self.assertLess(handoff, success)


if __name__ == "__main__":
    unittest.main()
