#!/usr/bin/env python3
"""Guardrails para cleanup lógico Address Device em enumeração FAILED."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
ADDRESS = ROOT / "kernel/src/drivers/xhci_address.sotlas"
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


class XhciFailedAddressCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.address_text = ADDRESS.read_text(encoding="utf-8")
        cls.enum_text = ENUMERATION.read_text(encoding="utf-8")
        cls.match = function_body(cls.address_text, "xhci_address_failed_slot_matches")
        cls.release = function_body(
            cls.address_text, "xhci_address_release_failed_for_epoch"
        )
        cls.complete = function_body(
            cls.address_text, "xhci_address_failed_release_complete_for"
        )
        cls.failed_enum = function_body(
            cls.enum_text, "xhci_hid_enumeration_disable_failed_slot"
        )

    def test_failed_cleanup_requires_exact_device_table_epoch(self):
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", self.match)
        self.assertIn(
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_FAILED",
            self.match,
        )
        self.assertIn("xhci_address_failed_slot_matches(slot_id, epoch)", self.release)
        self.assertIn("xhci_address_failed_slot_matches(slot_id, epoch)", self.complete)

    def test_stale_epoch_is_never_overwritten(self):
        stale = self.release.index("XHCI_ADDRESS_EPOCHS[index] != epoch")
        already_empty = self.release.index(
            "return xhci_address_failed_state_empty_for(index, slot_id);", stale
        )
        ready_clear = self.release.index("XHCI_ADDRESS_READY_SLOTS[index] = false")
        self.assertLess(stale, already_empty)
        self.assertLess(already_empty, ready_clear)
        self.assertNotIn("XHCI_ADDRESS_EPOCHS[index] = epoch", self.release)

    def test_cleanup_is_logical_only(self):
        forbidden = (
            "dma_release",
            "dma_unshare_from_device",
            "xhci_context_release",
            "xhci_ep0_quiesce",
            "xhci_device_table_release",
            "xhci_slot_release",
        )
        for token in forbidden:
            self.assertNotIn(token, self.release)
            self.assertNotIn(token, self.complete)

    def test_enumeration_calls_address_cleanup_only_after_disable_slot_completion(self):
        disable = self.failed_enum.index("xhci_command_execute(command, slot_id)")
        configuration = self.failed_enum.index(
            "xhci_configuration_release_failed_for_epoch(slot_id, epoch)"
        )
        descriptor = self.failed_enum.index(
            "xhci_device_descriptor_release_failed_for_epoch(slot_id, epoch)"
        )
        address = self.failed_enum.index(
            "xhci_address_release_failed_for_epoch(slot_id, epoch)"
        )
        self.assertLess(disable, configuration)
        self.assertLess(configuration, descriptor)
        self.assertLess(descriptor, address)

    def test_enumeration_keeps_physical_owners_quarantined(self):
        forbidden = (
            "dma_release",
            "dma_unshare_from_device",
            "xhci_context_release",
            "xhci_device_table_release",
            "xhci_slot_release",
        )
        for token in forbidden:
            self.assertNotIn(token, self.failed_enum)


if __name__ == "__main__":
    unittest.main()
