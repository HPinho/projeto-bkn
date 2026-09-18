#!/usr/bin/env python3
"""Guardrails para cleanup lógico Configure Endpoint em enumeração FAILED."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIGURE = ROOT / "kernel/src/drivers/xhci_configure_endpoint.sotlas"
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


def final_return_expression(body: str) -> str:
    start = body.rfind("return ")
    if start < 0:
        raise AssertionError("missing final return")
    end = body.find(";", start)
    if end < 0:
        raise AssertionError("unterminated final return")
    return body[start:end]


class XhciFailedConfigureEndpointCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configure_text = CONFIGURE.read_text(encoding="utf-8")
        cls.enum_text = ENUMERATION.read_text(encoding="utf-8")
        cls.match = function_body(
            cls.configure_text, "xhci_configure_endpoint_failed_slot_matches"
        )
        cls.empty = function_body(
            cls.configure_text, "xhci_configure_endpoint_failed_state_empty_for"
        )
        cls.release = function_body(
            cls.configure_text, "xhci_configure_endpoint_release_failed_for_epoch"
        )
        cls.complete = function_body(
            cls.configure_text, "xhci_configure_endpoint_failed_release_complete_for"
        )
        cls.drop = function_body(
            cls.configure_text, "xhci_configure_endpoint_drop_hid_for_slot"
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
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_EPOCHS[index] != epoch", self.release)
        self.assertIn(
            "return xhci_configure_endpoint_failed_state_empty_for(index, slot_id);",
            self.release,
        )
        self.assertNotIn("XHCI_CONFIGURE_ENDPOINT_EPOCHS[index] =", self.release)
        self.assertIn("!XHCI_CONFIGURE_ENDPOINT_READY_SLOTS[index]", self.empty)
        self.assertIn("!XHCI_CONFIGURE_ENDPOINT_DROPPED_SLOTS[index]", self.empty)
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_DCIS[index] == 0", self.empty)
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_ACTIVE_SLOT_ID != slot_id", self.empty)

    def test_release_only_clears_logical_publication(self):
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_READY_SLOTS[index] = false", self.release)
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_DROPPED_SLOTS[index] = false", self.release)
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_DCIS[index] = 0", self.release)
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_ACTIVE_SLOT_ID = 0", self.release)
        for forbidden in (
            "xhci_configure_endpoint_drop_hid_for_slot",
            "xhci_configure_endpoint_output_state",
            "xhci_configure_endpoint_input_write32",
            "xhci_context_",
            "direct_map_virtual_address",
            "x86_read_cr3_raw",
            "xhci_command_execute",
            "dma_release",
            "dma_unshare_from_device",
            "pmm_free",
        ):
            self.assertNotIn(forbidden, self.release)

    def test_failed_complete_preserves_exact_epoch_gate(self):
        self.assertIn(
            "xhci_configure_endpoint_failed_slot_matches(slot_id, epoch)",
            self.complete,
        )
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_EPOCHS[index] != epoch", self.complete)
        self.assertIn(
            "return xhci_configure_endpoint_failed_state_empty_for(index, slot_id);",
            self.complete,
        )

    def test_physical_drop_primitive_remains_separate(self):
        self.assertIn("xhci_configure_endpoint_output_state", self.drop)
        self.assertIn("xhci_context_input_physical_for", self.drop)
        self.assertIn("xhci_command_execute", self.drop)
        self.assertNotIn("failed_slot_matches", self.drop)
        self.assertNotIn("release_failed_for_epoch", self.drop)

    def test_enumeration_orders_configure_between_set_and_evaluate(self):
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
        self.assertLess(disable, configuration)
        self.assertLess(configuration, descriptor)
        self.assertLess(descriptor, set_configuration)
        self.assertLess(set_configuration, configure_endpoint)
        self.assertLess(configure_endpoint, evaluate)
        self.assertLess(evaluate, ep0)
        self.assertLess(ep0, address)

        logical_start = self.failed_enum.index("let logical_released =")
        logical_end = self.failed_enum.index("if !logical_released", logical_start)
        return_expr = self.failed_enum[logical_start:logical_end]
        for required in (
            "set_configuration_released",
            "configure_endpoint_released",
            "evaluate_released",
            "ep0_released",
            "address_released",
        ):
            self.assertIn(required, return_expr)


if __name__ == "__main__":
    unittest.main()
