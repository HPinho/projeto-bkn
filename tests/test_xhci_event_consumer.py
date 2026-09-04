#!/usr/bin/env python3
"""Guardrails do consumidor único do Event Ring xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONSUMER = ROOT / "kernel/src/drivers/xhci_event_consumer.sotlas"
COMMAND = ROOT / "kernel/src/drivers/xhci_command.sotlas"
EP0 = ROOT / "kernel/src/drivers/xhci_ep0.sotlas"


class XhciEventConsumerTests(unittest.TestCase):
    def test_consumer_starts_after_initial_noop_event(self):
        text = CONSUMER.read_text(encoding="utf-8")
        self.assertIn("XHCI_EVENT_CONSUMER_FIRST_INDEX: u32 = 1", text)
        self.assertIn("xhci_start_noop_completed()", text)
        self.assertIn("XHCI_EVENT_CONSUMER_CYCLE = true", text)

    def test_only_consumer_advances_erdp_after_noop(self):
        consumer = CONSUMER.read_text(encoding="utf-8")
        command = COMMAND.read_text(encoding="utf-8")
        ep0 = EP0.read_text(encoding="utf-8")
        self.assertIn("XHCI_INTR_ERDP", consumer)
        self.assertNotIn("XHCI_INTR_ERDP", command)
        self.assertNotIn("XHCI_INTR_ERDP", ep0)

    def test_command_uses_shared_consumer(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_event_consumer::*;", text)
        self.assertIn("xhci_event_consumer_prepare_after_noop()", text)
        self.assertIn("xhci_event_consumer_peek()", text)
        self.assertIn("xhci_event_consumer_consume()", text)
        self.assertNotIn("static mut XHCI_EVENT_DEQUEUE_INDEX", text)
        self.assertNotIn("static mut XHCI_EVENT_CONSUMER_CYCLE", text)

    def test_peek_does_not_advance_before_validation(self):
        text = CONSUMER.read_text(encoding="utf-8")
        peek = text.split("pub fn xhci_event_consumer_peek", 1)[1].split(
            "pub fn xhci_event_consumer_consume", 1
        )[0]
        self.assertNotIn("XHCI_EVENT_CONSUMER_INDEX += 1", peek)
        self.assertNotIn("xhci_event_consumer_update_erdp", peek)

    def test_consume_advances_cycle_and_erdp(self):
        text = CONSUMER.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_event_consumer_consume", 1)[1]
        self.assertIn("XHCI_EVENT_CONSUMER_INDEX += 1", body)
        self.assertIn("XHCI_EVENT_CONSUMER_CYCLE = !XHCI_EVENT_CONSUMER_CYCLE", body)
        self.assertIn("xhci_event_consumer_update_erdp()", body)


if __name__ == "__main__":
    unittest.main()
