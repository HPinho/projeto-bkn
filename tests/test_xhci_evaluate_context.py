#!/usr/bin/env python3
"""Guardrails da atualização de Max Packet Size do EP0."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/xhci_evaluate_context.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciEvaluateContextTests(unittest.TestCase):
    def setUp(self):
        self.text = MODULE.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_stage_requires_address_context_and_command_ring(self):
        for token in (
            "xhci_address_is_ready()",
            "xhci_context_is_ready()",
            "xhci_command_is_ready()",
        ):
            self.assertIn(token, self.text)

    def test_only_ep0_add_flag_is_published(self):
        self.assertIn("XHCI_EVALUATE_ADD_EP0: u32 = 1 << 1", self.text)
        self.assertIn("*drop_flags = 0", self.text)
        self.assertIn("*add_flags = XHCI_EVALUATE_ADD_EP0", self.text)

    def test_max_packet_update_is_masked_and_bounded(self):
        self.assertIn("XHCI_EVALUATE_EP0_MAX_PACKET_MASK", self.text)
        for value in ("8", "16", "32", "64", "512"):
            self.assertIn(f"max_packet == {value}", self.text)

    def test_evaluate_uses_stateful_command_path(self):
        self.assertIn("xhci_trb_evaluate_context(", self.text)
        self.assertIn("xhci_command_submit(command)", self.text)
        self.assertIn("xhci_command_wait_completion(command_physical)", self.text)
        self.assertIn("xhci_command_last_slot_id() != slot_id", self.text)

    def test_main_registers_stage_without_calling_it(self):
        self.assertIn("import kernel::drivers::xhci_evaluate_context::*;", self.main)
        body = self.main.split("pub fn baken_kernel_main", 1)[1]
        self.assertNotIn("xhci_evaluate_ep0_max_packet(", body)


if __name__ == "__main__":
    unittest.main()
