#!/usr/bin/env python3
"""Guardrails HID-4c.4e do demux de Transfer Events por Slot ID + epoch."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRANSFER = ROOT / "kernel/src/drivers/xhci_transfer.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciTransferTests(unittest.TestCase):
    def test_waiter_uses_shared_event_consumer_only(self):
        text = TRANSFER.read_text(encoding="utf-8")
        self.assertIn("xhci_event_consumer_peek()", text)
        self.assertIn("xhci_event_consumer_consume()", text)
        self.assertNotIn("XHCI_EVENT_CONSUMER_INDEX", text)
        self.assertNotIn("XHCI_EVENT_CONSUMER_CYCLE", text)
        self.assertNotIn("XHCI_INTR_ERDP", text)

    def test_result_and_pending_state_are_partitioned_by_slot_and_epoch(self):
        text = TRANSFER.read_text(encoding="utf-8")
        self.assertIn("XHCI_TRANSFER_SLOT_CAPACITY: usize = XHCI_DEVICE_SLOT_CAPACITY", text)
        self.assertIn("static mut XHCI_TRANSFER_RESULTS: [XhciTransferResult;", text)
        self.assertIn("static mut XHCI_TRANSFER_PENDING_EVENTS: [XhciTransferPendingEvent;", text)
        self.assertIn("xhci_device_table_slot_epoch(slot_id)", text)
        self.assertIn("pub fn xhci_transfer_pending_is_ready_for(slot_id: u8)", text)
        self.assertIn("pub fn xhci_transfer_pending_matches(slot_id: u8", text)
        self.assertIn("pub fn xhci_transfer_last_residual_length_for(slot_id: u8)", text)
        self.assertIn("pub fn xhci_transfer_last_completion_code_for(slot_id: u8)", text)
        self.assertNotIn("static mut XHCI_TRANSFER_LAST_RESIDUAL_LENGTH:", text)
        self.assertNotIn("static mut XHCI_TRANSFER_LAST_COMPLETION_CODE:", text)

    def test_router_attributes_event_from_event_trb_before_consuming(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = text.split("fn xhci_transfer_publish_pending_event", 1)[1].split(
            "fn xhci_transfer_take_pending", 1
        )[0]
        for token in (
            "xhci_event_type(event) != XHCI_TRB_TYPE_TRANSFER_EVENT",
            "xhci_event_slot_id(event)",
            "xhci_transfer_event_endpoint_id(event)",
            "xhci_transfer_event_trb_pointer(event)",
            "xhci_device_table_slot_epoch(slot_id)",
            "XHCI_TRANSFER_PENDING_EVENTS[index].epoch = epoch",
            "XHCI_TRANSFER_PENDING_EVENTS[index].endpoint_id = endpoint_id",
            "XHCI_TRANSFER_PENDING_EVENTS[index].trb_pointer = trb_pointer",
            "xhci_event_consumer_consume()",
        ):
            self.assertIn(token, body)
        publish = body.index("XHCI_TRANSFER_PENDING_EVENTS[index].trb_pointer = trb_pointer")
        consume = body.index("xhci_event_consumer_consume()")
        self.assertLess(publish, consume)

    def test_waiter_routes_other_slots_instead_of_failing_on_them(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_transfer_wait_completion", 1)[1].split(
            "pub fn xhci_transfer_wait_ep0_completion", 1
        )[0]
        self.assertIn("let event_slot = xhci_event_slot_id(event)", body)
        self.assertIn("if event_slot == slot_id &&", body)
        self.assertIn("xhci_transfer_publish_pending_event(event)", body)
        self.assertIn("if event_slot == slot_id", body)
        self.assertNotIn("if xhci_event_slot_id(event) != slot_id { return false; }", body)
        self.assertIn("xhci_transfer_take_pending(", body)

    def test_same_slot_wrong_endpoint_or_pointer_still_fails_closed(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_transfer_wait_completion", 1)[1].split(
            "pub fn xhci_transfer_wait_ep0_completion", 1
        )[0]
        self.assertIn("event_endpoint != endpoint_id", body)
        self.assertIn("event_pointer != completion_trb_physical", body)
        same_slot = body.index("if event_slot == slot_id &&")
        route = body.index("xhci_transfer_publish_pending_event(event)")
        self.assertLess(same_slot, route)

    def test_explicit_route_next_event_is_bounded_and_host_error_aware(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_transfer_route_next_event()", 1)[1].split(
            "pub fn xhci_transfer_wait_completion", 1
        )[0]
        self.assertIn("XHCI_TRANSFER_POLL_LIMIT", body)
        self.assertIn("XHCI_USBSTS_HOST_CONTROLLER_ERROR", body)
        self.assertIn("xhci_transfer_publish_pending_event(event)", body)
        self.assertIn("pub fn xhci_transfer_routed_event_count() -> u64", text)

    def test_pending_mailbox_is_single_entry_per_slot_and_epoch_safe(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = text.split("fn xhci_transfer_publish_pending_event", 1)[1].split(
            "fn xhci_transfer_take_pending", 1
        )[0]
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].valid &&", body)
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].epoch == epoch", body)
        self.assertIn("return false;", body)
        ready = text.split("pub fn xhci_transfer_pending_is_ready_for", 1)[1].split(
            "pub fn xhci_transfer_pending_matches", 1
        )[0]
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].epoch != epoch", ready)
        self.assertIn("xhci_transfer_clear_pending_index(index)", ready)

    def test_ep0_wrapper_still_uses_endpoint_id_one(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_transfer_wait_ep0_completion", 1)[1]
        self.assertIn("xhci_transfer_wait_completion", body)
        self.assertIn("XHCI_TRANSFER_EP0_ENDPOINT_ID", body)

    def test_legacy_result_wrappers_use_active_slot(self):
        text = TRANSFER.read_text(encoding="utf-8")
        self.assertIn("xhci_transfer_last_residual_length_for(xhci_transfer_active_slot_id())", text)
        self.assertIn("xhci_transfer_last_completion_code_for(xhci_transfer_active_slot_id())", text)

    def test_main_registers_shared_consumer_and_transfer_waiter(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_event_consumer::*;", text)
        self.assertIn("import kernel::drivers::xhci_transfer::*;", text)
        self.assertLess(
            text.index("import kernel::drivers::xhci_event_consumer::*;"),
            text.index("import kernel::drivers::xhci_transfer::*;"),
        )


if __name__ == "__main__":
    unittest.main()
