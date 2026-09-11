#!/usr/bin/env python3
"""Guardrails HID-4d.3b para teardown lógico da identidade HID."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = ROOT / "kernel/src/drivers/xhci_hid_descriptor.sotlas"
INPUT_DEVICE = ROOT / "kernel/src/drivers/input_device.sotlas"


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


def ordered_positions(body: str, *tokens: str) -> list[int]:
    positions: list[int] = []
    cursor = 0
    for token in tokens:
        position = body.find(token, cursor)
        if position < 0:
            raise AssertionError(f"missing ordered token: {token}")
        positions.append(position)
        cursor = position + len(token)
    return positions


class XhciHidIdentityTeardownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.descriptor = DESCRIPTOR.read_text(encoding="utf-8")
        cls.input_device = INPUT_DEVICE.read_text(encoding="utf-8")

    def test_current_generation_query_is_locked_and_survives_detached_record(self):
        body = function_body(self.input_device, "input_device_generation_for_id")
        self.assertIn("input_device_lock_irq()", body)
        self.assertIn("INPUT_DEVICES[slot].device_id == device_id", body)
        self.assertIn("generation = INPUT_DEVICES[slot].generation", body)
        self.assertIn("input_device_unlock_irq(flags)", body)
        self.assertNotIn("INPUT_DEVICES[slot].valid", body)

    def test_hotplug_gate_requires_exact_epoch_and_detach_pending(self):
        body = function_body(
            self.descriptor, "xhci_hid_descriptor_teardown_epoch_matches"
        )
        for token in (
            "epoch == 0",
            "xhci_device_table_slot_is_valid(slot_id)",
            "xhci_device_table_slot_epoch(slot_id) != epoch",
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING",
            "XHCI_HID_DESCRIPTOR_STATES[index].epoch == epoch",
        ):
            self.assertIn(token, body)

    def test_teardown_preserves_identity_until_event_queue_map_cleanup(self):
        body = function_body(
            self.descriptor, "xhci_hid_descriptor_teardown_input_device_for_epoch"
        )
        ordered_positions(
            body,
            "hid_input_events_unbind_device(device_id, generation)",
            "input_event_purge_device(device_id, generation)",
            "hid_input_device_map_unbind(device_id, generation)",
            "input_device_detach(device_id, generation)",
            "XHCI_HID_DESCRIPTOR_STATES[index].input_device_id = INPUT_DEVICE_ID_NONE",
            "XHCI_HID_DESCRIPTOR_STATES[index].input_device_generation = INPUT_DEVICE_GENERATION_INVALID",
        )

    def test_teardown_is_retry_safe_for_already_unbound_layers(self):
        body = function_body(
            self.descriptor, "xhci_hid_descriptor_teardown_input_device_for_epoch"
        )
        self.assertRegex(
            body,
            r"if\s+device_id\s*==\s*INPUT_DEVICE_ID_NONE\s*&&\s*"
            r"generation\s*==\s*INPUT_DEVICE_GENERATION_INVALID\s*\{\s*return\s+true",
        )
        self.assertRegex(
            body,
            r"if\s+hid_input_events_device_is_bound\(device_id, generation\)\s*\{"
            r"[\s\S]*?hid_input_events_unbind_device\(device_id, generation\)",
        )
        self.assertRegex(
            body,
            r"if\s+hid_input_device_map_is_ready\(device_id, generation\)\s*\{"
            r"[\s\S]*?hid_input_device_map_unbind\(device_id, generation\)",
        )
        self.assertGreaterEqual(
            body.count("xhci_hid_descriptor_teardown_epoch_matches(slot_id, epoch)"), 5
        )

    def test_new_generation_is_never_detached_by_old_teardown(self):
        body = function_body(
            self.descriptor, "xhci_hid_descriptor_teardown_input_device_for_epoch"
        )
        generation_read = body.find("let current_generation = input_device_generation_for_id(device_id)")
        generation_gate = body.find("if current_generation == generation", generation_read)
        detach = body.find("input_device_detach(device_id, generation)", generation_gate)
        post_read = body.find("let detached_generation = input_device_generation_for_id(device_id)", detach)
        self.assertGreaterEqual(generation_read, 0)
        self.assertGreater(generation_gate, generation_read)
        self.assertGreater(detach, generation_gate)
        self.assertGreater(post_read, detach)
        self.assertIn("detached_generation == generation", body)

    def test_descriptor_identity_clear_is_exact_and_idempotent(self):
        body = function_body(
            self.descriptor, "xhci_hid_descriptor_teardown_input_device_for_epoch"
        )
        clear = body.rfind(
            "XHCI_HID_DESCRIPTOR_STATES[index].input_device_id = INPUT_DEVICE_ID_NONE"
        )
        self.assertGreater(clear, body.find("input_device_detach(device_id, generation)"))
        prefix = body[:clear]
        self.assertIn("XHCI_HID_DESCRIPTOR_STATES[index].epoch != epoch", prefix)
        self.assertIn("XHCI_HID_DESCRIPTOR_STATES[index].input_device_id != device_id", prefix)
        self.assertIn("XHCI_HID_DESCRIPTOR_STATES[index].input_device_generation != generation", prefix)
        self.assertIn(
            "XHCI_HID_DESCRIPTOR_STATES[index].input_device_id == INPUT_DEVICE_ID_NONE",
            prefix,
        )

    def test_identity_microcut_does_not_release_physical_resources(self):
        body = function_body(
            self.descriptor, "xhci_hid_descriptor_teardown_input_device_for_epoch"
        )
        for forbidden in (
            "dma_release",
            "dma_unshare_from_device",
            "xhci_hid_context_release",
            "xhci_trb_disable_slot",
            "drop_endpoint",
        ):
            self.assertNotIn(forbidden, body)

    def test_enumeration_reset_keeps_legacy_rollback_separate(self):
        reset = function_body(self.descriptor, "xhci_hid_descriptor_reset_for_slot")
        legacy = function_body(
            self.descriptor, "xhci_hid_descriptor_release_input_device_for_slot"
        )
        self.assertIn("xhci_hid_descriptor_release_input_device_for_slot(slot_id)", reset)
        self.assertNotIn("xhci_hid_descriptor_teardown_input_device_for_epoch", reset)
        self.assertIn("input_device_detach(device_id, generation)", legacy)


if __name__ == "__main__":
    unittest.main()
