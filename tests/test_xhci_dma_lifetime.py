#!/usr/bin/env python3
"""Guardrails HID-4d.3a para lifetime de DMA temporário na enumeração xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = ROOT / "kernel/src/drivers/xhci_descriptor.sotlas"
CONFIGURATION = ROOT / "kernel/src/drivers/xhci_configuration.sotlas"
DMA = ROOT / "kernel/src/memory/dma.sotlas"


class XhciDmaLifetimeTests(unittest.TestCase):
    def test_dma_layer_owns_unshare_and_release_primitives(self):
        text = DMA.read_text(encoding="utf-8")
        self.assertIn("pub fn dma_unshare_from_device(buffer: *mut DmaBuffer)", text)
        self.assertIn("pub fn dma_release(buffer: *mut DmaBuffer)", text)
        self.assertIn("pmm_free_pages_lifo", text)

    def test_device_probe_releases_temporary_dma_after_completed_parse(self):
        text = DESCRIPTOR.read_text(encoding="utf-8")
        helper = text.split("fn xhci_descriptor_release_current_buffer_for_epoch", 1)[1]
        helper = helper.split("fn xhci_descriptor_publish_candidate_buffer", 1)[0]
        self.assertIn("dma_buffer_shared(&XHCI_DEVICE_DESCRIPTOR_STATES[index].buffer)", helper)
        self.assertIn(
            "dma_unshare_from_device(&mut XHCI_DEVICE_DESCRIPTOR_STATES[index].buffer)",
            helper,
        )
        self.assertIn(
            "dma_buffer_cpu_owned(&XHCI_DEVICE_DESCRIPTOR_STATES[index].buffer)", helper
        )
        self.assertIn("dma_release(&mut XHCI_DEVICE_DESCRIPTOR_STATES[index].buffer)", helper)

        body = text.split("pub fn xhci_probe_device_descriptor_8_for_slot", 1)[1]
        body = body.split("pub fn xhci_probe_first_device_descriptor_8", 1)[0]
        publish_owner = body.index("xhci_descriptor_publish_candidate_buffer(slot_id, epoch, buffer)")
        submit = body.index("xhci_ep0_submit_control_td_for_slot", publish_owner)
        wait = body.index("xhci_transfer_wait_ep0_completion", submit)
        parse = body.index("let max_packet0", wait)
        release = body.index(
            "xhci_descriptor_release_current_buffer_for_epoch(slot_id, epoch)", parse
        )
        publish = body.index("probe_ready = true", release)
        self.assertLess(publish_owner, submit)
        self.assertLess(submit, wait)
        self.assertLess(wait, parse)
        self.assertLess(parse, release)
        self.assertLess(release, publish)

        # Submit/wait ambíguos mantêm o owner em quarentena; não pode haver free
        # entre esses retornos e a primeira prova terminal de residual/parse.
        submit_failure = body.index("if status_physical == 0")
        wait_failure = body.index("if !xhci_transfer_wait_ep0_completion", submit_failure)
        residual = body.index("xhci_transfer_last_residual_length_for", wait_failure)
        self.assertNotIn("release_current_buffer", body[submit_failure:wait_failure])
        self.assertNotIn("release_current_buffer", body[wait_failure:residual])

    def test_configuration_header_releases_temporary_dma_before_publish(self):
        text = CONFIGURATION.read_text(encoding="utf-8")
        helper = text.split("fn xhci_configuration_release_temporary", 1)[1]
        helper = helper.split("fn xhci_configuration_fetch_for_slot", 1)[0]
        self.assertIn("dma_buffer_shared(buffer as *const DmaBuffer)", helper)
        self.assertIn("dma_unshare_from_device(buffer)", helper)
        self.assertIn("dma_release(buffer)", helper)

        body = text.split("pub fn xhci_probe_configuration_header_for_slot", 1)[1]
        body = body.split("pub fn xhci_probe_first_configuration_header", 1)[0]
        parse = body.index("let configuration_value")
        release = body.index("xhci_configuration_release_temporary(&mut buffer)", parse)
        publish = body.index("header_ready = true")
        self.assertLess(parse, release)
        self.assertLess(release, publish)
        self.assertNotIn("XHCI_CONFIGURATION_STATES[index].buffer = buffer", body)

    def test_persistent_full_descriptor_and_configuration_remain_owned_by_state(self):
        descriptor = DESCRIPTOR.read_text(encoding="utf-8")
        publish_helper = descriptor.split("fn xhci_descriptor_publish_candidate_buffer", 1)[1]
        publish_helper = publish_helper.split("fn xhci_descriptor_read8", 1)[0]
        self.assertIn("XHCI_DEVICE_DESCRIPTOR_STATES[index].buffer = buffer", publish_helper)

        full_device = descriptor.split("pub fn xhci_get_device_descriptor_for_slot", 1)[1]
        full_device = full_device.split("pub fn xhci_get_first_device_descriptor", 1)[0]
        owner_publish = full_device.index(
            "xhci_descriptor_publish_candidate_buffer(slot_id, epoch, buffer)"
        )
        submit = full_device.index("xhci_ep0_submit_control_td_for_slot", owner_publish)
        ready = full_device.index("XHCI_DEVICE_DESCRIPTOR_STATES[index].ready = true", submit)
        self.assertLess(owner_publish, submit)
        self.assertLess(submit, ready)
        self.assertNotIn("release_current_buffer", full_device[ready:])

        configuration = CONFIGURATION.read_text(encoding="utf-8")
        full_config = configuration.split("pub fn xhci_read_configuration_full_for_slot", 1)[1]
        full_config = full_config.split("pub fn xhci_read_first_configuration_full", 1)[0]
        self.assertIn("XHCI_CONFIGURATION_STATES[index].buffer = buffer", full_config)
        self.assertNotIn("xhci_configuration_release_temporary(&mut buffer)", full_config)

    def test_drivers_do_not_bypass_dma_release_with_direct_pmm_free(self):
        for path in (DESCRIPTOR, CONFIGURATION):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("pmm_free_pages_lifo", text)
            self.assertNotIn("pmm_free_pages(", text)


if __name__ == "__main__":
    unittest.main()
