#!/usr/bin/env python3
"""Guardrails HID-4d.4a1: teardown do DMA persistente de enumeracao xHCI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = ROOT / "kernel/src/drivers/xhci_descriptor.sotlas"
CONFIGURATION = ROOT / "kernel/src/drivers/xhci_configuration.sotlas"
SLOT_TEARDOWN = ROOT / "kernel/src/drivers/xhci_slot_teardown.sotlas"
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


class XhciEnumerationDmaTeardownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.descriptor = DESCRIPTOR.read_text(encoding="utf-8")
        cls.configuration = CONFIGURATION.read_text(encoding="utf-8")
        cls.teardown = SLOT_TEARDOWN.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")
        cls.descriptor_prepare = function_body(
            cls.descriptor, "xhci_descriptor_prepare_state"
        )
        cls.descriptor_epoch = function_body(
            cls.descriptor, "xhci_descriptor_epoch_matches"
        )
        cls.descriptor_release = function_body(
            cls.descriptor, "xhci_device_descriptor_release_persistent_for_epoch"
        )
        cls.descriptor_complete = function_body(
            cls.descriptor,
            "xhci_device_descriptor_persistent_release_complete_for",
        )
        cls.configuration_prepare = function_body(
            cls.configuration, "xhci_configuration_prepare_state"
        )
        cls.configuration_epoch = function_body(
            cls.configuration, "xhci_configuration_epoch_matches"
        )
        cls.configuration_release = function_body(
            cls.configuration, "xhci_configuration_release_persistent_for_epoch"
        )
        cls.configuration_complete = function_body(
            cls.configuration,
            "xhci_configuration_persistent_release_complete_for",
        )
        cls.ready = function_body(
            cls.teardown, "xhci_slot_teardown_enumeration_epoch_ready"
        )
        cls.complete = function_body(
            cls.teardown, "xhci_slot_teardown_enumeration_dma_complete_for"
        )
        cls.orchestrate = function_body(
            cls.teardown, "xhci_slot_teardown_release_enumeration_dma_for"
        )

    def test_module_is_part_of_native_graph(self):
        self.assertIn(
            "import kernel::drivers::xhci_slot_teardown::*;", self.main
        )

    def test_dependency_direction_stays_acyclic(self):
        for dependency in (
            "import kernel::drivers::xhci_device_table::*;",
            "import kernel::drivers::xhci_descriptor::*;",
            "import kernel::drivers::xhci_configuration::*;",
            "import kernel::drivers::xhci_hid_teardown::*;",
        ):
            self.assertIn(dependency, self.teardown)
        self.assertNotIn("xhci_slot_teardown", self.descriptor)
        self.assertNotIn("xhci_slot_teardown", self.configuration)
        self.assertNotIn("import kernel::memory::dma::*;", self.teardown)

    def test_low_level_owners_require_exact_detach_epoch(self):
        for body in (self.descriptor_epoch, self.configuration_epoch):
            self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", body)
            self.assertIn(
                "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING",
                body,
            )

    def test_same_epoch_recreation_is_blocked_but_new_epoch_resets_tombstone(self):
        self.assertIn(
            "XHCI_DEVICE_DESCRIPTOR_RELEASED_EPOCHS[index] == epoch",
            self.descriptor_prepare,
        )
        self.assertIn(
            "XHCI_DEVICE_DESCRIPTOR_RELEASED_EPOCHS[index] = 0",
            self.descriptor_prepare,
        )
        self.assertIn(
            "XHCI_CONFIGURATION_RELEASED_EPOCHS[index] == epoch",
            self.configuration_prepare,
        )
        reset = function_body(self.configuration, "xhci_configuration_reset_state")
        self.assertIn("XHCI_CONFIGURATION_RELEASED_EPOCHS[index] = 0", reset)

    def test_descriptor_ownership_order_is_unshare_cpu_release(self):
        unshare = self.descriptor_release.index("dma_unshare_from_device")
        cpu = self.descriptor_release.index("dma_buffer_cpu_owned", unshare)
        release = self.descriptor_release.index("dma_release", cpu)
        self.assertLess(unshare, cpu)
        self.assertLess(cpu, release)

    def test_configuration_ownership_order_is_unshare_cpu_release(self):
        unshare = self.configuration_release.index("dma_unshare_from_device")
        cpu = self.configuration_release.index("dma_buffer_cpu_owned", unshare)
        release = self.configuration_release.index("dma_release", cpu)
        self.assertLess(unshare, cpu)
        self.assertLess(cpu, release)

    def test_owner_release_is_retry_safe_across_partial_progress(self):
        for body, started in (
            (
                self.descriptor_release,
                "XHCI_DEVICE_DESCRIPTOR_RELEASE_STARTED_EPOCHS[index]",
            ),
            (
                self.configuration_release,
                "XHCI_CONFIGURATION_RELEASE_STARTED_EPOCHS[index]",
            ),
        ):
            self.assertIn(started, body)
            self.assertIn(".buffer.valid", body)
            self.assertIn("if shared", body)
            self.assertIn("dma_release", body)
        self.assertIn(
            "XHCI_DEVICE_DESCRIPTOR_RELEASE_STARTED_EPOCHS[index] == epoch",
            self.descriptor_complete,
        )
        self.assertIn(
            "XHCI_CONFIGURATION_RELEASE_STARTED_EPOCHS[index] == epoch",
            self.configuration_complete,
        )

    def test_upper_gate_requires_endpoint_teardown_completion(self):
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", self.ready)
        self.assertIn(
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING",
            self.ready,
        )
        self.assertIn(
            "xhci_hid_teardown_endpoint_complete_for(slot_id, epoch)", self.ready
        )
        gate = self.orchestrate.index(
            "xhci_slot_teardown_enumeration_epoch_ready(slot_id, epoch)"
        )
        configuration = self.orchestrate.index(
            "xhci_configuration_release_persistent_for_epoch"
        )
        self.assertLess(gate, configuration)

    def test_configuration_is_released_before_device_descriptor(self):
        configuration = self.orchestrate.index(
            "xhci_configuration_release_persistent_for_epoch"
        )
        configuration_proof = self.orchestrate.index(
            "xhci_configuration_persistent_release_complete_for",
            configuration,
        )
        descriptor = self.orchestrate.index(
            "xhci_device_descriptor_release_persistent_for_epoch",
            configuration_proof,
        )
        descriptor_proof = self.orchestrate.index(
            "xhci_device_descriptor_persistent_release_complete_for",
            descriptor,
        )
        self.assertLess(configuration, configuration_proof)
        self.assertLess(configuration_proof, descriptor)
        self.assertLess(descriptor, descriptor_proof)

    def test_paired_release_is_irq_safe_and_serialized(self):
        self.assertIn("x86_irq_save_disable", self.teardown)
        self.assertIn(
            "spinlock_lock(&mut XHCI_SLOT_ENUMERATION_DMA_TEARDOWN_LOCK)",
            self.teardown,
        )
        self.assertIn(
            "spinlock_unlock(&mut XHCI_SLOT_ENUMERATION_DMA_TEARDOWN_LOCK)",
            self.teardown,
        )
        self.assertIn("xhci_slot_teardown_lock_irq()", self.orchestrate)
        self.assertIn("xhci_slot_teardown_unlock_irq(flags)", self.orchestrate)

    def test_completion_rechecks_both_owner_tombstones(self):
        self.assertIn(
            "xhci_slot_teardown_enumeration_epoch_ready(slot_id, epoch)",
            self.complete,
        )
        self.assertIn(
            "xhci_configuration_persistent_release_complete_for(slot_id, epoch)",
            self.complete,
        )
        self.assertIn(
            "xhci_device_descriptor_persistent_release_complete_for(slot_id, epoch)",
            self.complete,
        )

    def test_4d4a1_does_not_cross_disable_slot_or_context_boundary(self):
        forbidden = (
            "xhci_trb_disable_slot",
            "XHCI_TRB_TYPE_DISABLE_SLOT",
            "xhci_device_table_release",
            "xhci_context_release",
            "DCBAA",
            "dcbaa",
            "xhci_command_execute",
            "xhci_event_consumer",
            "ERDP",
        )
        for token in forbidden:
            self.assertNotIn(token, self.orchestrate)
            self.assertNotIn(token, self.complete)

    def test_low_level_release_has_single_external_sotlas_caller(self):
        driver_dir = ROOT / "kernel/src/drivers"
        sources = {
            path.name: path.read_text(encoding="utf-8")
            for path in driver_dir.glob("*.sotlas")
        }
        for symbol in (
            "xhci_configuration_release_persistent_for_epoch",
            "xhci_device_descriptor_release_persistent_for_epoch",
        ):
            callers = []
            for name, text in sources.items():
                count = text.count(symbol)
                if count:
                    callers.extend([name] * count)
            self.assertEqual(
                sorted(set(callers)),
                sorted([
                    "xhci_configuration.sotlas"
                    if "configuration" in symbol
                    else "xhci_descriptor.sotlas",
                    "xhci_slot_teardown.sotlas",
                ]),
            )


if __name__ == "__main__":
    unittest.main()
