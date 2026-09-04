#!/usr/bin/env python3
"""Guardrails para Setup/Data/Status/Normal TRBs usados no EP0 xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRB = ROOT / "kernel/src/drivers/xhci_trb.sotlas"


class XhciTransferTrbTests(unittest.TestCase):
    def test_transfer_trb_types_are_present(self):
        text = TRB.read_text(encoding="utf-8")
        self.assertIn("XHCI_TRB_TYPE_NORMAL: u32 = 1", text)
        self.assertIn("XHCI_TRB_TYPE_SETUP_STAGE: u32 = 2", text)
        self.assertIn("XHCI_TRB_TYPE_DATA_STAGE: u32 = 3", text)
        self.assertIn("XHCI_TRB_TYPE_STATUS_STAGE: u32 = 4", text)

    def test_setup_stage_is_immediate_eight_byte_setup_packet(self):
        text = TRB.read_text(encoding="utf-8")
        self.assertIn("fn xhci_setup_packet_parameter", text)
        self.assertIn("XHCI_TRB_IDT_BIT", text)
        self.assertIn("status: 8", text)
        self.assertIn("XHCI_SETUP_TRT_IN_DATA", text)
        self.assertIn("XHCI_SETUP_TRT_OUT_DATA", text)

    def test_data_and_status_support_direction_and_ioc(self):
        text = TRB.read_text(encoding="utf-8")
        self.assertIn("pub fn xhci_trb_data_stage", text)
        self.assertIn("pub fn xhci_trb_status_stage", text)
        self.assertIn("XHCI_TRB_DIR_IN_BIT", text)
        self.assertIn("XHCI_TRB_IOC_BIT", text)
        self.assertIn("XHCI_TRB_TRANSFER_LENGTH_MASK", text)
        self.assertIn("XHCI_TRB_TD_SIZE_SHIFT", text)

    def test_trb_builder_layer_has_no_hardware_side_effects(self):
        text = TRB.read_text(encoding="utf-8")
        forbidden = [
            "x86_mmio_write32(", "pci_enable_command_bits(",
            "doorbell", "dma_alloc(", "xhci_command_submit(",
        ]
        lowered = "\n".join(
            line for line in text.splitlines()
            if not line.strip().startswith("//")
        ).lower()
        for token in forbidden:
            self.assertNotIn(token.lower(), lowered)


if __name__ == "__main__":
    unittest.main()
