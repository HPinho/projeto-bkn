#!/usr/bin/env python3
"""Guardrails for HID-4d.3b1 logical teardown transaction gate."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "kernel/src/drivers/xhci_hid_lifecycle.sotlas"


def function_body(source: str, name: str) -> str:
    marker = f"fn {name}("
    start = source.find(marker)
    if start < 0:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", start)
    if brace < 0:
        raise AssertionError(f"missing function body {name}")
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
    raise AssertionError(f"unterminated function {name}")


class HidLogicalTeardownGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = LIFECYCLE.read_text(encoding="utf-8")

    def test_lifecycle_tracks_transaction_per_epoch(self) -> None:
        self.assertIn("pub logical_teardown_started: bool;", self.source)
        self.assertIn("logical_teardown_started: false", self.source)
        publish = function_body(self.source, "xhci_hid_lifecycle_publish_detach")
        self.assertIn(".epoch = epoch;", publish)
        self.assertIn(".endpoint_stopped = false;", publish)
        self.assertIn(".logical_teardown_started = false;", publish)

    def test_begin_requires_stop_and_drain_gate_before_mutation(self) -> None:
        body = function_body(
            self.source, "xhci_hid_lifecycle_begin_logical_teardown_for"
        )
        gate = body.find("xhci_hid_lifecycle_can_finalize_for(slot_id, epoch)")
        mutation = body.find(".logical_teardown_started = true;")
        self.assertGreaterEqual(gate, 0)
        self.assertGreater(mutation, gate)
        self.assertIn(".epoch != epoch", body)
        self.assertIn("!.detach_detected", body)
        self.assertIn("!.endpoint_stopped", body)

    def test_begin_is_idempotent_for_same_generation(self) -> None:
        body = function_body(
            self.source, "xhci_hid_lifecycle_begin_logical_teardown_for"
        )
        self.assertIn(".logical_teardown_started { return true; }", body)

    def test_query_revalidates_exact_current_generation(self) -> None:
        body = function_body(
            self.source, "xhci_hid_lifecycle_logical_teardown_started_for"
        )
        self.assertIn("xhci_hid_lifecycle_is_detach_pending_for(slot_id, epoch)", body)
        self.assertIn(".epoch == epoch", body)
        self.assertIn(".logical_teardown_started", body)

    def test_gate_does_not_release_physical_resources(self) -> None:
        body = function_body(
            self.source, "xhci_hid_lifecycle_begin_logical_teardown_for"
        )
        forbidden = (
            "dma_release",
            "dma_unshare_from_device",
            "drop_endpoint",
            "disable_slot",
            "ring_physical",
            "input_device_detach",
        )
        for token in forbidden:
            self.assertNotIn(token, body)


if __name__ == "__main__":
    unittest.main()
