#!/usr/bin/env python3
"""Guardrails HID-4c.3 do produtor EP0 por Slot ID + epoch."""

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

    def test_ep0_state_is_partitioned_by_slot_and_epoch(self):
        text = EP0.read_text(encoding="utf-8")
        self.assertIn("XHCI_EP0_SLOT_CAPACITY: usize = XHCI_DEVICE_SLOT_CAPACITY", text)
        self.assertIn("static mut XHCI_EP0_STATES: [XhciEp0State;", text)
        self.assertIn("pub fn xhci_ep0_prepare_for_slot(slot_id: u8)", text)
        self.assertIn("xhci_device_table_slot_epoch(slot_id)", text)
        self.assertIn("xhci_address_is_ready_for(slot_id)", text)
        self.assertIn("xhci_context_is_ready_for(slot_id)", text)
        self.assertIn("xhci_context_ep0_ring_physical_for(slot_id)", text)
        self.assertNotIn("static mut XHCI_EP0_ENQUEUE_INDEX:", text)
        self.assertNotIn("static mut XHCI_EP0_PRODUCER_CYCLE:", text)
        self.assertNotIn("static mut XHCI_EP0_LAST_STATUS_TRB_PHYSICAL:", text)

    def test_control_td_is_fully_published_before_slot_doorbell(self):
        text = EP0.read_text(encoding="utf-8")
        fn = text[text.index("pub fn xhci_ep0_submit_control_td_for_slot"):]
        setup = fn.index("xhci_ep0_write_one_for(slot_id, setup)")
        data = fn.index("xhci_ep0_write_one_for(slot_id, data)")
        status = fn.index("xhci_ep0_write_one_for(slot_id, status)")
        barrier = fn.index("x86_read_cr3_raw()")
        doorbell = fn.index("xhci_ep0_ring_doorbell_for(slot_id)")
        self.assertLess(setup, data)
        self.assertLess(data, status)
        self.assertLess(status, barrier)
        self.assertLess(barrier, doorbell)

    def test_link_trb_and_cycle_state_are_per_slot(self):
        text = EP0.read_text(encoding="utf-8")
        self.assertIn("XHCI_RING_RESERVED_LINK_TRBS", text)
        self.assertIn("xhci_ep0_publish_link_for(slot_id, cycle)", text)
        self.assertIn("XHCI_EP0_STATES[state_index].producer_cycle =", text)
        self.assertIn("!XHCI_EP0_STATES[state_index].producer_cycle", text)
        self.assertIn("xhci_trb_cycle_bits(cycle)", text)

    def test_doorbell_targets_explicit_slot_default_control_endpoint(self):
        text = EP0.read_text(encoding="utf-8")
        body = text.split("fn xhci_ep0_ring_doorbell_for(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_ep0_prepare_for_slot", 1)[0]
        self.assertIn("XHCI_EP0_ENDPOINT_ID: u32 = 1", text)
        self.assertIn("doorbell_base + ((slot_id as u64) * 4)", body)
        self.assertIn("x86_mmio_write32(doorbell, XHCI_EP0_ENDPOINT_ID", body)

    def test_legacy_wrappers_delegate_to_active_slot(self):
        text = EP0.read_text(encoding="utf-8")
        self.assertIn("return xhci_ep0_prepare_for_slot(slot_id)", text)
        self.assertIn("xhci_ep0_submit_control_td_for_slot(", text)
        self.assertIn("xhci_ep0_producer_cycle_for(xhci_ep0_active_slot_id())", text)
        self.assertIn("xhci_ep0_last_status_trb_physical_for(xhci_ep0_active_slot_id())", text)

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
