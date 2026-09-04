#!/usr/bin/env python3
"""Guardrails dos subcheckpoints de bring-up xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "kernel/src/drivers/xhci_controller.sotlas"


class XhciControllerSubstageTests(unittest.TestCase):
    def test_parameter_checkpoints_follow_nonzero_slots_and_ports(self):
        text = CTRL.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_controller_prepare_first()", 1)[1]

        slots_guard = body.index("if max_slots == 0")
        slots_marker = body.index("xhci_controller_checkpoint(52, 's' as u8)")
        ports_guard = body.index("if max_ports == 0")
        ports_marker = body.index("xhci_controller_checkpoint(53, 'p' as u8)")
        params_marker = body.index("xhci_controller_checkpoint(54, 'h' as u8)")

        self.assertLess(slots_guard, slots_marker)
        self.assertLess(slots_marker, ports_guard)
        self.assertLess(ports_guard, ports_marker)
        self.assertLess(ports_marker, params_marker)

    def test_handoff_entry_and_success_are_distinct(self):
        text = CTRL.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_controller_prepare_first()", 1)[1]
        before = body.index("xhci_controller_checkpoint(55, 'j' as u8)")
        handoff = body.index("xhci_legacy_handoff(mmio, hccparams1)")
        success = body.index("xhci_controller_checkpoint(6, '9' as u8)")
        self.assertLess(before, handoff)
        self.assertLess(handoff, success)


if __name__ == "__main__":
    unittest.main()
