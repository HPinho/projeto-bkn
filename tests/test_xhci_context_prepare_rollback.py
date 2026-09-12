#!/usr/bin/env python3
"""Guardrails para rollback transacional da arena Device/Input/EP0 xHCI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "kernel/src/drivers/xhci_context.sotlas"


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


class XhciContextPrepareRollbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CONTEXT.read_text(encoding="utf-8")
        cls.prepare = function_body(cls.text, "xhci_context_prepare_for_slot")
        cls.restore = function_body(
            cls.text, "xhci_context_restore_dcbaa_after_prepare_failure"
        )
        cls.release = function_body(
            cls.text, "xhci_context_release_unpublished_arena"
        )
        cls.rollback = function_body(
            cls.text, "xhci_context_rollback_published_dcbaa"
        )
        cls.reset = function_body(
            cls.text, "xhci_context_reset_unpublished_record"
        )
        cls.teardown = function_body(
            cls.text, "xhci_context_release_arena_for_epoch"
        )

    def test_prepare_keeps_exact_single_three_page_arena(self):
        self.assertIn("XHCI_CONTEXT_ARENA_PAGES: u64 = 3", self.text)
        self.assertEqual(
            self.prepare.count(
                "dma_alloc(XHCI_CONTEXT_ARENA_PAGES * XHCI_CONTEXT_PAGE_SIZE"
            ),
            1,
        )
        self.assertIn("XHCI_DEVICE_CONTEXT_PAGE", self.prepare)
        self.assertIn("XHCI_INPUT_CONTEXT_PAGE", self.prepare)
        self.assertIn("XHCI_EP0_RING_PAGE", self.prepare)

    def test_cr3_and_zero_dcbaa_are_proved_before_alloc(self):
        cr3 = self.prepare.index("x86_read_cr3_raw() == 0")
        dcbaa = self.prepare.index("xhci_context_dcbaa_slot_value(slot_id)", cr3)
        alloc = self.prepare.index("dma_alloc(XHCI_CONTEXT_ARENA_PAGES")
        self.assertLess(cr3, dcbaa)
        self.assertLess(dcbaa, alloc)
        self.assertIn("dcbaa_before == XHCI_CONTEXT_DCBAA_INVALID", self.prepare)
        self.assertIn("dcbaa_before != 0", self.prepare)

    def test_pre_dcbaa_failures_only_release_cpu_owned_candidate(self):
        self.assertIn("if !rollback.valid { return true; }", self.release)
        cpu = self.release.index("dma_buffer_cpu_owned(&rollback)")
        release = self.release.index("dma_release(&mut rollback)")
        self.assertLess(cpu, release)
        self.assertNotIn("dma_unshare_from_device", self.release)
        self.assertNotIn("pmm_free", self.release)
        write_dcbaa = self.prepare.index("xhci_context_write_dcbaa_slot")
        pre = self.prepare[:write_dcbaa]
        self.assertGreaterEqual(
            pre.count("xhci_context_release_unpublished_arena(arena)"), 5
        )

    def test_post_dcbaa_rollback_clears_pointer_before_unshare_and_release(self):
        restore = self.rollback.index("xhci_context_restore_dcbaa_after_prepare_failure")
        unshare = self.rollback.index("dma_unshare_from_device")
        release = self.rollback.index("dma_release(&mut rollback)")
        self.assertLess(restore, unshare)
        self.assertLess(unshare, release)
        self.assertIn("if observed == 0 { return true; }", self.restore)
        self.assertIn("if observed != device_physical { return false; }", self.restore)
        self.assertIn("*((dcbaa_virtual + offset) as *mut u64) = 0", self.restore)
        self.assertIn("cleared == 0", self.restore)

    def test_dcbaa_write_and_share_failures_use_transactional_rollback(self):
        write = self.prepare.index("xhci_context_write_dcbaa_slot")
        rollback_unshared = self.prepare.index(
            "xhci_context_rollback_published_dcbaa", write
        )
        share = self.prepare.index("dma_share_with_device", rollback_unshared)
        rollback_shared_failure = self.prepare.index(
            "xhci_context_rollback_published_dcbaa", share
        )
        self.assertLess(write, rollback_unshared)
        self.assertLess(rollback_unshared, share)
        self.assertLess(share, rollback_shared_failure)
        self.assertIn("arena, false", self.prepare[rollback_unshared:share])

    def test_record_is_not_ready_until_device_table_transition_succeeds(self):
        publish_not_ready = self.prepare.index("XHCI_CONTEXTS[index].ready = false")
        state = self.prepare.index(
            "xhci_device_table_set_state(slot_id, epoch, XHCI_DEVICE_STATE_CONTEXT_READY)"
        )
        publish_ready = self.prepare.index("XHCI_CONTEXTS[index].ready = true", state)
        self.assertLess(publish_not_ready, state)
        self.assertLess(state, publish_ready)

    def test_state_failure_removes_software_alias_before_dma_rollback(self):
        state = self.prepare.index(
            "xhci_device_table_set_state(slot_id, epoch, XHCI_DEVICE_STATE_CONTEXT_READY)"
        )
        reset = self.prepare.index("xhci_context_reset_unpublished_record", state)
        rollback = self.prepare.index("xhci_context_rollback_published_dcbaa", reset)
        self.assertLess(state, reset)
        self.assertLess(reset, rollback)
        for token in (
            "XHCI_CONTEXTS[index].context_size = 0",
            "XHCI_CONTEXTS[index].arena = dma_invalid_buffer()",
            "XHCI_CONTEXTS[index].device_physical = 0",
            "XHCI_CONTEXTS[index].input_physical = 0",
            "XHCI_CONTEXTS[index].ep0_ring_physical = 0",
            "XHCI_CONTEXTS[index].ep0_max_packet = 0",
        ):
            self.assertIn(token, self.reset)

    def test_existing_4b_teardown_still_has_single_release(self):
        self.assertEqual(self.teardown.count("dma_release"), 1)
        self.assertIn("dma_unshare_from_device", self.teardown)
        self.assertIn("xhci_context_dcbaa_slot_value", self.teardown)

    def test_prepare_rollback_never_owns_event_or_command_ring(self):
        prepare_region = self.text.split(
            "fn xhci_context_restore_dcbaa_after_prepare_failure", 1
        )[1].split("pub fn xhci_context_prepare_for_enabled_slot", 1)[0]
        for forbidden in (
            "xhci_event_consumer",
            "xhci_event_ring",
            "xhci_command_execute",
            "xhci_trb_disable_slot",
        ):
            self.assertNotIn(forbidden, prepare_region)


if __name__ == "__main__":
    unittest.main()
