#!/usr/bin/env python3
"""Guardrails da política BIOS→OS para USB Legacy Support xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "kernel/src/drivers/xhci_controller.sotlas"


class XhciLegacyHandoffTests(unittest.TestCase):
    def test_legacy_control_status_is_disabled(self):
        text = CTRL.read_text(encoding="utf-8")
        self.assertIn("XHCI_LEGACY_CONTROL_STATUS", text)
        self.assertIn("fn xhci_legacy_disable_smis", text)
        helper = text.split("fn xhci_legacy_disable_smis", 1)[1].split(
            "fn xhci_legacy_handoff", 1
        )[0]
        self.assertIn("x86_mmio_write32(control, 0)", helper)

    def test_bios_timeout_does_not_abort_controller_bringup(self):
        text = CTRL.read_text(encoding="utf-8")
        handoff = text.split("fn xhci_legacy_handoff", 1)[1].split(
            "fn xhci_wait_halted", 1
        )[0]
        timeout_pos = handoff.index("while spins < XHCI_LEGACY_POLL_LIMIT")
        tail = handoff[timeout_pos:]
        self.assertIn("xhci_legacy_disable_smis(address)", tail)
        self.assertIn("XHCI_LEGACY_OS_OWNED", tail)
        self.assertIn("return true;", tail)
        self.assertNotIn("spins += 1;\n                }\n                return false;", tail)

    def test_normal_release_also_disables_legacy_smis(self):
        text = CTRL.read_text(encoding="utf-8")
        handoff = text.split("fn xhci_legacy_handoff", 1)[1].split(
            "fn xhci_wait_halted", 1
        )[0]
        self.assertGreaterEqual(handoff.count("xhci_legacy_disable_smis(address)"), 3)


if __name__ == "__main__":
    unittest.main()
