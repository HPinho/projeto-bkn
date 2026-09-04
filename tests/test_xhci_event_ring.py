#!/usr/bin/env python3
"""Guardrails do estado lógico consumidor do Event Ring xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVENT_RING = ROOT / "kernel/src/drivers/xhci_event_ring.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def code_without_comments(path: Path) -> str:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        lines.append(line.split("//", 1)[0])
    return "\n".join(lines).lower()


class XhciEventRingTests(unittest.TestCase):
    def test_event_ring_starts_at_consumer_cycle_one(self):
        text = EVENT_RING.read_text(encoding="utf-8")
        self.assertIn("dequeue_index: 0", text)
        self.assertIn("consumer_cycle_state: true", text)

    def test_event_ring_uses_full_segment_without_link_trb_reservation(self):
        text = EVENT_RING.read_text(encoding="utf-8")
        self.assertIn("dequeue_index < (*state).trb_count", text)
        self.assertIn("(*state).dequeue_index >= (*state).trb_count", text)
        self.assertNotIn("RESERVED_LINK", text)

    def test_wrap_resets_dequeue_and_toggles_consumer_cycle(self):
        text = EVENT_RING.read_text(encoding="utf-8")
        self.assertIn("pub fn xhci_event_ring_advance", text)
        self.assertIn("(*state).dequeue_index += 1", text)
        self.assertIn("(*state).dequeue_index = 0", text)
        self.assertIn("(*state).consumer_cycle_state = !(*state).consumer_cycle_state", text)

    def test_event_ring_is_initialized_from_valid_erst_entry(self):
        text = EVENT_RING.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_erst::*;", text)
        self.assertIn("if !xhci_erst_entry_valid(entry)", text)
        self.assertIn("trb_count: (*entry).ring_segment_size", text)

    def test_event_ring_has_no_hardware_side_effects(self):
        code = code_without_comments(EVENT_RING)
        for token in (
            "mmio_read", "mmio_write", "erdp", "erstba", "erstsz",
            "doorbell", "pci_write", "pci_enable", "bus_master",
            "__out", "dma_alloc(", "interrupt", "msi", "msix",
            "virtual_base[", "xhci_trb_decode",
        ):
            self.assertNotIn(token, code, token)

    def test_main_only_links_event_ring_contract(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_event_ring::*;", text)
        self.assertNotIn("xhci_event_ring_init(", text)
        self.assertNotIn("xhci_event_ring_advance(", text)


if __name__ == "__main__":
    unittest.main()
