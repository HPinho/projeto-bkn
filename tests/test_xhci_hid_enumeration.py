#!/usr/bin/env python3
"""Guardrails HID-4c.4c: pipeline xHCI/HID explícito por porta e Slot ID."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENUM = ROOT / "kernel/src/drivers/xhci_hid_enumeration.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class XhciHidEnumerationTests(unittest.TestCase):
    def test_module_is_in_canonical_graph_but_not_legacy_post_cutover(self):
        main = MAIN.read_text(encoding="utf-8")
        post = POST.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_hid_enumeration::*;", main)
        self.assertNotIn("xhci_hid_enumerate_port(", post)
        self.assertNotIn("xhci_hid_enumerate_next_connected(", post)

    def test_pipeline_stages_explicit_port_then_enables_one_slot(self):
        text = ENUM.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_enumerate_port(port_id: u8) -> u8", 1)[1]
        body = body.split("pub fn xhci_hid_enumerate_next_connected", 1)[0]
        stage = body.index("xhci_port_stage_prepare_for(port_id)")
        slot_type = body.index("let slot_type = xhci_port_stage_slot_type()")
        enable = body.index("xhci_slot_enable_port(port_id, slot_type)")
        epoch = body.index("let epoch = xhci_device_table_slot_epoch(slot_id)")
        self.assertLess(stage, slot_type)
        self.assertLess(slot_type, enable)
        self.assertLess(enable, epoch)
        self.assertIn("xhci_device_table_find_slot_for_port(port_id) != 0", body)
        self.assertIn("xhci_device_table_port_id(slot_id) != port_id", body)

    def test_pipeline_propagates_same_slot_through_certified_per_slot_chain(self):
        text = ENUM.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_enumerate_port(port_id: u8) -> u8", 1)[1]
        body = body.split("pub fn xhci_hid_enumerate_next_connected", 1)[0]
        required = (
            "xhci_context_prepare_for_slot(slot_id)",
            "xhci_address_slot(slot_id)",
            "xhci_ep0_prepare_for_slot(slot_id)",
            "xhci_probe_device_descriptor_8_for_slot(slot_id)",
            "xhci_reconcile_ep0_from_descriptor_probe_for_slot(slot_id)",
            "xhci_get_device_descriptor_for_slot(slot_id)",
            "xhci_probe_configuration_header_for_slot(slot_id)",
            "xhci_read_configuration_full_for_slot(slot_id)",
            "xhci_get_hid_configuration_for_slot(slot_id)",
            "xhci_hid_endpoint_address_for(slot_id)",
            "xhci_hid_endpoint_max_packet_for(slot_id)",
            "xhci_hid_endpoint_interval_for(slot_id)",
            "xhci_hid_context_prepare_for_slot(",
            "xhci_configure_hid_endpoint_for_slot(slot_id)",
            "xhci_set_configuration_for_slot(slot_id)",
            "xhci_hid_report_prepare_for_slot(slot_id)",
            "xhci_hid_enumeration_is_ready_for(slot_id)",
        )
        positions = [body.index(item) for item in required]
        self.assertEqual(positions, sorted(positions))

    def test_pipeline_does_not_fall_back_to_legacy_first_device_wrappers(self):
        text = ENUM.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_enumerate_port(port_id: u8) -> u8", 1)[1]
        body = body.split("pub fn xhci_hid_enumerate_next_connected", 1)[0]
        for forbidden in (
            "xhci_port_stage_prepare_first(",
            "xhci_slot_enable_first_port(",
            "xhci_context_prepare_for_enabled_slot(",
            "xhci_address_first_slot(",
            "xhci_ep0_prepare_after_address(",
            "xhci_probe_first_device_descriptor_8(",
            "xhci_reconcile_ep0_from_descriptor_probe()",
            "xhci_get_first_device_descriptor(",
            "xhci_probe_first_configuration_header(",
            "xhci_read_first_configuration_full(",
            "xhci_get_first_hid_configuration(",
            "xhci_configure_first_hid_endpoint(",
            "xhci_set_first_configuration(",
        ):
            self.assertNotIn(forbidden, body, forbidden)

    def test_ready_gate_requires_full_same_slot_runtime_state(self):
        text = ENUM.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_enumeration_is_ready_for(slot_id: u8)", 1)[1]
        body = body.split("pub fn xhci_hid_enumerate_port", 1)[0]
        for required in (
            "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_HID_READY",
            "xhci_context_is_ready_for(slot_id)",
            "xhci_address_is_ready_for(slot_id)",
            "xhci_ep0_is_ready_for(slot_id)",
            "xhci_device_descriptor_is_ready_for(slot_id)",
            "xhci_configuration_is_ready_for(slot_id)",
            "xhci_hid_context_is_ready_for(slot_id)",
            "xhci_configure_endpoint_is_ready_for(slot_id)",
            "xhci_set_configuration_is_ready_for(slot_id)",
            "xhci_hid_descriptor_is_ready_for(slot_id)",
            "xhci_hid_report_is_ready_for(slot_id)",
        ):
            self.assertIn(required, body)

    def test_failure_path_disables_hardware_and_quarantines_slot(self):
        text = ENUM.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_enumeration_disable_failed_slot", 1)[1]
        body = body.split("fn xhci_hid_enumeration_restore_active", 1)[0]
        failed = body.index(
            "xhci_device_table_set_state(slot_id, epoch, XHCI_DEVICE_STATE_FAILED)"
        )
        disable = body.index("xhci_trb_disable_slot(slot_id, xhci_command_producer_cycle())")
        submit = body.index("xhci_command_submit(command)")
        wait = body.index("xhci_command_wait_completion(command_physical)")
        slot_check = body.index("xhci_command_last_slot_id() != slot_id")
        self.assertLess(failed, disable)
        self.assertLess(disable, submit)
        self.assertLess(submit, wait)
        self.assertLess(wait, slot_check)
        self.assertIn("xhci_hid_descriptor_release_input_device_for_slot(slot_id)", body)
        self.assertNotIn("\n    xhci_device_table_release(", body)
        self.assertIn("quarentena", text)

    def test_next_connected_iteration_is_bounded_and_skips_ports_with_slots(self):
        text = ENUM.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_enumerate_next_connected", 1)[1]
        self.assertIn("xhci_port_scan()", body)
        self.assertIn("while scanned < XHCI_HID_ENUMERATION_SCAN_LIMIT", body)
        self.assertIn("xhci_port_next_connected(cursor)", body)
        self.assertIn("xhci_device_table_find_slot_for_port(port_id) == 0", body)
        self.assertIn("return xhci_hid_enumerate_port(port_id);", body)
        self.assertIn("cursor = port_id;", body)
        self.assertIn("scanned += 1;", body)

    def test_no_fake_multi_device_marker(self):
        text = ENUM.read_text(encoding="utf-8")
        self.assertNotIn("MULTI_DEVICE_READY", text)
        self.assertNotIn("DUAL_DEVICE_READY", text)


if __name__ == "__main__":
    unittest.main()
