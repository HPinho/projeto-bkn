#!/usr/bin/env python3
"""Guardrails do waiter compartilhado de Transfer Event xHCI."""

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

    def test_generic_waiter_validates_endpoint_before_consuming(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_transfer_wait_completion", 1)[1].split(
            "pub fn xhci_transfer_wait_ep0_completion", 1
        )[0]
        consume = body.index("xhci_event_consumer_consume()")
        for token in (
            "XHCI_TRB_TYPE_TRANSFER_EVENT",
            "xhci_event_slot_id(event) != slot_id",
            "xhci_transfer_event_endpoint_id(event) != endpoint_id",
            "xhci_transfer_event_trb_pointer(event) != completion_trb_physical",
            "xhci_event_success(event)",
        ):
            self.assertLess(body.index(token), consume)

    def test_ep0_wrapper_uses_endpoint_id_one(self):
        text = TRANSFER.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_transfer_wait_ep0_completion", 1)[1]
        self.assertIn("xhci_transfer_wait_completion", body)
        self.assertIn("XHCI_TRANSFER_EP0_ENDPOINT_ID", body)

    def test_waiter_rejects_event_data_and_host_controller_error(self):
        text = TRANSFER.read_text(encoding="utf-8")
        self.assertIn("xhci_transfer_event_has_event_data(event)", text)
        self.assertIn("XHCI_USBSTS_HOST_CONTROLLER_ERROR", text)

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
