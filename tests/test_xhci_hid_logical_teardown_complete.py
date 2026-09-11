#!/usr/bin/env python3
"""Guardrails HID-4d.3b para conclusão SMP-safe do teardown lógico generation-safe."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "kernel/src/drivers/xhci_hid_lifecycle.sotlas"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", match.end())
    if brace < 0:
        raise AssertionError(f"missing function body {name}")

    depth = 0
    index = brace
    in_string = False
    escaped = False
    line_comment = False
    block_comment = False
    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 2
                continue
            index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
        index += 1
    raise AssertionError(f"unterminated function {name}")


def ordered_positions(body: str, *tokens: str) -> list[int]:
    positions: list[int] = []
    cursor = 0
    for token in tokens:
        position = body.find(token, cursor)
        if position < 0:
            raise AssertionError(f"missing ordered token: {token}")
        positions.append(position)
        cursor = position + len(token)
    return positions


class XhciHidLogicalTeardownCompleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = LIFECYCLE.read_text(encoding="utf-8")
        cls.publish = function_body(cls.source, "xhci_hid_lifecycle_publish_detach")
        cls.lock = function_body(
            cls.source, "xhci_hid_lifecycle_teardown_lock_irq"
        )
        cls.unlock = function_body(
            cls.source, "xhci_hid_lifecycle_teardown_unlock_irq"
        )
        cls.complete = function_body(
            cls.source, "xhci_hid_lifecycle_complete_logical_teardown_for"
        )
        cls.query = function_body(
            cls.source, "xhci_hid_lifecycle_logical_teardown_complete_for"
        )

    def test_lifecycle_tracks_complete_bit_per_epoch(self):
        self.assertRegex(
            self.source, r"\bpub\s+logical_teardown_complete\s*:\s*bool\s*;"
        )
        self.assertRegex(
            self.source, r"\blogical_teardown_complete\s*:\s*false\b"
        )
        ordered_positions(
            self.publish,
            ".epoch = epoch;",
            ".detach_detected = true;",
            ".endpoint_stopped = false;",
            ".logical_teardown_started = false;",
            ".logical_teardown_complete = false;",
        )

    def test_teardown_has_dedicated_smp_lock_and_irq_save_restore(self):
        self.assertIn("import kernel::sync::spinlock::*;", self.source)
        self.assertRegex(
            self.source,
            r"static\s+mut\s+XHCI_HID_LIFECYCLE_TEARDOWN_LOCK\s*:\s*SpinLock",
        )
        ordered_positions(
            self.lock,
            "x86_irq_save_disable()",
            "spinlock_lock(&mut XHCI_HID_LIFECYCLE_TEARDOWN_LOCK)",
        )
        ordered_positions(
            self.unlock,
            "spinlock_unlock(&mut XHCI_HID_LIFECYCLE_TEARDOWN_LOCK)",
            "x86_irq_restore(flags)",
        )

    def test_orchestrator_locks_before_started_gate_and_any_cleanup(self):
        lock = "xhci_hid_lifecycle_teardown_lock_irq()"
        started = "xhci_hid_lifecycle_logical_teardown_started_for(slot_id, epoch)"
        first_cleanup = "xhci_hid_descriptor_teardown_input_device_for_epoch(slot_id, epoch)"
        lock_pos, started_pos, cleanup_pos = ordered_positions(
            self.complete, lock, started, first_cleanup
        )
        self.assertLess(lock_pos, started_pos)
        self.assertLess(started_pos, cleanup_pos)

    def test_orchestrator_is_idempotent_only_after_exact_started_gate(self):
        started = self.complete.find(
            "xhci_hid_lifecycle_logical_teardown_started_for(slot_id, epoch)"
        )
        already_complete = self.complete.find(
            "already_complete = XHCI_HID_LIFECYCLE_STATES[index].logical_teardown_complete"
        )
        first_cleanup = self.complete.find(
            "xhci_hid_descriptor_teardown_input_device_for_epoch(slot_id, epoch)"
        )
        self.assertGreaterEqual(started, 0)
        self.assertGreater(already_complete, started)
        self.assertGreater(first_cleanup, already_complete)
        self.assertIn("if complete_ok && !already_complete", self.complete)

    def test_orchestrator_enforces_logical_cleanup_order(self):
        ordered_positions(
            self.complete,
            "xhci_hid_descriptor_teardown_input_device_for_epoch(slot_id, epoch)",
            "xhci_hid_descriptor_teardown_dma_for_epoch(slot_id, epoch)",
            "xhci_hid_report_teardown_dma_for_epoch(slot_id, epoch)",
            "xhci_transfer_clear_slot_state_for_epoch(slot_id, epoch)",
            "XHCI_HID_LIFECYCLE_STATES[index].logical_teardown_complete = true;",
        )

    def test_exact_lifecycle_is_revalidated_between_every_subcleanup(self):
        started = "xhci_hid_lifecycle_logical_teardown_started_for(slot_id, epoch)"
        identity = self.complete.find(
            "xhci_hid_descriptor_teardown_input_device_for_epoch(slot_id, epoch)"
        )
        descriptor = self.complete.find(
            "xhci_hid_descriptor_teardown_dma_for_epoch(slot_id, epoch)"
        )
        report = self.complete.find(
            "xhci_hid_report_teardown_dma_for_epoch(slot_id, epoch)"
        )
        transfer = self.complete.find(
            "xhci_transfer_clear_slot_state_for_epoch(slot_id, epoch)"
        )
        final_write = self.complete.rfind(
            "XHCI_HID_LIFECYCLE_STATES[index].logical_teardown_complete = true;"
        )

        after_identity = self.complete.find(started, identity + 1)
        after_descriptor = self.complete.find(started, descriptor + 1)
        after_report = self.complete.find(started, report + 1)
        after_transfer = self.complete.find(started, transfer + 1)

        self.assertGreater(after_identity, identity)
        self.assertLess(after_identity, descriptor)
        self.assertGreater(after_descriptor, descriptor)
        self.assertLess(after_descriptor, report)
        self.assertGreater(after_report, report)
        self.assertLess(after_report, transfer)
        self.assertGreater(after_transfer, transfer)
        self.assertLess(after_transfer, final_write)

    def test_final_quiescence_is_proven_after_transfer_clear(self):
        transfer = self.complete.find(
            "xhci_transfer_clear_slot_state_for_epoch(slot_id, epoch)"
        )
        quiescent = self.complete.find(
            "xhci_hid_lifecycle_quiescent_for(slot_id, epoch)", transfer
        )
        publish_complete = self.complete.rfind(
            "XHCI_HID_LIFECYCLE_STATES[index].logical_teardown_complete = true;"
        )
        self.assertGreater(quiescent, transfer)
        self.assertGreater(publish_complete, quiescent)

    def test_complete_bit_write_revalidates_lifecycle_identity(self):
        write = self.complete.rfind(
            "XHCI_HID_LIFECYCLE_STATES[index].logical_teardown_complete = true;"
        )
        prefix = self.complete[:write]
        for token in (
            "XHCI_HID_LIFECYCLE_STATES[index].valid",
            "XHCI_HID_LIFECYCLE_STATES[index].epoch != epoch",
            "XHCI_HID_LIFECYCLE_STATES[index].detach_detected",
            "XHCI_HID_LIFECYCLE_STATES[index].endpoint_stopped",
            "XHCI_HID_LIFECYCLE_STATES[index].logical_teardown_started",
        ):
            self.assertIn(token, prefix)

    def test_lock_covers_all_cleanup_and_is_released_before_return(self):
        lock = self.complete.find("xhci_hid_lifecycle_teardown_lock_irq()")
        first_cleanup = self.complete.find(
            "xhci_hid_descriptor_teardown_input_device_for_epoch(slot_id, epoch)"
        )
        final_write = self.complete.rfind(
            "XHCI_HID_LIFECYCLE_STATES[index].logical_teardown_complete = true;"
        )
        unlock = self.complete.rfind("xhci_hid_lifecycle_teardown_unlock_irq(flags)")
        final_return = self.complete.rfind("return complete_ok;")
        self.assertGreater(first_cleanup, lock)
        self.assertGreater(final_write, first_cleanup)
        self.assertGreater(unlock, final_write)
        self.assertGreater(final_return, unlock)
        critical = self.complete[first_cleanup:unlock]
        self.assertNotRegex(critical, r"\breturn\b")

    def test_complete_query_is_exact_generation_scoped(self):
        self.assertIn(
            "xhci_hid_lifecycle_logical_teardown_started_for(slot_id, epoch)",
            self.query,
        )
        self.assertIn("XHCI_HID_LIFECYCLE_STATES[index].epoch == epoch", self.query)
        self.assertIn("logical_teardown_complete", self.query)
        self.assertIn("endpoint_stopped", self.query)

    def test_orchestrator_does_not_cross_into_3c_or_4d4_physical_teardown(self):
        for forbidden in (
            "drop_endpoint",
            "disable_slot",
            "xhci_hid_context_release",
            "xhci_context_release",
            "xhci_ep0",
            "dma_release",
            "dma_unshare_from_device",
            "pmm_free",
            "dcbaa",
        ):
            self.assertNotIn(forbidden, self.complete.lower())

    def test_orchestrator_never_uses_slot_only_or_singleton_cleanup(self):
        for forbidden in (
            "xhci_hid_descriptor_release_input_device_for_slot",
            "xhci_hid_report_transfer_pending_for(slot_id)",
            "xhci_transfer_pending_is_ready_for(slot_id)",
            "xhci_hid_report_active_slot_id()",
            "xhci_transfer_active_slot_id()",
        ):
            self.assertNotIn(forbidden, self.complete)


if __name__ == "__main__":
    unittest.main()
