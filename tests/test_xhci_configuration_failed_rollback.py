#!/usr/bin/env python3
"""Guardrails para ownership/recovery FAILED do Configuration Descriptor xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONF = ROOT / "kernel/src/drivers/xhci_configuration.sotlas"
ENUM = ROOT / "kernel/src/drivers/xhci_hid_enumeration.sotlas"


class XhciConfigurationFailedRollbackTests(unittest.TestCase):
    def setUp(self):
        self.conf = CONF.read_text(encoding="utf-8")
        self.enum = ENUM.read_text(encoding="utf-8")

    def test_epoch_reset_fails_closed_while_old_dma_owner_exists(self):
        reset = self.conf.split("fn xhci_configuration_reset_state", 1)[1]
        reset = reset.split("fn xhci_configuration_prepare_state", 1)[0]
        valid_guard = reset.index("XHCI_CONFIGURATION_STATES[index].buffer.valid")
        epoch_write = reset.index("XHCI_CONFIGURATION_STATES[index].epoch = epoch")
        self.assertLess(valid_guard, epoch_write)
        self.assertIn("if XHCI_CONFIGURATION_STATES[index].buffer.valid { return false; }", reset)

        prepare = self.conf.split("fn xhci_configuration_prepare_state", 1)[1]
        prepare = prepare.split("fn xhci_configuration_state_is_current", 1)[0]
        mismatch = prepare.index("XHCI_CONFIGURATION_STATES[index].epoch != epoch")
        owner_guard = prepare.index("XHCI_CONFIGURATION_STATES[index].buffer.valid", mismatch)
        reset_call = prepare.index("xhci_configuration_reset_state(slot_id, epoch)", owner_guard)
        self.assertLess(mismatch, owner_guard)
        self.assertLess(owner_guard, reset_call)

    def test_header_invalidation_cannot_orphan_published_buffer(self):
        body = self.conf.split("fn xhci_configuration_invalidate_after_header", 1)[1]
        body = body.split("fn xhci_configuration_invalidate_after_full", 1)[0]
        owner_guard = body.index("if XHCI_CONFIGURATION_STATES[index].buffer.valid { return false; }")
        invalidate = body.index("XHCI_CONFIGURATION_STATES[index].full_ready = false")
        self.assertLess(owner_guard, invalidate)

    def test_candidate_is_published_before_header_and_full_fetch(self):
        for start, end in (
            (
                "pub fn xhci_probe_configuration_header_for_slot",
                "pub fn xhci_probe_first_configuration_header",
            ),
            (
                "pub fn xhci_read_configuration_full_for_slot",
                "pub fn xhci_read_first_configuration_full",
            ),
        ):
            body = self.conf.split(start, 1)[1].split(end, 1)[0]
            share = body.index("dma_share_with_device(&mut buffer)")
            publish = body.index("xhci_configuration_publish_candidate_buffer(slot_id, epoch, buffer)")
            fetch = body.index("xhci_configuration_fetch_for_slot", publish)
            self.assertLess(share, publish)
            self.assertLess(publish, fetch)

    def test_ambiguous_submit_and_wait_never_release_published_dma(self):
        body = self.conf.split("fn xhci_configuration_fetch_for_slot", 1)[1]
        body = body.split("pub fn xhci_probe_configuration_header_for_slot", 1)[0]
        submit = body.index("xhci_ep0_submit_control_td_for_slot")
        submit_failure = body.index("if status_physical == 0", submit)
        wait_failure = body.index("if !xhci_transfer_wait_ep0_completion", submit_failure)
        residual = body.index("xhci_transfer_last_residual_length_for", wait_failure)
        self.assertNotIn("dma_unshare_from_device", body[submit:residual])
        self.assertNotIn("dma_release", body[submit:residual])
        self.assertNotIn("release_current_buffer", body[submit_failure:residual])

    def test_terminal_parse_failures_release_only_canonical_epoch_owner(self):
        header = self.conf.split("pub fn xhci_probe_configuration_header_for_slot", 1)[1]
        header = header.split("pub fn xhci_probe_first_configuration_header", 1)[0]
        parse = header.index("let configuration_value")
        release = header.index(
            "xhci_configuration_release_current_buffer_for_epoch(slot_id, epoch)", parse
        )
        self.assertLess(parse, release)

        full = self.conf.split("pub fn xhci_read_configuration_full_for_slot", 1)[1]
        full = full.split("pub fn xhci_read_first_configuration_full", 1)[0]
        validate = full.index("xhci_configuration_read16(base, 2) != total_length")
        release = full.index(
            "xhci_configuration_release_current_buffer_for_epoch(slot_id, epoch)", validate
        )
        self.assertLess(validate, release)

    def test_failed_release_is_exact_epoch_and_retry_safe(self):
        body = self.conf.split("pub fn xhci_configuration_release_failed_for_epoch", 1)[1]
        body = body.split("pub fn xhci_configuration_failed_release_complete_for", 1)[0]
        for token in (
            "xhci_device_table_slot_epoch(slot_id) != epoch",
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_FAILED",
            "xhci_configuration_failed_release_complete_for(slot_id, epoch)",
            "XHCI_CONFIGURATION_RELEASE_STARTED_EPOCHS[index] = epoch",
            "xhci_configuration_release_current_buffer_for_epoch(slot_id, epoch)",
            "XHCI_CONFIGURATION_RELEASED_EPOCHS[index] = epoch",
        ):
            self.assertIn(token, body)

        release = self.conf.split("fn xhci_configuration_release_current_buffer_for_epoch", 1)[1]
        release = release.split("fn xhci_configuration_publish_candidate_buffer", 1)[0]
        unshare = release.index(
            "dma_unshare_from_device(&mut XHCI_CONFIGURATION_STATES[index].buffer)"
        )
        cpu = release.index(
            "dma_buffer_cpu_owned(&XHCI_CONFIGURATION_STATES[index].buffer)", unshare
        )
        free = release.index("dma_release(&mut XHCI_CONFIGURATION_STATES[index].buffer)", cpu)
        self.assertLess(unshare, cpu)
        self.assertLess(cpu, free)

    def test_disable_slot_completion_precedes_configuration_then_device_cleanup(self):
        body = self.enum.split("fn xhci_hid_enumeration_disable_failed_slot", 1)[1]
        body = body.split("fn xhci_hid_enumeration_restore_active", 1)[0]
        disable = body.index("xhci_command_execute(command, slot_id)")
        configuration = body.index(
            "xhci_configuration_release_failed_for_epoch(slot_id, epoch)", disable
        )
        descriptor = body.index(
            "xhci_device_descriptor_release_failed_for_epoch(slot_id, epoch)", configuration
        )
        self.assertLess(disable, configuration)
        self.assertLess(configuration, descriptor)
        self.assertNotIn("xhci_device_table_release", body)

    def test_configuration_recovery_does_not_own_command_or_event_ring_or_pmm(self):
        code = "\n".join(
            line for line in self.conf.splitlines() if not line.lstrip().startswith("//")
        )
        for forbidden in (
            "xhci_command_execute",
            "xhci_command_submit",
            "xhci_event_consumer",
            "xhci_event_ring",
            "pmm_free_pages(",
            "pmm_free_pages_lifo",
        ):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
