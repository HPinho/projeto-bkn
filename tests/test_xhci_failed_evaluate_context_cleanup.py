#!/usr/bin/env python3
"""Guardrails para cleanup lógico Evaluate Context em enumeração FAILED."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVALUATE = ROOT / "kernel/src/drivers/xhci_evaluate_context.sotlas"
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


class XhciFailedEvaluateContextCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evaluate_text = EVALUATE.read_text(encoding="utf-8")
        cls.enum_text = ENUMERATION.read_text(encoding="utf-8")
        cls.match = function_body(
            cls.evaluate_text, "xhci_evaluate_context_failed_slot_matches"
        )
        cls.empty = function_body(
            cls.evaluate_text, "xhci_evaluate_context_failed_state_empty_for"
        )
        cls.release = function_body(
            cls.evaluate_text, "xhci_evaluate_context_release_failed_for_epoch"
        )
        cls.complete = function_body(
            cls.evaluate_text,
            "xhci_evaluate_context_failed_release_complete_for",
        )
        cls.detach = function_body(
            cls.evaluate_text, "xhci_evaluate_context_quiesce_for_epoch"
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

    def test_neutral_state_is_idempotent_without_epoch_adoption(self):
        self.assertIn("XHCI_EVALUATE_CONTEXT_EPOCHS[index] != epoch", self.release)
        self.assertIn(
            "return xhci_evaluate_context_failed_state_empty_for(index);",
            self.release,
        )
        self.assertNotIn("XHCI_EVALUATE_CONTEXT_EPOCHS[index] =", self.release)
        self.assertNotIn("xhci_evaluate_context_reset_slot", self.release)
        self.assertIn(
            "XHCI_EVALUATE_CONTEXT_LAST_EP0_MAX_PACKETS[index] == 0",
            self.empty,
        )
        self.assertIn(
            "!XHCI_EVALUATE_CONTEXT_COMMAND_SUBMITTED_SLOTS[index]",
            self.empty,
        )

    def test_release_is_logical_only(self):
        self.assertIn(
            "XHCI_EVALUATE_CONTEXT_LAST_EP0_MAX_PACKETS[index] = 0",
            self.release,
        )
        self.assertIn(
            "XHCI_EVALUATE_CONTEXT_COMMAND_SUBMITTED_SLOTS[index] = false",
            self.release,
        )
        for forbidden in (
            "xhci_context_input_physical_for",
            "xhci_context_device_physical_for",
            "xhci_context_ep0_ring_physical_for",
            "direct_map_virtual_address",
            "dma_release",
            "dma_unshare_from_device",
            "pmm_free",
            "xhci_command_execute",
        ):
            self.assertNotIn(forbidden, self.release)

    def test_failed_complete_keeps_exact_epoch_gate(self):
        self.assertIn(
            "xhci_evaluate_context_failed_slot_matches(slot_id, epoch)",
            self.complete,
        )
        self.assertIn("XHCI_EVALUATE_CONTEXT_EPOCHS[index] != epoch", self.complete)
        self.assertIn(
            "return xhci_evaluate_context_failed_state_empty_for(index);",
            self.complete,
        )

    def test_detach_path_stays_separate(self):
        self.assertIn(
            "xhci_evaluate_context_epoch_matches_detach(slot_id, epoch)",
            self.detach,
        )
        self.assertNotIn("failed_slot_matches", self.detach)

    def test_failed_enumeration_orders_evaluate_before_ep0_and_address(self):
        disable = self.failed_enum.index("xhci_command_execute(command, slot_id)")
        configuration = self.failed_enum.index(
            "xhci_configuration_release_failed_for_epoch(slot_id, epoch)"
        )
        descriptor = self.failed_enum.index(
            "xhci_device_descriptor_release_failed_for_epoch(slot_id, epoch)"
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
        self.assertLess(descriptor, evaluate)
        self.assertLess(evaluate, ep0)
        self.assertLess(ep0, address)
        return_start = self.failed_enum.rfind("return ")
        self.assertGreaterEqual(return_start, 0)
        return_expression = self.failed_enum[return_start:]
        self.assertIn("evaluate_released", return_expression)
        self.assertIn("ep0_released", return_expression)
        self.assertIn("address_released", return_expression)


if __name__ == "__main__":
    unittest.main()
