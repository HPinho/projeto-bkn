#!/usr/bin/env python3
"""Guardrails HID-4d.4a2: quiesce lógico per-slot antes de Disable Slot."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVERS = ROOT / "kernel/src/drivers"
ADDRESS = DRIVERS / "xhci_address.sotlas"
EP0 = DRIVERS / "xhci_ep0.sotlas"
EVALUATE = DRIVERS / "xhci_evaluate_context.sotlas"
SET_CONFIGURATION = DRIVERS / "xhci_set_configuration.sotlas"
SLOT_TEARDOWN = DRIVERS / "xhci_slot_teardown.sotlas"


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


class XhciSlotLogicalQuiesceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.address = ADDRESS.read_text(encoding="utf-8")
        cls.ep0 = EP0.read_text(encoding="utf-8")
        cls.evaluate = EVALUATE.read_text(encoding="utf-8")
        cls.set_configuration = SET_CONFIGURATION.read_text(encoding="utf-8")
        cls.teardown = SLOT_TEARDOWN.read_text(encoding="utf-8")
        cls.orchestrate = function_body(
            cls.teardown, "xhci_slot_teardown_quiesce_logical_state_for"
        )
        cls.complete = function_body(
            cls.teardown, "xhci_slot_teardown_logical_state_complete_for"
        )

    def test_operational_paths_fail_closed_in_detach_pending(self):
        checks = (
            (self.address, "xhci_address_slot"),
            (self.ep0, "xhci_ep0_prepare_for_slot"),
            (self.ep0, "xhci_ep0_is_ready_for"),
            (self.evaluate, "xhci_evaluate_ep0_max_packet_for_slot"),
            (self.set_configuration, "xhci_set_configuration_prepare_state"),
            (self.set_configuration, "xhci_set_configuration_for_slot"),
        )
        for source, name in checks:
            body = function_body(source, name)
            self.assertIn(
                "xhci_device_table_state(slot_id) == XHCI_DEVICE_STATE_DETACH_PENDING",
                body,
                name,
            )

    def test_all_owner_quiesce_helpers_are_exact_detach_epoch(self):
        checks = (
            (self.address, "xhci_address_epoch_matches_detach"),
            (self.ep0, "xhci_ep0_epoch_matches_detach"),
            (self.evaluate, "xhci_evaluate_context_epoch_matches_detach"),
            (
                self.set_configuration,
                "xhci_set_configuration_epoch_matches_detach",
            ),
        )
        for source, name in checks:
            body = function_body(source, name)
            self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", body)
            self.assertIn(
                "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING",
                body,
            )

    def test_upper_gate_requires_4a1_completion(self):
        first = self.orchestrate.index(
            "xhci_slot_teardown_enumeration_dma_complete_for(slot_id, epoch)"
        )
        set_config = self.orchestrate.index(
            "xhci_set_configuration_quiesce_for_epoch"
        )
        self.assertLess(first, set_config)
        self.assertIn(
            "xhci_slot_teardown_enumeration_dma_complete_for(slot_id, epoch)",
            self.complete,
        )

    def test_quiesce_order_is_set_config_evaluate_ep0_address(self):
        set_config = self.orchestrate.index(
            "xhci_set_configuration_quiesce_for_epoch"
        )
        evaluate = self.orchestrate.index(
            "xhci_evaluate_context_quiesce_for_epoch", set_config
        )
        ep0 = self.orchestrate.index("xhci_ep0_quiesce_for_epoch", evaluate)
        address = self.orchestrate.index("xhci_address_quiesce_for_epoch", ep0)
        self.assertLess(set_config, evaluate)
        self.assertLess(evaluate, ep0)
        self.assertLess(ep0, address)

    def test_each_owner_has_completion_proof(self):
        for token in (
            "xhci_set_configuration_quiesce_complete_for(slot_id, epoch)",
            "xhci_evaluate_context_quiesce_complete_for(slot_id, epoch)",
            "xhci_ep0_quiesce_complete_for(slot_id, epoch)",
            "xhci_address_quiesce_complete_for(slot_id, epoch)",
        ):
            self.assertIn(token, self.complete)

    def test_legacy_active_slot_aliases_are_cleared(self):
        set_quiesce = function_body(
            self.set_configuration, "xhci_set_configuration_quiesce_for_epoch"
        )
        ep0_quiesce = function_body(self.ep0, "xhci_ep0_quiesce_for_epoch")
        address_quiesce = function_body(self.address, "xhci_address_quiesce_for_epoch")
        self.assertIn("XHCI_SET_CONFIGURATION_ACTIVE_SLOT_ID = 0", set_quiesce)
        self.assertIn("XHCI_EP0_ACTIVE_SLOT_ID = 0", ep0_quiesce)
        self.assertIn("XHCI_ADDRESS_SLOT_ID = 0", address_quiesce)
        self.assertIn("XHCI_ADDRESS_READY = false", address_quiesce)

    def test_ep0_quiesce_is_logical_only(self):
        body = function_body(self.ep0, "xhci_ep0_quiesce_for_epoch")
        self.assertIn("ready = false", body)
        self.assertIn("last_status_trb_physical = 0", body)
        for forbidden in (
            "dma_release",
            "xhci_context_release",
            "xhci_trb_disable_slot",
            "xhci_device_table_release",
        ):
            self.assertNotIn(forbidden, body)

    def test_4a2_does_not_cross_disable_slot_or_barrier_boundary(self):
        for token in (
            "xhci_trb_disable_slot",
            "XHCI_TRB_TYPE_DISABLE_SLOT",
            "xhci_command_execute",
            "xhci_context_release",
            "dma_release",
            "DCBAA",
            "dcbaa",
            "xhci_device_table_release",
            "xhci_event_consumer",
            "ERDP",
        ):
            self.assertNotIn(token, self.orchestrate)
            self.assertNotIn(token, self.complete)

    def test_lower_owners_do_not_depend_on_slot_teardown(self):
        for source in (
            self.address,
            self.ep0,
            self.evaluate,
            self.set_configuration,
        ):
            self.assertNotIn("xhci_slot_teardown", source)

    def test_device_table_is_deliberately_retained_for_4d5(self):
        self.assertNotIn("xhci_device_table_release", self.teardown)
        self.assertIn("XHCI_DEVICE_STATE_DETACH_PENDING", self.teardown)


if __name__ == "__main__":
    unittest.main()
