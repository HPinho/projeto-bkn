#!/usr/bin/env python3
"""Guardrails do decodificador puro de Event TRBs xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "kernel/src/drivers/xhci_event.sotlas"


def code_without_comments(path: Path) -> str:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        lines.append(raw.split("//", 1)[0])
    return "\n".join(lines)


class XhciEventTests(unittest.TestCase):
    def test_event_type_and_completion_constants(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("XHCI_TRB_TYPE_TRANSFER_EVENT: u32 = 32", text)
        self.assertIn("XHCI_TRB_TYPE_COMMAND_COMPLETION_EVENT: u32 = 33", text)
        self.assertIn("XHCI_COMPLETION_CODE_SUCCESS: u8 = 1", text)
        self.assertIn("XHCI_EVENT_COMPLETION_CODE_SHIFT: u32 = 24", text)

    def test_transfer_event_decodes_endpoint_slot_and_residual_length(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("XHCI_EVENT_ENDPOINT_ID_SHIFT: u32 = 16", text)
        self.assertIn("XHCI_EVENT_SLOT_ID_SHIFT: u32 = 24", text)
        self.assertIn("XHCI_EVENT_TRANSFER_LENGTH_MASK: u32 = 0x00FFFFFF", text)
        self.assertIn("pub fn xhci_transfer_event_endpoint_id", text)
        self.assertIn("pub fn xhci_transfer_event_residual_length", text)

    def test_event_data_is_not_treated_as_trb_pointer(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("XHCI_EVENT_ED_BIT: u32 = 1 << 2", text)
        self.assertIn("if xhci_transfer_event_has_event_data(trb) { return 0; }", text)
        self.assertIn("return (*trb).parameter & 0xFFFFFFFFFFFFFFF0", text)
        self.assertIn("pub fn xhci_transfer_event_data", text)

    def test_command_completion_decodes_original_command_pointer(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("pub fn xhci_command_completion_trb_pointer", text)
        self.assertIn("XHCI_EVENT_COMMAND_PARAMETER_MASK: u32 = 0x00FFFFFF", text)
        self.assertIn("pub fn xhci_command_completion_parameter", text)

    def test_decoder_has_no_event_ring_or_hardware_side_effects(self):
        code = code_without_comments(EVENT).lower()
        for token in (
            "mmio_read", "mmio_write", "doorbell", "erst", "dequeue",
            "pci_write", "pci_enable", "__out", "dma_alloc(", "interrupt_enable",
        ):
            self.assertNotIn(token, code, token)


if __name__ == "__main__":
    unittest.main()
