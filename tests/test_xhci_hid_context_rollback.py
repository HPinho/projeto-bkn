#!/usr/bin/env python3
"""Guardrails para rollback do prepare do HID Transfer Ring xHCI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID = ROOT / "kernel/src/drivers/xhci_hid_context.sotlas"
DMA = ROOT / "kernel/src/memory/dma.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_hid_dual.yml"


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


class XhciHidContextRollbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = HID.read_text(encoding="utf-8")
        cls.dma = DMA.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.prepare = function_body(cls.text, "xhci_hid_context_prepare_for_slot")
        cls.release = function_body(
            cls.text, "xhci_hid_context_release_unpublished_ring"
        )
        cls.restore = function_body(
            cls.text, "xhci_hid_context_restore_input_snapshot"
        )
        cls.rollback = function_body(
            cls.text, "xhci_hid_context_rollback_prepare"
        )
        cls.share = function_body(cls.dma, "dma_share_with_device")

    def test_cr3_is_validated_before_allocating_ring(self):
        cr3 = self.prepare.index("x86_read_cr3_raw() == 0")
        alloc = self.prepare.index("dma_alloc(XHCI_HID_RING_SIZE")
        self.assertLess(cr3, alloc)

    def test_input_context_is_snapshotted_before_dma_allocation(self):
        snapshot = self.prepare.index("let old_drop_flags")
        dequeue = self.prepare.index("let old_ep_dequeue")
        alloc = self.prepare.index("dma_alloc(XHCI_HID_RING_SIZE")
        self.assertLess(snapshot, alloc)
        self.assertLess(dequeue, alloc)
        for token in (
            "old_drop_flags",
            "old_add_flags",
            "old_slot_dw0",
            "old_ep_dw0",
            "old_ep_dw1",
            "old_ep_dequeue",
            "old_ep_dw4",
        ):
            self.assertIn(token, self.prepare)

    def test_unpublished_release_accepts_only_cpu_owned_dma(self):
        self.assertIn("if !rollback.valid { return true; }", self.release)
        cpu = self.release.index("dma_buffer_cpu_owned(&rollback)")
        free = self.release.index("dma_release(&mut rollback)")
        self.assertLess(cpu, free)
        self.assertNotIn("dma_unshare_from_device", self.release)
        self.assertNotIn("pmm_free", self.release)

    def test_rollback_restores_every_input_context_field_before_release(self):
        for token in (
            "xhci_hid_context_write32(input, 0, drop_flags)",
            "xhci_hid_context_write32(input, 4, add_flags)",
            "xhci_hid_context_write32(input, slot_offset, slot_dw0)",
            "xhci_hid_context_write32(input, endpoint_offset, ep_dw0)",
            "xhci_hid_context_write32(input, endpoint_offset + 4, ep_dw1)",
            "xhci_hid_context_write64(input, endpoint_offset + 8, ep_dequeue)",
            "xhci_hid_context_write32(input, endpoint_offset + 16, ep_dw4)",
        ):
            self.assertIn(token, self.restore)
        restore = self.rollback.index("xhci_hid_context_restore_input_snapshot")
        release = self.rollback.index("xhci_hid_context_release_unpublished_ring")
        self.assertLess(restore, release)

    def test_zero_and_bind_failures_release_the_cpu_owned_ring(self):
        zero = self.prepare.index("!xhci_hid_context_zero")
        zero_release = self.prepare.index(
            "xhci_hid_context_release_unpublished_ring(ring_buffer)", zero
        )
        bind = self.prepare.index("let ring = xhci_ring_bind", zero_release)
        bind_check = self.prepare.index("!xhci_ring_is_ready(&ring)", bind)
        bind_release = self.prepare.index(
            "xhci_hid_context_release_unpublished_ring(ring_buffer)", bind_check
        )
        self.assertLess(zero, zero_release)
        self.assertLess(bind_check, bind_release)

    def test_context_write_and_share_failures_use_snapshot_rollback(self):
        first_write = self.prepare.index("xhci_hid_context_write32(input, drop_flags_offset")
        first_rollback = self.prepare.index("xhci_hid_context_rollback_prepare(", first_write)
        endpoint_write = self.prepare.index("xhci_hid_context_write32(input, endpoint_offset")
        endpoint_rollback = self.prepare.index(
            "xhci_hid_context_rollback_prepare(", endpoint_write
        )
        share = self.prepare.index("!dma_share_with_device(&mut ring_buffer)")
        share_rollback = self.prepare.index("xhci_hid_context_rollback_prepare(", share)
        self.assertLess(first_write, first_rollback)
        self.assertLess(endpoint_write, endpoint_rollback)
        self.assertLess(share, share_rollback)

    def test_share_is_last_fallible_step_before_publication(self):
        share = self.prepare.index("dma_share_with_device(&mut ring_buffer)")
        publish = self.prepare.index("XHCI_HID_CONTEXTS[index].ready = true", share)
        self.assertLess(share, publish)
        tail = self.prepare[share:publish]
        self.assertNotIn("xhci_command", tail)
        self.assertNotIn("xhci_event_consumer", tail)
        self.assertNotIn("dma_alloc", tail)

    def test_dma_share_transitions_only_after_cpu_owned_precondition(self):
        cpu = self.share.index("!dma_buffer_cpu_owned(buffer as *const DmaBuffer)")
        fence = self.share.index("__dma_fence()", cpu)
        owner = self.share.index("DMA_OWNER_SHARED", fence)
        verify = self.share.index("return dma_buffer_shared(buffer as *const DmaBuffer)", owner)
        self.assertLess(cpu, fence)
        self.assertLess(fence, owner)
        self.assertLess(owner, verify)

    def test_hid_workflow_executes_the_new_guardrail(self):
        self.assertIn(
            "python3 tests/test_xhci_hid_context_rollback.py", self.workflow
        )


if __name__ == "__main__":
    unittest.main()
