#!/usr/bin/env python3
"""Guardrails do produtor/consumer stateful do Command/Event Ring xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "kernel/src/drivers/xhci_command.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciCommandTests(unittest.TestCase):
    def test_command_state_starts_after_noop_slots(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertIn("XHCI_COMMAND_FIRST_FREE_INDEX: u32 = 1", text)
        self.assertIn("XHCI_EVENT_FIRST_FREE_INDEX: u32 = 1", text)
        self.assertIn("xhci_start_noop_completed()", text)
        self.assertIn("XHCI_COMMAND_ENQUEUE_INDEX = XHCI_COMMAND_FIRST_FREE_INDEX", text)
        self.assertIn("XHCI_EVENT_DEQUEUE_INDEX = XHCI_EVENT_FIRST_FREE_INDEX", text)

    def test_link_trb_is_reserved_and_republished_with_current_cycle(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertIn("XHCI_RUNTIME_COMMAND_TRBS - XHCI_RING_RESERVED_LINK_TRBS", text)
        self.assertIn("xhci_command_publish_link(cycle)", text)
        self.assertIn("xhci_trb_link(xhci_runtime_command_ring_physical(), true, cycle)", text)
        self.assertIn("XHCI_COMMAND_PRODUCER_CYCLE = !XHCI_COMMAND_PRODUCER_CYCLE", text)

    def test_submit_overrides_cycle_bit_and_rings_doorbell_after_publish(self):
        text = COMMAND.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_command_submit(command: XhciTrb)", 1)[1]
        write = body.index("*slot = published")
        barrier = body.index("x86_read_cr3_raw()")
        advance = body.index("xhci_command_advance_producer()")
        doorbell = body.index("xhci_command_ring_doorbell0()")
        self.assertLess(write, barrier)
        self.assertLess(barrier, advance)
        self.assertLess(advance, doorbell)
        self.assertIn("published.control = (published.control & ~XHCI_TRB_CYCLE_BIT)", body)

    def test_completion_matches_pointer_and_advances_erdp(self):
        text = COMMAND.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_command_wait_completion(command_physical: u64)", 1)[1]
        self.assertIn("xhci_event_cycle(event) == XHCI_EVENT_CONSUMER_CYCLE", body)
        self.assertIn("XHCI_TRB_TYPE_COMMAND_COMPLETION_EVENT", body)
        self.assertIn("xhci_event_success(event)", body)
        self.assertIn("xhci_command_completion_trb_pointer(event) != command_physical", body)
        self.assertIn("xhci_command_advance_event()", body)
        self.assertIn("xhci_command_update_erdp()", body)
        self.assertIn("XHCI_EVENT_CONSUMER_CYCLE = !XHCI_EVENT_CONSUMER_CYCLE", text)

    def test_command_module_is_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_command::*;", text)


if __name__ == "__main__":
    unittest.main()
