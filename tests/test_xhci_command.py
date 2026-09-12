#!/usr/bin/env python3
"""Guardrails do produtor stateful do Command Ring xHCI e consumidor compartilhado."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "kernel/src/drivers/xhci_command.sotlas"
CONSUMER = ROOT / "kernel/src/drivers/xhci_event_consumer.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", match.end())
    if brace < 0:
        raise AssertionError(f"missing function body {name}")
    depth = 0
    index = brace
    in_string = False
    escaped = False
    line_comment = False
    block_comment = False
    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 2
                continue
            index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
        index += 1
    raise AssertionError(f"unterminated function {name}")


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
        body = function_body(text, "xhci_command_submit")
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
        body = function_body(text, "xhci_command_wait_completion")
        self.assertIn("xhci_event_consumer_peek()", body)
        self.assertIn("XHCI_TRB_TYPE_COMMAND_COMPLETION_EVENT", body)
        self.assertIn("xhci_event_success(event)", body)
        self.assertIn("xhci_command_completion_trb_pointer(event) != command_physical", body)
        self.assertIn("xhci_event_consumer_consume()", body)
        self.assertNotIn("XHCI_EVENT_DEQUEUE_INDEX", text)
        self.assertNotIn("xhci_command_update_erdp", text)

    def test_command_waiter_routes_known_async_events_before_command_completion(self):
        text = COMMAND.read_text(encoding="utf-8")
        body = function_body(text, "xhci_command_wait_completion")
        port = body.index("event_type == XHCI_TRB_TYPE_PORT_STATUS_CHANGE_EVENT")
        validate_port = body.index("xhci_port_status_change_port_id(event) == 0", port)
        consume = body.index("xhci_event_consumer_consume()", validate_port)
        port_continue = body.index("continue;", consume)
        transfer = body.index("event_type == XHCI_TRB_TYPE_TRANSFER_EVENT", port_continue)
        route = body.index("xhci_transfer_route_next_event()", transfer)
        transfer_continue = body.index("continue;", route)
        command = body.index("event_type != XHCI_TRB_TYPE_COMMAND_COMPLETION_EVENT", transfer_continue)
        self.assertLess(port, validate_port)
        self.assertLess(validate_port, consume)
        self.assertLess(consume, port_continue)
        self.assertLess(port_continue, transfer)
        self.assertLess(transfer, route)
        self.assertLess(route, transfer_continue)
        self.assertLess(transfer_continue, command)
        self.assertIn("return false;", body[command:])

    def test_transfer_events_are_delegated_to_per_slot_demux(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_transfer::*;", text)
        body = function_body(text, "xhci_command_wait_completion")
        transfer = body.split("if event_type == XHCI_TRB_TYPE_TRANSFER_EVENT", 1)[1]
        transfer = transfer.split("if event_type != XHCI_TRB_TYPE_COMMAND_COMPLETION_EVENT", 1)[0]
        self.assertIn("xhci_transfer_route_next_event()", transfer)
        self.assertNotIn("xhci_event_consumer_consume()", transfer)

    def test_slot_id_state_is_fail_closed_per_command(self):
        text = COMMAND.read_text(encoding="utf-8")
        submit = function_body(text, "xhci_command_submit")
        wait = function_body(text, "xhci_command_wait_completion")
        self.assertIn("XHCI_COMMAND_LAST_SLOT_ID = 0", submit)
        self.assertIn("XHCI_COMMAND_LAST_SLOT_ID = xhci_event_slot_id(event)", wait)
        consume = wait.rindex("xhci_event_consumer_consume()")
        clear_after_consume_failure = wait.index("XHCI_COMMAND_LAST_SLOT_ID = 0", consume)
        self.assertGreater(clear_after_consume_failure, consume)

    def test_raw_submit_and_wait_are_private_to_transaction_layer(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^fn\s+xhci_command_submit\s*\(")
        self.assertRegex(text, r"(?m)^fn\s+xhci_command_wait_completion\s*\(")
        self.assertIn("pub fn xhci_command_execute_capture_slot(command: XhciTrb)", text)
        self.assertIn("pub fn xhci_command_execute(command: XhciTrb, expected_slot_id: u8)", text)

    def test_event_cursor_getters_delegate_to_shared_consumer(self):
        text = COMMAND.read_text(encoding="utf-8")
        self.assertIn("return xhci_event_consumer_index();", text)
        self.assertIn("return xhci_event_consumer_cycle();", text)

    def test_command_module_is_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_command::*;", text)


if __name__ == "__main__":
    unittest.main()
