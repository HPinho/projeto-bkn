#!/usr/bin/env python3
"""Guardrails HID-4d.4b: Disable Slot + DCBAA + arena de contexts."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVERS = ROOT / "kernel/src/drivers"
CONTEXT = DRIVERS / "xhci_context.sotlas"
SLOT = DRIVERS / "xhci_slot.sotlas"
GUARD = DRIVERS / "xhci_slot_reuse_guard.sotlas"
TEARDOWN = DRIVERS / "xhci_slot_teardown.sotlas"


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


class XhciSlotPhysicalTeardownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = CONTEXT.read_text(encoding="utf-8")
        cls.slot = SLOT.read_text(encoding="utf-8")
        cls.guard = GUARD.read_text(encoding="utf-8")
        cls.teardown = TEARDOWN.read_text(encoding="utf-8")
        cls.capture = function_body(
            cls.teardown, "xhci_slot_teardown_capture_physical_preconditions_for"
        )
        cls.disable_complete = function_body(
            cls.teardown, "xhci_slot_teardown_disable_complete_for"
        )
        cls.physical_complete = function_body(
            cls.teardown, "xhci_slot_teardown_physical_complete_for"
        )
        cls.orchestrate = function_body(
            cls.teardown, "xhci_slot_teardown_disable_and_release_context_for"
        )
        cls.context_release = function_body(
            cls.context, "xhci_context_release_arena_for_epoch"
        )
        cls.context_complete = function_body(
            cls.context, "xhci_context_teardown_complete_for"
        )
        cls.dcbaa_read = function_body(
            cls.context, "xhci_context_dcbaa_slot_value"
        )
        cls.dcbaa_clear = function_body(
            cls.context, "xhci_context_clear_dcbaa_for_epoch"
        )

    def test_context_is_one_three_page_arena(self):
        self.assertIn("pub const XHCI_CONTEXT_ARENA_PAGES: u64 = 3", self.context)
        self.assertIn("pub const XHCI_DEVICE_CONTEXT_PAGE: u64 = 0", self.context)
        self.assertIn("pub const XHCI_INPUT_CONTEXT_PAGE: u64 = 1", self.context)
        self.assertIn("pub const XHCI_EP0_RING_PAGE: u64 = 2", self.context)
        self.assertEqual(self.context_release.count("dma_release"), 1)
        self.assertIn("dma_release(&mut XHCI_CONTEXTS[index].arena)", self.context_release)

    def test_context_release_ownership_order_is_unshare_cpu_release(self):
        unshare = self.context_release.index("dma_unshare_from_device")
        cpu = self.context_release.index("dma_buffer_cpu_owned", unshare)
        release = self.context_release.index("dma_release", cpu)
        self.assertLess(unshare, cpu)
        self.assertLess(cpu, release)

    def test_dcbaa_read_failure_is_not_confused_with_zero(self):
        self.assertIn(
            "pub const XHCI_CONTEXT_DCBAA_INVALID: u64 = 0xFFFFFFFFFFFFFFFF",
            self.context,
        )
        self.assertGreaterEqual(
            self.dcbaa_read.count("return XHCI_CONTEXT_DCBAA_INVALID"), 3
        )
        self.assertIn("observed == XHCI_CONTEXT_DCBAA_INVALID", self.dcbaa_clear)
        self.assertIn("dcbaa_value == XHCI_CONTEXT_DCBAA_INVALID", self.context_complete)

    def test_context_owner_is_exact_detach_epoch_and_blocks_recreation(self):
        match = function_body(self.context, "xhci_context_epoch_matches_detach")
        prepare = function_body(self.context, "xhci_context_prepare_for_slot")
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", match)
        self.assertIn(
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING",
            match,
        )
        self.assertIn(
            "xhci_device_table_state(slot_id) == XHCI_DEVICE_STATE_DETACH_PENDING",
            prepare,
        )
        self.assertIn("XHCI_CONTEXT_RELEASE_STARTED_EPOCHS[index] == epoch", prepare)
        self.assertIn("XHCI_CONTEXT_RELEASED_EPOCHS[index] == epoch", prepare)

    def test_context_release_requires_dcbaa_zero_before_free(self):
        read = self.context_release.index("xhci_context_dcbaa_slot_value")
        invalid = self.context_release.index("XHCI_CONTEXT_DCBAA_INVALID", read)
        release = self.context_release.index("dma_release", invalid)
        self.assertLess(read, invalid)
        self.assertLess(invalid, release)
        self.assertIn("dcbaa_recheck", self.context_release)

    def test_context_completion_is_a_physical_tombstone(self):
        for token in (
            "XHCI_CONTEXT_RELEASE_STARTED_EPOCHS[index] == epoch",
            "XHCI_CONTEXT_RELEASED_EPOCHS[index] == epoch",
            "!XHCI_CONTEXTS[index].ready",
            "!XHCI_CONTEXTS[index].arena.valid",
            "XHCI_CONTEXTS[index].device_physical == 0",
            "XHCI_CONTEXTS[index].input_physical == 0",
            "XHCI_CONTEXTS[index].ep0_ring_physical == 0",
        ):
            self.assertIn(token, self.context_complete)

    def test_reuse_guard_serializes_enable_against_teardown_block(self):
        begin = function_body(self.guard, "xhci_slot_reuse_guard_begin_enable")
        end = function_body(self.guard, "xhci_slot_reuse_guard_end_enable")
        block = function_body(self.guard, "xhci_slot_reuse_guard_block_for")
        self.assertIn("XHCI_SLOT_REUSE_BLOCKED_COUNT != 0", begin)
        self.assertIn("XHCI_SLOT_REUSE_ENABLE_INFLIGHT += 1", begin)
        self.assertIn("XHCI_SLOT_REUSE_ENABLE_INFLIGHT -= 1", end)
        self.assertIn("XHCI_SLOT_REUSE_ENABLE_INFLIGHT != 0", block)
        self.assertIn("XHCI_SLOT_REUSE_BLOCKED_EPOCHS[index] = epoch", block)
        self.assertNotIn("xhci_slot_reuse_guard_release", self.guard)

    def test_enable_slot_is_inside_reuse_guard_transaction(self):
        enable = function_body(self.slot, "xhci_slot_enable_port")
        begin = enable.index("xhci_slot_reuse_guard_begin_enable()")
        command = enable.index("xhci_trb_enable_slot", begin)
        end = enable.index("xhci_slot_reuse_guard_end_enable()", command)
        self.assertLess(begin, command)
        self.assertLess(command, end)

    def test_detach_pending_slot_is_not_operational(self):
        for name in ("xhci_slot_select", "xhci_slot_is_ready_for", "xhci_slot_id"):
            body = function_body(self.slot, name)
            if name == "xhci_slot_select":
                self.assertIn("xhci_slot_is_ready_for(slot_id)", body)
            elif name == "xhci_slot_is_ready_for":
                self.assertIn(
                    "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_DETACH_PENDING",
                    body,
                )
            else:
                self.assertIn("xhci_slot_is_ready_for", body)

    def test_slot_alias_quiesce_keeps_device_table_record(self):
        body = function_body(self.slot, "xhci_slot_quiesce_disabled_for_epoch")
        self.assertIn("XHCI_SLOT_READY = false", body)
        self.assertIn("XHCI_SLOT_ID = 0", body)
        self.assertNotIn("xhci_device_table_release", body)

    def test_4b_captures_4a2_before_destroying_contexts(self):
        self.assertIn(
            "xhci_slot_teardown_logical_state_complete_for(slot_id, epoch)",
            self.capture,
        )
        self.assertIn("preconditions_captured: true", self.capture)
        self.assertNotIn("xhci_context_release_arena_for_epoch", self.capture)

    def test_reuse_guard_blocks_before_disable_attempt(self):
        block = self.orchestrate.index("xhci_slot_reuse_guard_block_for")
        attempted = self.orchestrate.index("disable_attempted = true", block)
        command = self.orchestrate.index("xhci_trb_disable_slot", attempted)
        self.assertLess(block, attempted)
        self.assertLess(attempted, command)

    def test_disable_attempt_is_published_before_command(self):
        attempted = self.orchestrate.index("disable_attempted = true")
        command = self.orchestrate.index("xhci_trb_disable_slot", attempted)
        execute = self.orchestrate.index("xhci_command_execute(command, slot_id)", command)
        complete = self.orchestrate.index("disable_complete = true", execute)
        self.assertLess(attempted, command)
        self.assertLess(command, execute)
        self.assertLess(execute, complete)

    def test_ambiguous_disable_failure_is_not_reissued(self):
        self.assertIn("if attempted", self.orchestrate)
        attempted_branch = self.orchestrate.index("if attempted")
        command = self.orchestrate.index("xhci_trb_disable_slot")
        self.assertLess(attempted_branch, command)
        self.assertIn("disable_attempted", self.disable_complete)
        self.assertIn("disable_complete", self.disable_complete)

    def test_physical_sequence_is_disable_alias_dcbaa_arena_publish(self):
        command = self.orchestrate.index("xhci_trb_disable_slot")
        alias = self.orchestrate.index("xhci_slot_quiesce_disabled_for_epoch", command)
        dcbaa = self.orchestrate.index("xhci_context_clear_dcbaa_for_epoch", alias)
        arena = self.orchestrate.index("xhci_context_release_arena_for_epoch", dcbaa)
        publish = self.orchestrate.index("context_complete = true", arena)
        self.assertLess(command, alias)
        self.assertLess(alias, dcbaa)
        self.assertLess(dcbaa, arena)
        self.assertLess(arena, publish)

    def test_physical_completion_keeps_reuse_guard_blocked(self):
        self.assertIn("xhci_slot_reuse_guard_blocked_for(slot_id, epoch)", self.disable_complete)
        self.assertIn("xhci_slot_reuse_guard_blocked_for(slot_id, epoch)", self.physical_complete)

    def test_completion_does_not_reconsult_destroyed_4a_proofs(self):
        for forbidden in (
            "xhci_slot_teardown_logical_state_complete_for",
            "xhci_hid_teardown_endpoint_complete_for",
            "xhci_configure_endpoint_drop_complete_for",
        ):
            self.assertNotIn(forbidden, self.physical_complete)
        self.assertIn("preconditions_captured", self.physical_complete)
        self.assertIn("xhci_context_teardown_complete_for", self.physical_complete)

    def test_top_level_4b_has_no_raw_dma_or_event_ring_barrier(self):
        self.assertNotIn("import kernel::memory::dma::*;", self.teardown)
        for token in (
            "xhci_device_table_release",
            "xhci_event_consumer",
            "ERDP",
            "erdp",
            "xhci_slot_reuse_guard_release",
        ):
            self.assertNotIn(token, self.teardown)

    def test_lower_owners_do_not_depend_on_slot_teardown(self):
        self.assertNotIn("xhci_slot_teardown", self.context)
        self.assertNotIn("xhci_slot_teardown", self.slot)
        self.assertNotIn("xhci_slot_teardown", self.guard)


if __name__ == "__main__":
    unittest.main()
