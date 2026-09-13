#!/usr/bin/env python3
"""Guardrails para cleanup lógico SET_CONFIGURATION em enumeração FAILED."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SET_CONFIGURATION = ROOT / "kernel/src/drivers/xhci_set_configuration.sotlas"
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


class XhciFailedSetConfigurationCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.set_text = SET_CONFIGURATION.read_text(encoding="utf-8")
        cls.enum_text = ENUMERATION.read_text(encoding="utf-8")
        cls.match = function_body(
            cls.set_text, "xhci_set_configuration_failed_slot_matches"
        )
        cls.empty = function_body(
            cls.set_text, "xhci_set_configuration_failed_state_empty_for"
        )
        cls.release = function_body(
            cls.set_text, "xhci_set_configuration_release_failed_for_epoch"
        )
        cls.complete = function_body(
            cls.set_text, "xhci_set_configuration_failed_release_complete_for"
        )
        cls.detach = function_body(
            cls.set_text, "xhci_set_configuration_quiesce_for_epoch"
        )
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

    def test_stale_epoch_is_only_accepted_when_state_is_neutral(self):
        self.assertIn("XHCI_SET_CONFIGURATION_STATES[index].epoch != epoch", self.release)
        self.assertIn(
            "return xhci_set_configuration_failed_state_empty_for(index, slot_id);",
            self.release,
        )
        self.assertNotIn("XHCI_SET_CONFIGURATION_STATES[index].epoch =", self.release)
        self.assertNotIn("xhci_set_configuration_prepare_state", self.release)
        self.assertIn("!XHCI_SET_CONFIGURATION_STATES[index].ready", self.empty)
        self.assertIn("XHCI_SET_CONFIGURATION_STATES[index].value == 0", self.empty)
        self.assertIn("XHCI_SET_CONFIGURATION_ACTIVE_SLOT_ID != slot_id", self.empty)

    def test_release_only_clears_logical_publication(self):
        self.assertIn("XHCI_SET_CONFIGURATION_STATES[index].ready = false", self.release)
        self.assertIn("XHCI_SET_CONFIGURATION_STATES[index].value = 0", self.release)
        self.assertIn("XHCI_SET_CONFIGURATION_ACTIVE_SLOT_ID = 0", self.release)
        for forbidden in (
            "xhci_ep0_submit_control_td_for_slot",
            "xhci_transfer_wait_ep0_completion",
            "xhci_hid_descriptor_initialize_for_slot",
            "xhci_trb_setup_stage",
            "xhci_command_execute",
            "dma_release",
            "dma_unshare_from_device",
            "xhci_context_",
            "pmm_free",
        ):
            self.assertNotIn(forbidden, self.release)

    def test_failed_complete_preserves_exact_epoch_gate(self):
        self.assertIn(
            "xhci_set_configuration_failed_slot_matches(slot_id, epoch)",
            self.complete,
        )
        self.assertIn("XHCI_SET_CONFIGURATION_STATES[index].epoch != epoch", self.complete)
        self.assertIn(
            "return xhci_set_configuration_failed_state_empty_for(index, slot_id);",
            self.complete,
        )

    def test_detach_path_remains_separate(self):
        self.assertIn(
            "xhci_set_configuration_epoch_matches_detach(slot_id, epoch)",
            self.detach,
        )
        self.assertNotIn("failed_slot_matches", self.detach)

    def test_enumeration_orders_set_configuration_before_evaluate_ep0_address(self):
        disable = self.failed_enum.index("xhci_command_execute(command, slot_id)")
        configuration = self.failed_enum.index(
            "xhci_configuration_release_failed_for_epoch(slot_id, epoch)"
        )
        descriptor = self.failed_enum.index(
            "xhci_device_descriptor_release_failed_for_epoch(slot_id, epoch)"
        )
        set_configuration = self.failed_enum.index(
            "xhci_set_configuration_release_failed_for_epoch(slot_id, epoch)"
        )
        evaluate = self.failed_enum.index(
            "xhci_evaluate_context_release_failed_for_epoch(slot_id, epoch)"
        )
        ep0 = self.failed_enum.index("xhci_ep0_release_failed_for_epoch(slot_id, epoch)")
        address = self.failed_enum.index(
            "xhci_address_release_failed_for_epoch(slot_id, epoch)"
        )
        self.assertLess(disable, configuration)
        self.assertLess(configuration, descriptor)
        self.assertLess(descriptor, set_configuration)
        self.assertLess(set_configuration, evaluate)
        self.assertLess(evaluate, ep0)
        self.assertLess(ep0, address)
        self.assertIn(
            "set_configuration_released && evaluate_released && ep0_released",
            self.failed_enum,
        )


if __name__ == "__main__":
    unittest.main()
