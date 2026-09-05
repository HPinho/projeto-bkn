#!/usr/bin/env python3
"""Guardrails do produtor stateful do Command Ring xHCI e consumidor compartilhado."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "kernel/src/drivers/xhci_command.sotlas"
CONSUMER = ROOT / "kernel/src/drivers/xhci_event_consumer.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciCommandTests(unittest.TestCase):
    def test_command_state_starts_after_noop_and_prepares_shared_consumer(self):
        text = COMMAND.read_text(encoding="utf-8")
        consumer = CONSUMER.read_text(encoding="utf-8")
        self.assertIn("XHCI_COMMAND_FIRST_FREE_INDEX: u32 = 1", text)
        self.assertIn("xhci_start_noop_completed()", text)
        self.assertIn("XHCI_COMMAND_ENQUEUE_INDEX = XHCI_COMMAND_FIRST_FREE_INDEX", text)
        self.assertIn("xhci_event_consumer_prepare_after_noop()", text)
        self.assertIn("XHCI_EVENT_CONSUMER_FIRST_INDEX: u32 = 1", consumer)

    def test_link_trb_is_reserved_and_republished_with_current_cycle(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertIn("XHCI_RUNTIME_COMMAND_TRBS - XHCI_RING_RESERVED_LINK_TRBS", text)
        self.assertIn("xhci_command_publish_link(cycle)", text)
        self.assertIn("xhci_trb_link(xhci_runtime_command_ring_physical(), true, cycle)", text)
        self.assertIn("XHCI_COMMAND_PRODUCER_CYCLE = !XHCI_COMMAND_PRODUCER_CYCLE", text)

    def test_submit_overrides_cycle_bit_and_advances_only_after_doorbell(self):
        text = COMMAND.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_command_submit(command: XhciTrb)", 1)[1]
        write = body.index("*slot = published")
        barrier = body.index("x86_read_cr3_raw()")
        doorbell = body.index("xhci_command_ring_doorbell0()")
        advance = body.index("xhci_command_advance_producer()")
        self.assertLess(write, barrier)
        self.assertLess(barrier, doorbell)
        self.assertLess(doorbell, advance)
        self.assertIn("published.control = (published.control & ~XHCI_TRB_CYCLE_BIT)", body)

    def test_completion_uses_shared_consumer_and_matches_command_pointer(self):
        text = COMMAND.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_command_wait_completion(command_physical: u64)", 1)[1]
        self.assertIn("xhci_event_consumer_peek()", body)
        self.assertIn("XHCI_TRB_TYPE_COMMAND_COMPLETION_EVENT", body)
        self.assertIn("xhci_event_success(event)", body)
        self.assertIn("xhci_command_completion_trb_pointer(event) != command_physical", body)
        self.assertIn("xhci_event_consumer_consume()", body)
        self.assertNotIn("XHCI_EVENT_DEQUEUE_INDEX", text)
        self.assertNotIn("xhci_command_update_erdp", text)

    def test_command_waiter_skips_only_port_status_change_events(self):
        text = COMMAND.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_command_wait_completion(command_physical: u64)", 1)[1]
        port = body.index("event_type == XHCI_TRB_TYPE_PORT_STATUS_CHANGE_EVENT")
        validate_port = body.index("xhci_port_status_change_port_id(event) == 0", port)
        consume = body.index("xhci_event_consumer_consume()", validate_port)
        continue_wait = body.index("continue;", consume)
        command = body.index("event_type != XHCI_TRB_TYPE_COMMAND_COMPLETION_EVENT", continue_wait)
        self.assertLess(port, validate_port)
        self.assertLess(validate_port, consume)
        self.assertLess(consume, continue_wait)
        self.assertLess(continue_wait, command)
        self.assertIn("return false;", body[command:])

    def test_slot_id_state_is_fail_closed_per_command(self):
        text = COMMAND.read_text(encoding="utf-8")
        submit = text.split("pub fn xhci_command_submit(command: XhciTrb)", 1)[1]
        submit = submit.split("pub fn xhci_command_wait_completion", 1)[0]
        wait = text.split("pub fn xhci_command_wait_completion(command_physical: u64)", 1)[1]
        self.assertIn("XHCI_COMMAND_LAST_SLOT_ID = 0", submit)
        self.assertIn("XHCI_COMMAND_LAST_SLOT_ID = xhci_event_slot_id(event)", wait)
        consume = wait.rindex("xhci_event_consumer_consume()")
        clear_after_consume_failure = wait.index("XHCI_COMMAND_LAST_SLOT_ID = 0", consume)
        self.assertGreater(clear_after_consume_failure, consume)

    def test_event_cursor_getters_delegate_to_shared_consumer(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertIn("return xhci_event_consumer_index();", text)
        self.assertIn("return xhci_event_consumer_cycle();", text)

    def test_command_module_is_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_command::*;", text)


if __name__ == "__main__":
    unittest.main()
