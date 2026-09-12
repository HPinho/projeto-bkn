#!/usr/bin/env python3
"""Guardrails para ownership DMA do Device Descriptor durante enumeração xHCI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = ROOT / "kernel/src/drivers/xhci_descriptor.sotlas"
ENUMERATION = ROOT / "kernel/src/drivers/xhci_hid_enumeration.sotlas"


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


class XhciDescriptorDmaOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DESCRIPTOR.read_text(encoding="utf-8")
        cls.enum_text = ENUMERATION.read_text(encoding="utf-8")
        cls.release = function_body(
            cls.text, "xhci_descriptor_release_current_buffer_for_epoch"
        )
        cls.publish = function_body(
            cls.text, "xhci_descriptor_publish_candidate_buffer"
        )
        cls.failed_release = function_body(
            cls.text, "xhci_device_descriptor_release_failed_for_epoch"
        )
        cls.probe = function_body(cls.text, "xhci_probe_device_descriptor_8_for_slot")
        cls.full = function_body(cls.text, "xhci_get_device_descriptor_for_slot")
        cls.enum_fail = function_body(
            cls.enum_text, "xhci_hid_enumeration_disable_failed_slot"
        )

    def test_release_helper_unshares_then_releases_exact_epoch_owner(self):
        self.assertIn("xhci_descriptor_current_buffer_epoch_matches", self.release)
        shared = self.release.index("dma_buffer_shared")
        unshare = self.release.index("dma_unshare_from_device")
        cpu = self.release.index("dma_buffer_cpu_owned")
        release = self.release.index("dma_release")
        self.assertLess(shared, unshare)
        self.assertLess(unshare, cpu)
        self.assertLess(cpu, release)
        self.assertNotIn("pmm_", self.release)

    def test_publish_helper_requires_shared_exact_epoch_empty_owner(self):
        compact = " ".join(self.publish.split())
        self.assertIn("xhci_descriptor_current_buffer_epoch_matches", compact)
        self.assertIn("dma_buffer_shared(&buffer)", compact)
        self.assertIn(
            "if XHCI_DEVICE_DESCRIPTOR_STATES[index].buffer.valid { return false; }",
            compact,
        )
        self.assertIn("XHCI_DEVICE_DESCRIPTOR_STATES[index].buffer = buffer", compact)

    def _assert_candidate_published_before_submit(self, body: str) -> None:
        share = body.index("dma_share_with_device(&mut buffer)")
        publish = body.index("xhci_descriptor_publish_candidate_buffer", share)
        submit = body.index("xhci_ep0_submit_control_td_for_slot", publish)
        self.assertLess(share, publish)
        self.assertLess(publish, submit)

    def test_probe_and_full_publish_candidate_before_ep0_submit(self):
        self._assert_candidate_published_before_submit(self.probe)
        self._assert_candidate_published_before_submit(self.full)

    def _assert_ambiguous_transfer_failures_keep_owner(self, body: str) -> None:
        compact = " ".join(body.split())
        self.assertIn("if status_physical == 0 { return false; }", compact)
        self.assertIn(
            "if !xhci_transfer_wait_ep0_completion(slot_id, status_physical) { return false; }",
            compact,
        )
        status = body.index("if status_physical == 0")
        wait = body.index("if !xhci_transfer_wait_ep0_completion", status)
        residual = body.index("xhci_transfer_last_residual_length_for", wait)
        self.assertNotIn("release_current_buffer", body[status:wait])
        self.assertNotIn("release_current_buffer", body[wait:residual])

    def test_ambiguous_submit_or_wait_failure_never_frees_dma(self):
        self._assert_ambiguous_transfer_failures_keep_owner(self.probe)
        self._assert_ambiguous_transfer_failures_keep_owner(self.full)

    def test_terminal_failures_release_candidate(self):
        for body in (self.probe, self.full):
            compact = " ".join(body.split())
            self.assertIn(
                "xhci_transfer_last_residual_length_for(slot_id) != 0 { "
                "xhci_descriptor_release_current_buffer_for_epoch(slot_id, epoch); return false; }",
                compact,
            )
        self.assertGreaterEqual(
            self.probe.count("xhci_descriptor_release_current_buffer_for_epoch"), 4
        )
        self.assertGreaterEqual(
            self.full.count("xhci_descriptor_release_current_buffer_for_epoch"), 3
        )

    def test_failed_cleanup_requires_failed_exact_epoch(self):
        compact = " ".join(self.failed_release.split())
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", compact)
        self.assertIn(
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_FAILED", compact
        )
        self.assertIn("xhci_descriptor_release_current_buffer_for_epoch", compact)
        self.assertIn("XHCI_DEVICE_DESCRIPTOR_RELEASED_EPOCHS[index] = epoch", compact)

    def test_disable_slot_completion_precedes_failed_dma_release(self):
        mark = self.enum_fail.index("XHCI_DEVICE_STATE_FAILED")
        execute = self.enum_fail.index("xhci_command_execute", mark)
        cleanup = self.enum_fail.index(
            "xhci_device_descriptor_release_failed_for_epoch", execute
        )
        self.assertLess(mark, execute)
        self.assertLess(execute, cleanup)

    def test_successful_full_descriptor_keeps_persistent_owner(self):
        publish = self.full.index("xhci_descriptor_publish_candidate_buffer")
        ready = self.full.index("XHCI_DEVICE_DESCRIPTOR_STATES[index].ready = true", publish)
        self.assertLess(publish, ready)
        self.assertNotIn("release_current_buffer", self.full[ready:])


if __name__ == "__main__":
    unittest.main()
