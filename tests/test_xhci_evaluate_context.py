#!/usr/bin/env python3
"""Guardrails da atualização de Max Packet Size do EP0."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/xhci_evaluate_context.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class XhciEvaluateContextTests(unittest.TestCase):
    def setUp(self):
        self.text = MODULE.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")
        self.post = POST.read_text(encoding="utf-8")

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

    def test_descriptor_probe_value_is_normalized_before_evaluate(self):
        self.assertIn("xhci_descriptor_ep0_max_packet_bytes(raw: u8)", self.text)
        self.assertIn("if raw == 9 { return 512; }", self.text)
        self.assertIn("xhci_device_descriptor_probe_max_packet0()", self.text)
        self.assertIn("xhci_device_descriptor_probe_is_ready()", self.text)

    def test_reconcile_skips_redundant_command_but_falls_back_to_evaluate(self):
        self.assertIn("xhci_reconcile_ep0_from_descriptor_probe()", self.text)
        self.assertIn("if xhci_context_ep0_max_packet() == target", self.text)
        self.assertIn("if !xhci_evaluate_ep0_max_packet(target)", self.text)
        self.assertIn("XHCI_EVALUATE_CONTEXT_COMMAND_SUBMITTED", self.text)

    def test_evaluate_uses_stateful_command_path(self):
        self.assertIn("xhci_trb_evaluate_context(", self.text)
        self.assertIn("xhci_command_submit(command)", self.text)
        self.assertIn("xhci_command_wait_completion(command_physical)", self.text)
        self.assertIn("xhci_command_last_slot_id() != slot_id", self.text)

    def test_post_cutover_runs_reconciliation_after_probe(self):
        probe = self.post.index("post_cutover_probe_first_usb_descriptor()")
        reconcile = self.post.index("post_cutover_reconcile_first_usb_ep0()")
        self.assertLess(probe, reconcile)
        self.assertIn("xhci_reconcile_ep0_from_descriptor_probe()", self.post)
        self.assertIn("x86_serial_write_stage_marker('E' as u8)", self.post)

    def test_main_registers_stage_without_calling_it_from_hybrid_entry(self):
        self.assertIn("import kernel::drivers::xhci_evaluate_context::*;", self.main)
        body = self.main.split("pub fn baken_kernel_main", 1)[1]
        self.assertNotIn("xhci_evaluate_ep0_max_packet(", body)
        self.assertNotIn("xhci_reconcile_ep0_from_descriptor_probe(", body)


if __name__ == "__main__":
    unittest.main()
