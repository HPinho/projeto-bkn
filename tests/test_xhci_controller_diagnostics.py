#!/usr/bin/env python3
"""Mantém checkpoints diagnósticos enquanto STEP=X estiver sob bring-up."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "kernel/src/drivers/xhci_controller.sotlas"


class XhciControllerDiagnosticTests(unittest.TestCase):
    def test_bringup_records_monotonic_checkpoints(self):
        text = CONTROLLER.read_text(encoding="utf-8")
        self.assertIn("XHCI_CONTROLLER_BRINGUP_STAGE", text)
        for stage, marker in [
            (1, "'4'"), (2, "'5'"), (3, "'6'"), (4, "'7'"),
            (5, "'8'"), (6, "'9'"), (7, "'q'"), (8, "'w'"),
        ]:
            self.assertIn(f"xhci_controller_checkpoint({stage}, {marker} as u8)", text)

    def test_capability_parameter_subcheckpoints_are_ordered(self):
        text = CONTROLLER.read_text(encoding="utf-8")
        sequence = [
            "xhci_controller_checkpoint(50, 'g' as u8)",
            "xhci_controller_checkpoint(51, 'r' as u8)",
            "xhci_controller_checkpoint(52, 's' as u8)",
            "xhci_controller_checkpoint(53, 'p' as u8)",
            "xhci_controller_checkpoint(54, 'h' as u8)",
            "xhci_controller_checkpoint(55, 'j' as u8)",
        ]
        offsets = [text.index(item) for item in sequence]
        self.assertEqual(offsets, sorted(offsets))
        self.assertLess(text.index("if max_slots == 0"), offsets[2])
        self.assertLess(text.index("if max_ports == 0"), offsets[3])

    def test_reset_checkpoint_is_after_handoff_and_pagesize(self):
        text = CONTROLLER.read_text(encoding="utf-8")
        handoff = text.index("xhci_legacy_handoff(mmio, hccparams1)")
        pagesize = text.index("page_size_mask =")
        reset = text.index("xhci_stop_and_reset(operational)")
        ready = text.index("XHCI_CONTROLLER_READY = true")
        self.assertLess(handoff, pagesize)
        self.assertLess(pagesize, reset)
        self.assertLess(reset, ready)


if __name__ == "__main__":
    unittest.main()
