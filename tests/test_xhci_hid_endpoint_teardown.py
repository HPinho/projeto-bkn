#!/usr/bin/env python3
"""Guardrails HID-4d.3c3: orquestracao/publicacao do teardown fisico HID."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEARDOWN = ROOT / "kernel/src/drivers/xhci_hid_teardown.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


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


class XhciHidEndpointTeardownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = TEARDOWN.read_text(encoding="utf-8")
        cls.main_text = MAIN.read_text(encoding="utf-8")
        cls.ready = function_body(cls.text, "xhci_hid_teardown_epoch_ready")
        cls.begin = function_body(cls.text, "xhci_hid_teardown_begin_for")
        cls.publish = function_body(
            cls.text, "xhci_hid_teardown_publish_complete_for"
        )
        cls.complete = function_body(
            cls.text, "xhci_hid_teardown_endpoint_complete_for"
        )
        cls.orchestrate = function_body(
            cls.text, "xhci_hid_teardown_endpoint_for"
        )

    def test_module_is_part_of_native_graph(self):
        self.assertIn(
            "import kernel::drivers::xhci_hid_teardown::*;", self.main_text
        )

    def test_orchestrator_sits_above_certified_layers(self):
        for dependency in (
            "import kernel::drivers::xhci_device_table::*;",
            "import kernel::drivers::xhci_hid_context::*;",
            "import kernel::drivers::xhci_configure_endpoint::*;",
            "import kernel::drivers::xhci_hid_lifecycle::*;",
        ):
            self.assertIn(dependency, self.text)
        self.assertNotIn("import kernel::memory::dma::*;", self.text)
        self.assertNotIn("import kernel::drivers::xhci_context::*;", self.text)
        self.assertNotIn("import kernel::drivers::xhci_command::*;", self.text)

    def test_epoch_gate_requires_detach_pending_and_logical_completion(self):
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", self.ready)
        self.assertIn(
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING",
            self.ready,
        )
        self.assertIn(
            "xhci_hid_lifecycle_logical_teardown_complete_for(slot_id, epoch)",
            self.ready,
        )

    def test_publication_state_is_smp_serialized(self):
        self.assertIn("x86_irq_save_disable", self.text)
        self.assertIn("spinlock_lock(&mut XHCI_HID_ENDPOINT_TEARDOWN_LOCK)", self.text)
        self.assertIn("spinlock_unlock(&mut XHCI_HID_ENDPOINT_TEARDOWN_LOCK)", self.text)
        self.assertIn("xhci_hid_teardown_lock_irq()", self.begin)
        self.assertIn("xhci_hid_teardown_unlock_irq(flags)", self.begin)
        self.assertIn("xhci_hid_teardown_lock_irq()", self.publish)
        self.assertIn("xhci_hid_teardown_unlock_irq(flags)", self.publish)

    def test_hardware_and_dma_steps_run_outside_publication_lock(self):
        # O orquestrador publico nao segura o lock ao atravessar 3c1/3c2.
        self.assertNotIn("xhci_hid_teardown_lock_irq", self.orchestrate)
        self.assertNotIn("spinlock_lock", self.orchestrate)
        self.assertNotIn("spinlock_unlock", self.orchestrate)

    def test_sequence_is_logical_drop_release_publish(self):
        begin = self.orchestrate.index("xhci_hid_teardown_begin_for")
        first_drop_proof = self.orchestrate.index(
            "xhci_configure_endpoint_drop_complete_for", begin
        )
        drop = self.orchestrate.index(
            "xhci_configure_endpoint_drop_hid_for_slot", first_drop_proof
        )
        second_drop_proof = self.orchestrate.index(
            "xhci_configure_endpoint_drop_complete_for", drop
        )
        first_ring_proof = self.orchestrate.index(
            "xhci_hid_context_ring_release_complete_for", second_drop_proof
        )
        release = self.orchestrate.index(
            "xhci_hid_lifecycle_release_transfer_ring_for", first_ring_proof
        )
        second_ring_proof = self.orchestrate.index(
            "xhci_hid_context_ring_release_complete_for", release
        )
        publish = self.orchestrate.index(
            "xhci_hid_teardown_publish_complete_for", second_ring_proof
        )
        self.assertLess(begin, first_drop_proof)
        self.assertLess(first_drop_proof, drop)
        self.assertLess(drop, second_drop_proof)
        self.assertLess(second_drop_proof, first_ring_proof)
        self.assertLess(first_ring_proof, release)
        self.assertLess(release, second_ring_proof)
        self.assertLess(second_ring_proof, publish)

    def test_completion_rechecks_physical_proofs(self):
        self.assertIn("xhci_hid_teardown_epoch_ready(slot_id, epoch)", self.complete)
        self.assertIn(
            "xhci_configure_endpoint_drop_complete_for(slot_id, epoch)",
            self.complete,
        )
        self.assertIn(
            "xhci_hid_context_ring_release_complete_for(slot_id, epoch)",
            self.complete,
        )
        self.assertIn("XHCI_HID_ENDPOINT_TEARDOWN_STATES[index].complete", self.complete)

    def test_publish_requires_started_and_both_physical_proofs(self):
        self.assertIn(
            "xhci_configure_endpoint_drop_complete_for(slot_id, epoch)", self.publish
        )
        self.assertIn(
            "xhci_hid_context_ring_release_complete_for(slot_id, epoch)", self.publish
        )
        self.assertIn(
            "!XHCI_HID_ENDPOINT_TEARDOWN_STATES[index].started", self.publish
        )
        self.assertIn(
            "XHCI_HID_ENDPOINT_TEARDOWN_STATES[index].complete = true", self.publish
        )

    def test_same_epoch_path_is_retry_safe(self):
        self.assertIn(
            "if xhci_hid_teardown_endpoint_complete_for(slot_id, epoch) { return true; }",
            self.orchestrate,
        )
        self.assertIn(
            "if !xhci_configure_endpoint_drop_complete_for(slot_id, epoch)",
            self.orchestrate,
        )
        self.assertIn(
            "if !xhci_hid_context_ring_release_complete_for(slot_id, epoch)",
            self.orchestrate,
        )

    def test_foreign_epoch_cannot_overwrite_incomplete_state(self):
        self.assertIn(
            "XHCI_HID_ENDPOINT_TEARDOWN_STATES[index].epoch != epoch", self.begin
        )
        self.assertIn(
            "if !XHCI_HID_ENDPOINT_TEARDOWN_STATES[index].complete", self.begin
        )

    def test_3c3_does_not_cross_disable_slot_boundary(self):
        forbidden = (
            "dma_release",
            "dma_unshare_from_device",
            "xhci_trb_disable_slot",
            "XHCI_TRB_TYPE_DISABLE_SLOT",
            "xhci_device_table_release",
            "xhci_context_",
            "DCBAA",
            "dcbaa",
            "xhci_command_execute",
        )
        for token in forbidden:
            self.assertNotIn(token, self.orchestrate)
            self.assertNotIn(token, self.publish)


if __name__ == "__main__":
    unittest.main()
