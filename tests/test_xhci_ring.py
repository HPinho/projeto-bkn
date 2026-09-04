#!/usr/bin/env python3
"""Guardrails do contrato de rings xHCI sobre DMA."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RING = ROOT / "kernel/src/drivers/xhci_ring.sotlas"


class XhciRingTests(unittest.TestCase):
    def test_trb_layout_contract_is_16_bytes_by_fields(self):
        text = RING.read_text(encoding="utf-8")
        self.assertIn("pub const XHCI_TRB_SIZE: u64 = 16", text)
        self.assertIn("pub struct XhciTrb", text)
        self.assertIn("parameter: u64", text)
        self.assertIn("status: u32", text)
        self.assertIn("control: u32", text)

    def test_ring_requires_real_dma_buffer(self):
        text = RING.read_text(encoding="utf-8")
        self.assertIn("if !buffer.valid", text)
        self.assertIn("buffer.virtual_address == (null as *mut u8)", text)
        self.assertIn("buffer.physical_address == 0", text)
        self.assertIn("buffer.size < required", text)
        self.assertIn("buffer.physical_address & (XHCI_RING_ALIGNMENT - 1)", text)

    def test_ring_contract_has_no_mmio_or_doorbell_side_effects(self):
        text = RING.read_text(encoding="utf-8").lower()
        for token in (
            "mmio_read", "mmio_write", "doorbell", "pci_write",
            "pci_enable", "bus_master", "__out", "dma_alloc(",
        ):
            self.assertNotIn(token, text, token)

    def test_ring_state_starts_at_cycle_one(self):
        text = RING.read_text(encoding="utf-8")
        self.assertIn("cycle_state: true", text)
        self.assertIn("enqueue_index: 0", text)


if __name__ == "__main__":
    unittest.main()
