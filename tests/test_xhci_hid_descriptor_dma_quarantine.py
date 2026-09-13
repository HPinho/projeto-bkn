#!/usr/bin/env python3
"""Guardrails: HID Report Descriptor DMA ownership em falhas de enumeração."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "kernel/src/drivers/xhci_hid_descriptor.sotlas"


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


class XhciHidDescriptorDmaQuarantineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SOURCE.read_text(encoding="utf-8")
        cls.reset = function_body(cls.text, "xhci_hid_descriptor_reset_for_slot")
        cls.prepare = function_body(cls.text, "xhci_hid_descriptor_prepare_state")
        cls.release_temp = function_body(
            cls.text, "xhci_hid_descriptor_release_temporary"
        )
        cls.publish = function_body(
            cls.text, "xhci_hid_descriptor_publish_candidate_buffer"
        )
        cls.fetch = function_body(cls.text, "xhci_hid_descriptor_fetch_for_slot")
        cls.probe = function_body(
            cls.text, "xhci_hid_descriptor_probe_internal_for_slot"
        )
        cls.initialize = function_body(
            cls.text, "xhci_hid_descriptor_initialize_for_slot"
        )

    def test_reset_never_overwrites_a_live_dma_owner(self):
        valid = self.reset.index("XHCI_HID_DESCRIPTOR_STATES[index].buffer.valid")
        release_identity = self.reset.index(
            "xhci_hid_descriptor_release_input_device_for_slot(slot_id)"
        )
        overwrite = self.reset.index(
            "XHCI_HID_DESCRIPTOR_STATES[index].buffer = dma_invalid_buffer()"
        )
        self.assertLess(valid, release_identity)
        self.assertLess(valid, overwrite)
        self.assertIn("if XHCI_HID_DESCRIPTOR_STATES[index].buffer.valid { return false; }", self.reset)

    def test_epoch_rollover_fails_closed_with_old_buffer(self):
        self.assertIn("XHCI_HID_DESCRIPTOR_STATES[index].epoch != epoch", self.prepare)
        self.assertIn("XHCI_HID_DESCRIPTOR_STATES[index].buffer.valid", self.prepare)
        self.assertIn("return xhci_hid_descriptor_reset_for_slot(slot_id, epoch)", self.prepare)

    def test_unpublished_candidate_can_only_be_released_before_submit(self):
        self.assertIn("dma_buffer_shared", self.release_temp)
        self.assertIn("dma_unshare_from_device", self.release_temp)
        self.assertIn("dma_buffer_cpu_owned", self.release_temp)
        self.assertIn("dma_release", self.release_temp)

    def test_owner_is_published_before_ep0_fetch(self):
        share = self.probe.index("dma_share_with_device(&mut buffer)")
        publish = self.probe.index(
            "xhci_hid_descriptor_publish_candidate_buffer(slot_id, epoch, buffer)"
        )
        fetch = self.probe.index("xhci_hid_descriptor_fetch_for_slot(")
        attach = self.probe.index("xhci_hid_attach_input_device_for_slot")
        self.assertLess(share, publish)
        self.assertLess(publish, fetch)
        self.assertLess(fetch, attach)

    def test_publish_requires_shared_current_epoch_and_empty_owner(self):
        self.assertIn("xhci_hid_descriptor_current_buffer_epoch_matches", self.publish)
        self.assertIn("dma_buffer_shared(&buffer)", self.publish)
        self.assertIn("XHCI_HID_DESCRIPTOR_STATES[index].buffer.valid", self.publish)
        self.assertIn("XHCI_HID_DESCRIPTOR_STATES[index].buffer = buffer", self.publish)

    def test_fetch_proves_canonical_owner_before_submit(self):
        owner = self.fetch.index("XHCI_HID_DESCRIPTOR_STATES[index].buffer.valid")
        same_dma = self.fetch.index(
            "XHCI_HID_DESCRIPTOR_STATES[index].buffer.physical_address != (*buffer).physical_address"
        )
        shared = self.fetch.index(
            "dma_buffer_shared(&XHCI_HID_DESCRIPTOR_STATES[index].buffer)"
        )
        submit = self.fetch.index("xhci_ep0_submit_control_td_for_slot(")
        self.assertLess(owner, same_dma)
        self.assertLess(same_dma, shared)
        self.assertLess(shared, submit)

    def test_ambiguous_submit_or_wait_never_frees_dma(self):
        self.assertIn("if status_physical == 0 { return false; }", self.fetch)
        self.assertIn(
            "if !xhci_transfer_wait_ep0_completion(slot_id, status_physical) { return false; }",
            self.fetch,
        )
        self.assertNotIn("dma_release", self.fetch)
        self.assertNotIn("dma_unshare_from_device", self.fetch)
        self.assertNotIn("xhci_hid_descriptor_release_temporary", self.fetch)

    def test_prepublication_failures_release_candidate(self):
        zero = self.probe.index("xhci_hid_descriptor_zero")
        first_release = self.probe.index("xhci_hid_descriptor_release_temporary")
        share = self.probe.index("dma_share_with_device(&mut buffer)")
        publish = self.probe.index("xhci_hid_descriptor_publish_candidate_buffer")
        self.assertLess(zero, first_release)
        self.assertLess(first_release, share)
        self.assertLess(share, publish)
        post_publish = self.probe[publish:]
        self.assertNotIn("xhci_hid_descriptor_release_temporary", post_publish)

    def test_successful_descriptor_initialization_is_retry_idempotent(self):
        ready = self.initialize.index("xhci_hid_descriptor_is_ready_for(slot_id)")
        reset = self.initialize.index("xhci_hid_descriptor_reset_for_slot(slot_id, epoch)")
        self.assertLess(ready, reset)

    def test_no_new_event_or_command_ring_owner(self):
        forbidden = (
            "xhci_event_consumer",
            "ERDP",
            "erdp",
            "xhci_command_execute",
            "xhci_command_wait_completion",
        )
        for token in forbidden:
            self.assertNotIn(token, self.text)


if __name__ == "__main__":
    unittest.main()
