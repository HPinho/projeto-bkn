#!/usr/bin/env python3
"""Guardrails para cleanup lógico de Transfer state em enumeração FAILED."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
TRANSFER = ROOT / "kernel/src/drivers/xhci_transfer.sotlas"
ENUMERATION = ROOT / "kernel/src/drivers/xhci_hid_enumeration.sotlas"
COMMAND = ROOT / "kernel/src/drivers/xhci_command.sotlas"


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


class XhciFailedTransferCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transfer_text = TRANSFER.read_text(encoding="utf-8")
        cls.enum_text = ENUMERATION.read_text(encoding="utf-8")
        cls.command_text = COMMAND.read_text(encoding="utf-8")
        cls.match = function_body(cls.transfer_text, "xhci_transfer_failed_slot_matches")
        cls.empty = function_body(cls.transfer_text, "xhci_transfer_failed_state_empty_for")
        cls.owned = function_body(cls.transfer_text, "xhci_transfer_failed_state_owned_by_epoch")
        cls.release = function_body(cls.transfer_text, "xhci_transfer_release_failed_for_epoch")
        cls.complete = function_body(
            cls.transfer_text, "xhci_transfer_failed_release_complete_for"
        )
        cls.detach = function_body(
            cls.transfer_text, "xhci_transfer_clear_slot_state_for_epoch"
        )
        cls.command_wait = function_body(cls.command_text, "xhci_command_wait_completion")
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

    def test_foreign_epoch_mailbox_or_result_fails_closed(self):
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].epoch != 0", self.owned)
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS[index].epoch != epoch", self.owned)
        self.assertIn("XHCI_TRANSFER_RESULTS[index].epoch != 0", self.owned)
        self.assertIn("XHCI_TRANSFER_RESULTS[index].epoch != epoch", self.owned)
        self.assertIn(
            "xhci_transfer_failed_state_owned_by_epoch(index, epoch)", self.release
        )

    def test_release_neutralizes_only_logical_mailbox_and_result(self):
        self.assertIn("xhci_transfer_clear_pending_index(index)", self.release)
        for token in (
            "XHCI_TRANSFER_RESULTS[index].valid = false",
            "XHCI_TRANSFER_RESULTS[index].epoch = 0",
            "XHCI_TRANSFER_RESULTS[index].endpoint_id = 0",
            "XHCI_TRANSFER_RESULTS[index].residual_length = 0",
            "XHCI_TRANSFER_RESULTS[index].completion_code = 0",
            "XHCI_TRANSFER_ACTIVE_SLOT_ID = 0",
        ):
            self.assertIn(token, self.release)
        for token in (
            "xhci_transfer_route_next_event",
            "xhci_event_consumer_",
            "x86_mmio",
            "dma_",
            "xhci_ring_",
            "xhci_context_",
            "xhci_command_",
            "pmm_free",
        ):
            self.assertNotIn(token, self.release)
            self.assertNotIn(token, self.complete)

    def test_neutral_state_requires_all_correlation_fields_empty(self):
        for token in (
            "!XHCI_TRANSFER_PENDING_EVENTS[index].valid",
            "XHCI_TRANSFER_PENDING_EVENTS[index].epoch == 0",
            "XHCI_TRANSFER_PENDING_EVENTS[index].endpoint_id == 0",
            "XHCI_TRANSFER_PENDING_EVENTS[index].trb_pointer == 0",
            "!XHCI_TRANSFER_RESULTS[index].valid",
            "XHCI_TRANSFER_RESULTS[index].epoch == 0",
            "XHCI_TRANSFER_RESULTS[index].endpoint_id == 0",
            "XHCI_TRANSFER_ACTIVE_SLOT_ID != slot_id",
        ):
            self.assertIn(token, self.empty)

    def test_detach_path_remains_separate(self):
        self.assertIn("xhci_transfer_teardown_epoch_matches(slot_id, epoch)", self.detach)
        self.assertNotIn("failed_slot_matches", self.detach)

    def test_disable_wait_routes_transfer_events_before_command_completion(self):
        transfer_event = self.command_wait.index("XHCI_TRB_TYPE_TRANSFER_EVENT")
        route = self.command_wait.index("xhci_transfer_route_next_event()", transfer_event)
        command_completion = self.command_wait.index(
            "XHCI_TRB_TYPE_COMMAND_COMPLETION_EVENT", route
        )
        self.assertLess(transfer_event, route)
        self.assertLess(route, command_completion)

    def test_enumeration_clears_transfer_state_immediately_after_disable(self):
        disable = self.failed_enum.index("xhci_command_execute(command, slot_id)")
        transfer = self.failed_enum.index(
            "xhci_transfer_release_failed_for_epoch(slot_id, epoch)"
        )
        configuration = self.failed_enum.index(
            "xhci_configuration_release_failed_for_epoch(slot_id, epoch)"
        )
        descriptor = self.failed_enum.index(
            "xhci_device_descriptor_release_failed_for_epoch(slot_id, epoch)"
        )
        set_configuration = self.failed_enum.index(
            "xhci_set_configuration_release_failed_for_epoch(slot_id, epoch)"
        )
        configure_endpoint = self.failed_enum.index(
            "xhci_configure_endpoint_release_failed_for_epoch(slot_id, epoch)"
        )
        evaluate = self.failed_enum.index(
            "xhci_evaluate_context_release_failed_for_epoch(slot_id, epoch)"
        )
        ep0 = self.failed_enum.index("xhci_ep0_release_failed_for_epoch(slot_id, epoch)")
        address = self.failed_enum.index(
            "xhci_address_release_failed_for_epoch(slot_id, epoch)"
        )
        self.assertLess(disable, transfer)
        self.assertLess(transfer, configuration)
        self.assertLess(configuration, descriptor)
        self.assertLess(descriptor, set_configuration)
        self.assertLess(set_configuration, configure_endpoint)
        self.assertLess(configure_endpoint, evaluate)
        self.assertLess(evaluate, ep0)
        self.assertLess(ep0, address)

        return_start = self.failed_enum.rfind("return ")
        self.assertGreaterEqual(return_start, 0)
        return_expression = self.failed_enum[return_start:]
        for owner in (
            "identity_released",
            "transfer_released",
            "configuration_released",
            "descriptor_released",
            "set_configuration_released",
            "configure_endpoint_released",
            "evaluate_released",
            "ep0_released",
            "address_released",
        ):
            self.assertIn(owner, return_expression)


if __name__ == "__main__":
    unittest.main()
