#!/usr/bin/env python3
"""Guardrails do produtor stateful do EP0 Transfer Ring."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EP0 = ROOT / "kernel/src/drivers/xhci_ep0.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciEp0ProducerTests(unittest.TestCase):
    def test_ep0_is_linked_but_not_activated_by_boot(self):
        main = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_ep0::*;", main)
        self.assertNotIn("xhci_ep0_prepare_after_address();", main)
        self.assertNotIn("xhci_ep0_submit_control_td(", main)

    def test_ep0_prepares_only_after_address_device(self):
        text = EP0.read_text(encoding="utf-8")
        self.assertIn("xhci_address_is_ready()", text)
        self.assertIn("xhci_address_slot_id() != xhci_context_slot_id()", text)
        self.assertIn("XHCI_EP0_ENQUEUE_INDEX = 0", text)
        self.assertIn("XHCI_EP0_PRODUCER_CYCLE = true", text)

    def test_control_td_is_fully_published_before_doorbell(self):
        text = EP0.read_text(encoding="utf-8")
        fn = text[text.index("pub fn xhci_ep0_submit_control_td"):]
        setup = fn.index("xhci_ep0_write_one(setup)")
        data = fn.index("xhci_ep0_write_one(data)")
        status = fn.index("xhci_ep0_write_one(status)")
        barrier = fn.index("x86_read_cr3_raw()")
        doorbell = fn.index("xhci_ep0_ring_doorbell()")
        self.assertLess(setup, data)
        self.assertLess(data, status)
        self.assertLess(status, barrier)
        self.assertLess(barrier, doorbell)

    def test_link_trb_and_cycle_state_are_maintained(self):
        text = EP0.read_text(encoding="utf-8")
        self.assertIn("XHCI_RING_RESERVED_LINK_TRBS", text)
        self.assertIn("xhci_ep0_publish_link(cycle)", text)
        self.assertIn("XHCI_EP0_PRODUCER_CYCLE = !XHCI_EP0_PRODUCER_CYCLE", text)
        self.assertIn("xhci_trb_cycle_bits(cycle)", text)

    def test_doorbell_targets_default_control_endpoint(self):
        text = EP0.read_text(encoding="utf-8")
        self.assertIn("XHCI_EP0_ENDPOINT_ID: u32 = 1", text)
        self.assertIn("doorbell_base + ((slot_id as u64) * 4)", text)
        self.assertIn("x86_mmio_write32(doorbell, XHCI_EP0_ENDPOINT_ID", text)

    def test_ep0_does_not_create_second_event_consumer(self):
        text = EP0.read_text(encoding="utf-8")
        forbidden = [
            "XHCI_EVENT_DEQUEUE_INDEX",
            "XHCI_EVENT_CONSUMER_CYCLE",
            "xhci_command_wait_completion",
            "xhci_event_slot_virtual",
            "XHCI_INTR_ERDP",
        ]
        for token in forbidden:
            self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
