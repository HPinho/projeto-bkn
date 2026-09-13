#!/usr/bin/env python3
"""Guardrails para cleanup lógico EP0 em enumeração FAILED."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EP0 = ROOT / "kernel/src/drivers/xhci_ep0.sotlas"
ENUMERATION = ROOT / "kernel/src/drivers/xhci_hid_enumeration.sotlas"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", match.end())
    if brace < 0:
        raise AssertionError(f"missing body {name}")
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
    raise AssertionError(f"unterminated body {name}")


class XhciFailedEp0CleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ep0_text = EP0.read_text(encoding="utf-8")
        cls.enum_text = ENUMERATION.read_text(encoding="utf-8")
        cls.match = function_body(cls.ep0_text, "xhci_ep0_failed_slot_matches")
        cls.empty = function_body(cls.ep0_text, "xhci_ep0_failed_state_empty_for")
        cls.release = function_body(cls.ep0_text, "xhci_ep0_release_failed_for_epoch")
        cls.complete = function_body(
            cls.ep0_text, "xhci_ep0_failed_release_complete_for"
        )
        cls.detach = function_body(cls.ep0_text, "xhci_ep0_quiesce_for_epoch")
        cls.failed_enum = function_body(
            cls.enum_text, "xhci_hid_enumeration_disable_failed_slot"
        )

    def test_failed_cleanup_requires_exact_failed_epoch(self):
        self.assertIn("xhci_device_table_slot_is_valid(slot_id)", self.match)
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", self.match)
        self.assertIn(
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_FAILED",
            self.match,
        )
        self.assertNotIn("XHCI_DEVICE_STATE_DETACH_PENDING", self.match)

    def test_neutral_state_is_idempotent_without_adopting_stale_epoch(self):
        self.assertIn("XHCI_EP0_STATES[state_index].epoch != epoch", self.release)
        self.assertIn(
            "return xhci_ep0_failed_state_empty_for(state_index, slot_id);",
            self.release,
        )
        self.assertNotIn("XHCI_EP0_STATES[state_index].epoch =", self.release)
        self.assertIn("!XHCI_EP0_STATES[index].ready", self.empty)
        self.assertIn("XHCI_EP0_STATES[index].enqueue_index == 0", self.empty)
        self.assertIn("XHCI_EP0_STATES[index].producer_cycle", self.empty)
        self.assertIn("XHCI_EP0_STATES[index].last_status_trb_physical == 0", self.empty)
        self.assertIn("XHCI_EP0_ACTIVE_SLOT_ID != slot_id", self.empty)

    def test_release_only_clears_ep0_logical_state(self):
        for expected in (
            "XHCI_EP0_STATES[state_index].ready = false",
            "XHCI_EP0_STATES[state_index].enqueue_index = 0",
            "XHCI_EP0_STATES[state_index].producer_cycle = true",
            "XHCI_EP0_STATES[state_index].last_status_trb_physical = 0",
            "XHCI_EP0_ACTIVE_SLOT_ID = 0",
        ):
            self.assertIn(expected, self.release)
        for forbidden in (
            "dma_release",
            "dma_unshare_from_device",
            "xhci_context_ep0_ring_physical_for",
            "xhci_context_release",
            "pmm_free",
        ):
            self.assertNotIn(forbidden, self.release)

    def test_failed_complete_keeps_exact_epoch_gate(self):
        self.assertIn("xhci_ep0_failed_slot_matches(slot_id, epoch)", self.complete)
        self.assertIn("XHCI_EP0_STATES[state_index].epoch != epoch", self.complete)
        self.assertIn(
            "return xhci_ep0_failed_state_empty_for(state_index, slot_id);",
            self.complete,
        )

    def test_detach_helper_remains_separate(self):
        self.assertIn("xhci_ep0_epoch_matches_detach(slot_id, epoch)", self.detach)
        self.assertNotIn("xhci_ep0_failed_slot_matches", self.detach)

    def test_enumeration_recovers_ep0_after_disable_and_before_address(self):
        disable = self.failed_enum.index("xhci_command_execute(command, slot_id)")
        configuration = self.failed_enum.index(
            "xhci_configuration_release_failed_for_epoch(slot_id, epoch)"
        )
        descriptor = self.failed_enum.index(
            "xhci_device_descriptor_release_failed_for_epoch(slot_id, epoch)"
        )
        ep0 = self.failed_enum.index("xhci_ep0_release_failed_for_epoch(slot_id, epoch)")
        address = self.failed_enum.index(
            "xhci_address_release_failed_for_epoch(slot_id, epoch)"
        )
        self.assertLess(disable, configuration)
        self.assertLess(configuration, descriptor)
        self.assertLess(descriptor, ep0)
        self.assertLess(ep0, address)
        self.assertIn("ep0_released && address_released", self.failed_enum)


if __name__ == "__main__":
    unittest.main()
