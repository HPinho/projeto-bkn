#!/usr/bin/env python3
"""Guardrails para prepare transacional do HID Report DMA xHCI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID_REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"


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


class XhciHidReportPrepareRollbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = HID_REPORT.read_text(encoding="utf-8")
        cls.prepare = function_body(cls.text, "xhci_hid_report_prepare_for_slot")
        cls.release = function_body(
            cls.text, "xhci_hid_report_release_unpublished_buffer"
        )

    def test_unpublished_candidate_release_is_cpu_owned_only(self):
        self.assertIn("if !rollback.valid { return true; }", self.release)
        cpu = self.release.index("dma_buffer_cpu_owned(&rollback)")
        release = self.release.index("dma_release(&mut rollback)")
        self.assertLess(cpu, release)
        self.assertNotIn("dma_unshare_from_device", self.release)
        self.assertNotIn("pmm_free", self.release)

    def test_prepare_rejects_old_published_or_quarantined_owner_before_alloc(self):
        alloc = self.prepare.index("dma_alloc(XHCI_HID_REPORT_DMA_SIZE")
        same_epoch = self.prepare.index(
            "XHCI_HID_REPORT_STATES[state_index].epoch == epoch"
        )
        stale_ready = self.prepare.index(
            "if XHCI_HID_REPORT_STATES[state_index].ready { return false; }",
            same_epoch,
        )
        stale_buffer = self.prepare.index(
            "if XHCI_HID_REPORT_STATES[state_index].buffer.valid { return false; }",
            stale_ready,
        )
        self.assertLess(same_epoch, stale_ready)
        self.assertLess(stale_ready, stale_buffer)
        self.assertLess(stale_buffer, alloc)

    def test_zero_and_share_failures_rollback_only_unpublished_candidate(self):
        alloc = self.prepare.index("dma_alloc(XHCI_HID_REPORT_DMA_SIZE")
        zero = self.prepare.index("xhci_hid_report_zero", alloc)
        zero_release = self.prepare.index(
            "xhci_hid_report_release_unpublished_buffer(buffer)", zero
        )
        share = self.prepare.index("dma_share_with_device(&mut buffer)", zero_release)
        share_release = self.prepare.index(
            "xhci_hid_report_release_unpublished_buffer(buffer)", share
        )
        publish = self.prepare.index("XHCI_HID_REPORT_STATES[state_index].epoch = epoch")
        self.assertLess(alloc, zero)
        self.assertLess(zero, zero_release)
        self.assertLess(zero_release, share)
        self.assertLess(share, share_release)
        self.assertLess(share_release, publish)
        self.assertNotIn("dma_unshare_from_device", self.prepare)

    def test_ready_true_is_final_record_publication(self):
        epoch = self.prepare.index("XHCI_HID_REPORT_STATES[state_index].epoch = epoch")
        buffer = self.prepare.index("XHCI_HID_REPORT_STATES[state_index].buffer = buffer")
        active = self.prepare.index("XHCI_HID_REPORT_ACTIVE_SLOT_ID = slot_id", buffer)
        ready = self.prepare.index("XHCI_HID_REPORT_STATES[state_index].ready = true")
        self.assertLess(epoch, buffer)
        self.assertLess(buffer, active)
        self.assertLess(active, ready)
        self.assertEqual(
            self.prepare.count("XHCI_HID_REPORT_STATES[state_index].ready = true"), 1
        )
        tail = self.prepare[ready:]
        self.assertNotIn("XHCI_HID_REPORT_STATES[state_index].epoch =", tail)
        self.assertNotIn("XHCI_HID_REPORT_STATES[state_index].buffer =", tail)
        self.assertNotIn("XHCI_HID_REPORT_ACTIVE_SLOT_ID =", tail)


if __name__ == "__main__":
    unittest.main()
