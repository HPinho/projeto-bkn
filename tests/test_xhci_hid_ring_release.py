#!/usr/bin/env python3
"""Guardrails HID-4d.3c2: release seguro do HID Transfer Ring."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "kernel/src/drivers/xhci_hid_context.sotlas"
LIFECYCLE = ROOT / "kernel/src/drivers/xhci_hid_lifecycle.sotlas"
CONFIGURE = ROOT / "kernel/src/drivers/xhci_configure_endpoint.sotlas"


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


class XhciHidRingReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context_text = CONTEXT.read_text(encoding="utf-8")
        cls.lifecycle_text = LIFECYCLE.read_text(encoding="utf-8")
        cls.configure_text = CONFIGURE.read_text(encoding="utf-8")
        cls.release = function_body(
            cls.context_text, "xhci_hid_context_release_ring_for_epoch"
        )
        cls.complete = function_body(
            cls.context_text, "xhci_hid_context_ring_release_complete_for"
        )
        cls.lifecycle_release = function_body(
            cls.lifecycle_text, "xhci_hid_lifecycle_release_transfer_ring_for"
        )

    def test_dependency_direction_remains_acyclic(self):
        self.assertNotIn(
            "import kernel::drivers::xhci_configure_endpoint::*;",
            self.context_text,
        )
        self.assertIn(
            "import kernel::drivers::xhci_configure_endpoint::*;",
            self.lifecycle_text,
        )
        self.assertNotIn(
            "import kernel::drivers::xhci_hid_lifecycle::*;",
            self.configure_text,
        )

    def test_low_level_release_is_exact_epoch(self):
        self.assertIn("xhci_hid_context_epoch_matches(slot_id, epoch)", self.release)
        epoch_match = function_body(self.context_text, "xhci_hid_context_epoch_matches")
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", epoch_match)
        self.assertIn("XHCI_HID_CONTEXTS[index].epoch == epoch", epoch_match)

    def test_release_ownership_order_is_shared_unshare_cpu_free(self):
        shared = self.release.index("dma_buffer_shared")
        unshare = self.release.index("dma_unshare_from_device")
        cpu_owned = self.release.index("dma_buffer_cpu_owned", unshare)
        release = self.release.index("dma_release", cpu_owned)
        self.assertLess(shared, unshare)
        self.assertLess(unshare, cpu_owned)
        self.assertLess(cpu_owned, release)
        self.assertIn("if !shared && !cpu_owned { return false; }", self.release)
        self.assertIn("if shared {", self.release)

    def test_partial_unshare_is_retry_safe(self):
        self.assertIn("cpu_owned = dma_buffer_cpu_owned", self.release)
        self.assertIn("if shared {", self.release)
        self.assertIn("if !dma_buffer_cpu_owned", self.release)
        self.assertIn("if !dma_release", self.release)

    def test_success_publishes_released_tombstone(self):
        release_call = self.release.index("dma_release")
        ready_false = self.release.index("XHCI_HID_CONTEXTS[index].ready = false", release_call)
        ring_zero = self.release.index("XHCI_HID_CONTEXTS[index].ring_physical = 0", release_call)
        self.assertLess(release_call, ready_false)
        self.assertLess(ready_false, ring_zero)
        self.assertIn("!XHCI_HID_CONTEXTS[index].ready", self.complete)
        self.assertIn("XHCI_HID_CONTEXTS[index].ring_physical == 0", self.complete)
        self.assertIn("!XHCI_HID_CONTEXTS[index].ring.valid", self.complete)

    def test_same_epoch_cannot_recreate_released_ring(self):
        prepare = function_body(self.context_text, "xhci_hid_context_prepare_for_slot")
        self.assertIn("XHCI_HID_CONTEXTS[index].epoch == epoch", prepare)
        self.assertIn("XHCI_HID_CONTEXTS[index].ring_physical == 0", prepare)
        self.assertIn("!XHCI_HID_CONTEXTS[index].ring.valid", prepare)

    def test_lifecycle_requires_logical_and_drop_completion_before_release(self):
        logical = self.lifecycle_release.index(
            "xhci_hid_lifecycle_logical_teardown_complete_for(slot_id, epoch)"
        )
        dropped = self.lifecycle_release.index(
            "xhci_configure_endpoint_drop_complete_for(slot_id, epoch)"
        )
        release = self.lifecycle_release.index(
            "xhci_hid_context_release_ring_for_epoch(slot_id, epoch)"
        )
        self.assertLess(logical, dropped)
        self.assertLess(dropped, release)
        self.assertNotIn("xhci_configure_endpoint_drop_hid_for_slot", self.lifecycle_release)

    def test_release_runs_under_existing_smp_teardown_lock(self):
        lock = self.lifecycle_release.index("xhci_hid_lifecycle_teardown_lock_irq()")
        release = self.lifecycle_release.index("xhci_hid_context_release_ring_for_epoch")
        unlock = self.lifecycle_release.index("xhci_hid_lifecycle_teardown_unlock_irq(flags)")
        self.assertLess(lock, release)
        self.assertLess(release, unlock)

    def test_3c2_does_not_cross_slot_context_boundary(self):
        lowered = (self.release + self.lifecycle_release).lower()
        for forbidden in (
            "xhci_trb_disable_slot",
            "xhci_device_table_release",
            "dcbaa",
            "xhci_context_release",
            "xhci_ep0_release",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_low_level_release_has_only_lifecycle_as_external_caller(self):
        symbol = "xhci_hid_context_release_ring_for_epoch("
        callers = []
        for path in (ROOT / "kernel/src").rglob("*.sotlas"):
            if symbol in path.read_text(encoding="utf-8"):
                callers.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(
            sorted(callers),
            sorted(
                [
                    "kernel/src/drivers/xhci_hid_context.sotlas",
                    "kernel/src/drivers/xhci_hid_lifecycle.sotlas",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
