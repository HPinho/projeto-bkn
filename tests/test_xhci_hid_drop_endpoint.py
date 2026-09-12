#!/usr/bin/env python3
"""Guardrails HID-4d.3c1: Drop Endpoint com prova física Disabled."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "kernel/src/drivers/xhci_configure_endpoint.sotlas"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", match.end())
    if brace < 0:
        raise AssertionError(f"missing function body {name}")
    depth = 0
    index = brace
    while index < len(source):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
        index += 1
    raise AssertionError(f"unterminated function {name}")


class XhciHidDropEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = STAGE.read_text(encoding="utf-8")
        cls.drop = function_body(cls.text, "xhci_configure_endpoint_drop_hid_for_slot")
        cls.proof = function_body(cls.text, "xhci_configure_endpoint_drop_complete_for")

    def test_disabled_is_distinct_from_invalid_context_access(self):
        self.assertIn("XHCI_ENDPOINT_STATE_DISABLED: u8 = 0", self.text)
        self.assertIn("XHCI_ENDPOINT_STATE_INVALID: u8 = 0xFF", self.text)
        state = function_body(self.text, "xhci_configure_endpoint_output_state")
        self.assertIn("return XHCI_ENDPOINT_STATE_INVALID", state)
        self.assertIn("dw0 & XHCI_ENDPOINT_STATE_MASK", state)

    def test_drop_is_exact_epoch_and_requires_logical_teardown(self):
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", self.drop)
        self.assertGreaterEqual(
            self.drop.count("xhci_hid_lifecycle_logical_teardown_complete_for(slot_id, epoch)"),
            3,
        )
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_EPOCHS[index] != epoch", self.drop)
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_DCIS[index] != dci", self.drop)

    def test_endpoint_must_be_physically_stopped_before_drop(self):
        stopped = self.drop.index("XHCI_ENDPOINT_STATE_STOPPED")
        command = self.drop.index("xhci_trb_configure_endpoint")
        self.assertLess(stopped, command)

    def test_input_context_uses_drop_dci_and_only_adds_slot_context(self):
        self.assertIn("let drop_flag = 1 << (dci as u32)", self.drop)
        self.assertIn("drop_flags_offset, drop_flag", self.drop)
        self.assertIn("add_flags_offset,\n           XHCI_INPUT_CONTROL_ADD_SLOT", self.drop)
        self.assertIn("old_slot_dw0 & ~XHCI_SLOT_CONTEXT_ENTRIES_MASK", self.drop)
        self.assertIn("1 << XHCI_SLOT_CONTEXT_ENTRIES_SHIFT", self.drop)

    def test_configure_endpoint_is_not_deconfigure_all(self):
        command = self.drop.split("let command = xhci_trb_configure_endpoint", 1)[1]
        command = command.split("if !xhci_command_execute", 1)[0]
        self.assertIn("false,", command)
        self.assertIn("xhci_command_producer_cycle()", command)
        self.assertNotIn("xhci_command_submit", self.drop)
        self.assertNotIn("xhci_command_wait_completion", self.drop)

    def test_precompletion_failures_restore_input_context(self):
        execute = self.drop.index("if !xhci_command_execute(command, slot_id)")
        before = self.drop[:execute]
        failure = self.drop[execute:self.drop.index("if xhci_device_table_slot_epoch", execute)]
        for token in ("old_drop_flags", "old_add_flags", "old_slot_dw0"):
            self.assertIn(token, before)
            self.assertIn(token, failure)

    def test_success_requires_output_endpoint_disabled_before_publication(self):
        execute = self.drop.index("if !xhci_command_execute(command, slot_id)")
        disabled = self.drop.index("XHCI_ENDPOINT_STATE_DISABLED", execute)
        publish = self.drop.index("XHCI_CONFIGURE_ENDPOINT_DROPPED_SLOTS[index] = true", execute)
        self.assertLess(disabled, publish)
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_READY_SLOTS[index] = false", self.drop[publish - 240:])

    def test_drop_completion_rechecks_physical_disabled_state(self):
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_DROPPED_SLOTS[index]", self.proof)
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_READY_SLOTS[index]", self.proof)
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", self.proof)
        self.assertIn("XHCI_ENDPOINT_STATE_DISABLED", self.proof)

    def test_3c1_does_not_free_ring_context_or_slot(self):
        lowered = self.drop.lower()
        for forbidden in (
            "dma_release",
            "dma_unshare_from_device",
            "xhci_trb_disable_slot",
            "xhci_device_table_release",
            "dcbaa",
        ):
            self.assertNotIn(forbidden, lowered)


if __name__ == "__main__":
    unittest.main()
