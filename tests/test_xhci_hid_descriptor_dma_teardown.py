#!/usr/bin/env python3
"""Guardrails HID-4d.3b para lifetime do Report Descriptor DMA."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = ROOT / "kernel/src/drivers/xhci_hid_descriptor.sotlas"


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


class XhciHidDescriptorDmaTeardownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = DESCRIPTOR.read_text(encoding="utf-8")
        cls.body = function_body(
            cls.source, "xhci_hid_descriptor_teardown_dma_for_epoch"
        )

    def test_requires_exact_hotplug_epoch_and_identity_already_gone(self):
        self.assertIn(
            "xhci_hid_descriptor_teardown_epoch_matches(slot_id, epoch)", self.body
        )
        self.assertIn(
            "XHCI_HID_DESCRIPTOR_STATES[index].input_device_id != INPUT_DEVICE_ID_NONE",
            self.body,
        )
        self.assertIn(
            "XHCI_HID_DESCRIPTOR_STATES[index].input_device_generation != INPUT_DEVICE_GENERATION_INVALID",
            self.body,
        )

    def test_shared_buffer_is_unshared_before_release(self):
        ordered_positions(
            self.body,
            "dma_buffer_shared(&XHCI_HID_DESCRIPTOR_STATES[index].buffer)",
            "dma_unshare_from_device(&mut XHCI_HID_DESCRIPTOR_STATES[index].buffer)",
            "dma_buffer_cpu_owned(&XHCI_HID_DESCRIPTOR_STATES[index].buffer)",
            "dma_release(&mut XHCI_HID_DESCRIPTOR_STATES[index].buffer)",
        )

    def test_cpu_owned_retry_path_is_explicit(self):
        self.assertIn(
            "cpu_owned = dma_buffer_cpu_owned(&XHCI_HID_DESCRIPTOR_STATES[index].buffer)",
            self.body,
        )
        self.assertIn("if !shared && !cpu_owned { return false; }", self.body)
        self.assertRegex(
            self.body,
            r"if\s+shared\s*\{[\s\S]*?dma_unshare_from_device",
        )

    def test_invalid_buffer_is_idempotent_and_skips_dma_release_block(self):
        valid_gate = self.body.find("if buffer_valid {")
        release = self.body.find("dma_release(", valid_gate)
        final_ready = self.body.find(
            "XHCI_HID_DESCRIPTOR_STATES[index].ready = false", valid_gate
        )
        self.assertGreaterEqual(valid_gate, 0)
        self.assertGreater(release, valid_gate)
        self.assertGreater(final_ready, release)
        self.assertIn(
            "XHCI_HID_DESCRIPTOR_STATES[index].buffer = dma_invalid_buffer()",
            self.body[final_ready:],
        )

    def test_epoch_is_revalidated_around_ownership_and_release(self):
        self.assertGreaterEqual(
            self.body.count(
                "xhci_hid_descriptor_teardown_epoch_matches(slot_id, epoch)"
            ),
            4,
        )
        unshare = self.body.find("dma_unshare_from_device")
        release = self.body.find("dma_release(")
        between = self.body.find(
            "xhci_hid_descriptor_teardown_epoch_matches(slot_id, epoch)", unshare
        )
        after = self.body.find(
            "xhci_hid_descriptor_teardown_epoch_matches(slot_id, epoch)", release
        )
        self.assertGreater(between, unshare)
        self.assertLess(between, release)
        self.assertGreater(after, release)

    def test_descriptor_logical_state_is_invalidated_only_after_release(self):
        release = self.body.find("dma_release(")
        ready = self.body.rfind("XHCI_HID_DESCRIPTOR_STATES[index].ready = false")
        buffer_reset = self.body.rfind(
            "XHCI_HID_DESCRIPTOR_STATES[index].buffer = dma_invalid_buffer()"
        )
        info_reset = self.body.rfind(
            "XHCI_HID_DESCRIPTOR_STATES[index].info = hid_report_descriptor_invalid()"
        )
        self.assertGreater(ready, release)
        self.assertGreater(buffer_reset, ready)
        self.assertGreater(info_reset, buffer_reset)
        self.assertNotIn("XHCI_HID_DESCRIPTOR_STATES[index].epoch =", self.body)

    def test_descriptor_dma_cut_does_not_touch_report_ring_or_slot_resources(self):
        for forbidden in (
            "xhci_hid_report",
            "xhci_hid_context",
            "xhci_configure_endpoint",
            "xhci_transfer_",
            "drop_endpoint",
            "disable_slot",
            "pmm_free",
        ):
            self.assertNotIn(forbidden, self.body)

    def test_enumeration_reset_does_not_call_hotplug_dma_teardown(self):
        reset = function_body(self.source, "xhci_hid_descriptor_reset_for_slot")
        self.assertNotIn("xhci_hid_descriptor_teardown_dma_for_epoch", reset)
        self.assertIn("xhci_hid_descriptor_release_input_device_for_slot(slot_id)", reset)


if __name__ == "__main__":
    unittest.main()
