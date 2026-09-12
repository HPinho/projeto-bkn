#!/usr/bin/env python3
"""Guardrails HID-4d.5: finalizacao registry + reuse sem segundo Event Ring consumer."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVERS = ROOT / "kernel/src/drivers"
REUSE = DRIVERS / "xhci_slot_reuse.sotlas"
GUARD = DRIVERS / "xhci_slot_reuse_guard.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", match.end())
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
    raise AssertionError(f"unterminated body {name}")


class XhciSlotReuseFinalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reuse = REUSE.read_text(encoding="utf-8")
        cls.guard = GUARD.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")
        cls.preconditions = function_body(cls.reuse, "xhci_slot_reuse_preconditions_for")
        cls.capture = function_body(cls.reuse, "xhci_slot_reuse_capture_for")
        cls.finalize = function_body(cls.reuse, "xhci_slot_reuse_finalize_for")
        cls.complete = function_body(cls.reuse, "xhci_slot_reuse_complete_for")
        cls.guard_release = function_body(cls.guard, "xhci_slot_reuse_guard_release_for")
        cls.guard_release_complete = function_body(
            cls.guard, "xhci_slot_reuse_guard_release_complete_for"
        )

    def test_modules_are_in_native_graph(self):
        self.assertIn("import kernel::drivers::xhci_slot_reuse_guard::*;", self.main)
        self.assertIn("import kernel::drivers::xhci_slot_reuse::*;", self.main)

    def test_preconditions_require_4b_transfer_safe_and_blocked_guard(self):
        for token in (
            "xhci_device_table_slot_epoch(slot_id) != epoch",
            "XHCI_DEVICE_STATE_DETACH_PENDING",
            "xhci_slot_teardown_physical_complete_for(slot_id, epoch)",
            "xhci_transfer_teardown_state_safe_for_epoch(slot_id, epoch)",
            "xhci_slot_reuse_guard_blocked_for(slot_id, epoch)",
        ):
            self.assertIn(token, self.preconditions)

    def test_capture_happens_before_registry_mutation(self):
        self.assertIn("xhci_slot_reuse_preconditions_for(slot_id, epoch)", self.capture)
        self.assertIn("preconditions_captured: true", self.capture)
        self.assertNotIn("xhci_device_table_release", self.capture)
        self.assertNotIn("xhci_slot_reuse_guard_release_for", self.capture)

    def test_registry_is_released_before_reuse_guard(self):
        registry = self.finalize.index("xhci_device_table_release(slot_id, epoch)")
        invalid = self.finalize.index("!xhci_device_table_slot_is_valid(slot_id)", registry)
        guard = self.finalize.index("xhci_slot_reuse_guard_release_for(slot_id, epoch)", invalid)
        guard_proof = self.finalize.index(
            "xhci_slot_reuse_guard_release_complete_for(slot_id, epoch)", guard
        )
        publish = self.finalize.index("complete = true", guard_proof)
        self.assertLess(registry, invalid)
        self.assertLess(invalid, guard)
        self.assertLess(guard, guard_proof)
        self.assertLess(guard_proof, publish)

    def test_reuse_guard_has_exact_release_tombstone(self):
        self.assertIn("XHCI_SLOT_REUSE_BLOCKED_EPOCHS[index] != epoch", self.guard_release)
        self.assertIn("XHCI_SLOT_REUSE_BLOCKED_EPOCHS[index] = 0", self.guard_release)
        self.assertIn("XHCI_SLOT_REUSE_RELEASED_EPOCHS[index] = epoch", self.guard_release)
        self.assertIn("XHCI_SLOT_REUSE_BLOCKED_COUNT -= 1", self.guard_release)
        self.assertIn(
            "XHCI_SLOT_REUSE_RELEASED_EPOCHS[index] == epoch",
            self.guard_release_complete,
        )

    def test_completion_survives_old_device_table_removal(self):
        self.assertNotIn("xhci_device_table_", self.complete)
        self.assertIn("registry_released", self.complete)
        self.assertIn("guard_released", self.complete)
        self.assertIn("complete", self.complete)

    def test_4d5_adds_no_command_or_event_ring_consumer(self):
        forbidden = (
            "xhci_trb_",
            "xhci_command_",
            "xhci_event_consumer",
            "ERDP",
            "erdp",
            "dma_release",
            "dma_unshare_from_device",
        )
        for token in forbidden:
            self.assertNotIn(token, self.reuse)

    def test_guard_release_has_single_upper_driver_caller(self):
        sources = {
            path.name: path.read_text(encoding="utf-8")
            for path in DRIVERS.glob("*.sotlas")
        }
        symbol = "xhci_slot_reuse_guard_release_for"
        callers = sorted(name for name, text in sources.items() if symbol in text)
        self.assertEqual(callers, ["xhci_slot_reuse.sotlas", "xhci_slot_reuse_guard.sotlas"])

    def test_finalizer_is_irq_safe_and_serialized(self):
        self.assertIn("x86_irq_save_disable", self.reuse)
        self.assertIn("spinlock_lock(&mut XHCI_SLOT_REUSE_FINALIZE_LOCK)", self.reuse)
        self.assertIn("spinlock_unlock(&mut XHCI_SLOT_REUSE_FINALIZE_LOCK)", self.reuse)
        self.assertIn("xhci_slot_reuse_lock_irq()", self.finalize)
        self.assertIn("xhci_slot_reuse_unlock_irq(flags)", self.finalize)


if __name__ == "__main__":
    unittest.main()
