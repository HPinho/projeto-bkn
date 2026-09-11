#!/usr/bin/env python3
"""Guardrails da atualização per-slot de Max Packet Size do EP0."""

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

    def test_stage_is_keyed_by_slot_and_epoch(self):
        for token in (
            "XHCI_EVALUATE_CONTEXT_EPOCHS",
            "XHCI_EVALUATE_CONTEXT_LAST_EP0_MAX_PACKETS",
            "XHCI_EVALUATE_CONTEXT_COMMAND_SUBMITTED_SLOTS",
            "xhci_device_table_slot_epoch(slot_id)",
        ):
            self.assertIn(token, self.text)
        self.assertNotIn("static mut XHCI_EVALUATE_CONTEXT_LAST_EP0_MAX_PACKET:", self.text)
        self.assertNotIn("static mut XHCI_EVALUATE_CONTEXT_COMMAND_SUBMITTED:", self.text)

    def test_stage_requires_matching_slot_state(self):
        for token in (
            "xhci_device_table_slot_is_valid(slot_id)",
            "xhci_address_is_ready_for(slot_id)",
            "xhci_context_is_ready_for(slot_id)",
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

    def test_evaluate_uses_context_of_same_slot(self):
        self.assertIn("pub fn xhci_evaluate_ep0_max_packet_for_slot(slot_id: u8, max_packet: u16)", self.text)
        self.assertIn("xhci_context_input_physical_for(slot_id)", self.text)
        self.assertIn("xhci_context_size_for(slot_id)", self.text)
        self.assertIn("xhci_trb_evaluate_context(\n        input_physical,\n        slot_id,", self.text)
        self.assertIn("xhci_command_last_slot_id() != slot_id", self.text)

    def test_descriptor_probe_is_normalized_per_slot(self):
        self.assertIn("xhci_descriptor_ep0_max_packet_bytes(raw: u8)", self.text)
        self.assertIn("if raw == 9 { return 512; }", self.text)
        self.assertIn("xhci_device_descriptor_probe_max_packet0_for(slot_id)", self.text)
        self.assertIn("xhci_device_descriptor_probe_is_ready_for(slot_id)", self.text)

    def test_reconcile_uses_matching_ep0_and_falls_back_to_evaluate(self):
        self.assertIn("pub fn xhci_reconcile_ep0_from_descriptor_probe_for_slot(slot_id: u8)", self.text)
        self.assertIn("xhci_context_ep0_max_packet_for(slot_id) == target", self.text)
        self.assertIn("if !xhci_evaluate_ep0_max_packet_for_slot(slot_id, target)", self.text)
        self.assertIn("xhci_evaluate_context_last_ep0_max_packet_for_slot(slot_id) == target", self.text)

    def test_legacy_wrappers_delegate_to_address_slot(self):
        for signature in (
            "pub fn xhci_evaluate_ep0_max_packet(max_packet: u16)",
            "pub fn xhci_reconcile_ep0_from_descriptor_probe()",
            "pub fn xhci_evaluate_context_last_ep0_max_packet()",
            "pub fn xhci_evaluate_context_command_submitted()",
        ):
            self.assertIn(signature, self.text)
        self.assertGreaterEqual(self.text.count("let slot_id = xhci_address_slot_id();"), 4)

    def test_post_cutover_keeps_certified_wrapper_path(self):
        probe = self.post.index("post_cutover_probe_first_usb_descriptor()")
        reconcile = self.post.index("post_cutover_reconcile_first_usb_ep0()")
        self.assertLess(probe, reconcile)
        self.assertIn("xhci_reconcile_ep0_from_descriptor_probe()", self.post)
        self.assertIn("xhci_evaluate_context_last_ep0_max_packet() != target", self.post)
        self.assertIn("x86_serial_write_stage_marker('E' as u8)", self.post)

    def test_main_registers_stage_without_calling_it_from_hybrid_entry(self):
        self.assertIn("import kernel::drivers::xhci_evaluate_context::*;", self.main)
        self.assertNotIn("pub fn baken_kernel_main", self.main)


if __name__ == "__main__":
    unittest.main()
