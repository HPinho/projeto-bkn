#!/usr/bin/env python3
"""Guardrails dos construtores puros de Command/Link TRBs xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRB = ROOT / "kernel/src/drivers/xhci_trb.sotlas"


def code_without_comments(path: Path) -> str:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        lines.append(raw.split("//", 1)[0])
    return "\n".join(lines)


class XhciTrbTests(unittest.TestCase):
    def test_command_type_ids_match_xhci_contract(self):
        text = TRB.read_text(encoding="utf-8")
        self.assertIn("XHCI_TRB_TYPE_LINK: u32 = 6", text)
        self.assertIn("XHCI_TRB_TYPE_ENABLE_SLOT: u32 = 9", text)
        self.assertIn("XHCI_TRB_TYPE_DISABLE_SLOT: u32 = 10", text)
        self.assertIn("XHCI_TRB_TYPE_ADDRESS_DEVICE: u32 = 11", text)
        self.assertIn("XHCI_TRB_TYPE_CONFIGURE_ENDPOINT: u32 = 12", text)
        self.assertIn("XHCI_TRB_TYPE_EVALUATE_CONTEXT: u32 = 13", text)
        self.assertIn("XHCI_TRB_TYPE_NOOP_COMMAND: u32 = 23", text)

    def test_type_cycle_slot_and_flag_bitfields_are_explicit(self):
        text = TRB.read_text(encoding="utf-8")
        self.assertIn("XHCI_TRB_CYCLE_BIT: u32 = 1", text)
        self.assertIn("XHCI_TRB_TOGGLE_CYCLE_BIT: u32 = 1 << 1", text)
        self.assertIn("XHCI_TRB_BSR_OR_DC_BIT: u32 = 1 << 9", text)
        self.assertIn("XHCI_TRB_TYPE_SHIFT: u32 = 10", text)
        self.assertIn("XHCI_TRB_SLOT_TYPE_SHIFT: u32 = 16", text)
        self.assertIn("XHCI_TRB_SLOT_ID_SHIFT: u32 = 24", text)

    def test_input_context_pointer_is_16_byte_aligned(self):
        text = TRB.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("input_context_physical & 0xFFFFFFFFFFFFFFF0"), 3)

    def test_link_pointer_is_16_byte_aligned_and_toggle_is_optional(self):
        text = TRB.read_text(encoding="utf-8")
        self.assertIn("pub fn xhci_trb_link", text)
        self.assertIn("next_segment_physical & 0xFFFFFFFFFFFFFFF0", text)
        self.assertIn("if toggle_cycle", text)
        self.assertIn("XHCI_TRB_TOGGLE_CYCLE_BIT", text)

    def test_trb_constructors_have_no_submission_side_effects(self):
        code = code_without_comments(TRB).lower()
        for token in (
            "doorbell", "mmio_read", "mmio_write", "pci_write", "pci_enable",
            "dma_alloc(", "xhci_ring_push", "__out", "bus_master",
        ):
            self.assertNotIn(token, code, token)

    def test_address_configure_and_evaluate_encode_slot_id(self):
        text = TRB.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("(slot_id as u32) << XHCI_TRB_SLOT_ID_SHIFT"), 4)
        self.assertIn("if block_set_address_request", text)
        self.assertIn("if deconfigure", text)
        self.assertIn("pub fn xhci_trb_evaluate_context", text)


if __name__ == "__main__":
    unittest.main()
