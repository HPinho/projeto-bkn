from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "kernel/src/drivers/xhci_hid_lifecycle.sotlas"
DEVICE_TABLE = ROOT / "kernel/src/drivers/xhci_device_table.sotlas"
REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class XhciHidLifecycleTests(unittest.TestCase):
    def test_lifecycle_is_in_canonical_graph_not_legacy_post_cutover(self):
        main = MAIN.read_text(encoding="utf-8")
        post = POST.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_hid_lifecycle::*;", main)
        self.assertNotIn("xhci_hid_lifecycle_scan_detached(", post)
        self.assertNotIn("xhci_hid_lifecycle_stop_endpoint_for(", post)

    def test_detach_pending_has_dedicated_generation_safe_transition(self):
        text = DEVICE_TABLE.read_text(encoding="utf-8")
        self.assertIn("pub const XHCI_DEVICE_STATE_DETACH_PENDING: u8 = 6", text)
        self.assertIn("pub fn xhci_device_table_mark_detach_pending(slot_id: u8, epoch: u32)", text)
        dedicated = text.split("pub fn xhci_device_table_mark_detach_pending", 1)[1]
        dedicated = dedicated.split("pub fn xhci_device_table_set_active", 1)[0]
        self.assertIn("XHCI_DEVICE_SLOTS[index].epoch != epoch", dedicated)
        self.assertIn("XHCI_DEVICE_SLOTS[index].state = XHCI_DEVICE_STATE_DETACH_PENDING", dedicated)

    def test_detach_detection_is_read_only_and_same_epoch(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_lifecycle_mark_detached_for", 1)[1]
        body = body.split("pub fn xhci_hid_lifecycle_scan_detached", 1)[0]
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", body)
        self.assertIn("xhci_port_snapshot(port_id)", body)
        self.assertIn("(*snapshot).connected", body)
        self.assertIn("xhci_device_table_mark_detach_pending(slot_id, epoch)", body)
        self.assertIn("xhci_hid_lifecycle_publish_detach(slot_id, epoch)", body)

    def test_stop_endpoint_is_generation_safe_and_ordered(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_lifecycle_stop_endpoint_for", 1)[1]
        body = body.split("pub fn xhci_hid_lifecycle_can_finalize_for", 1)[0]
        for token in (
            "xhci_hid_lifecycle_is_detach_pending_for(slot_id, epoch)",
            "XHCI_HID_LIFECYCLE_STATES[index].epoch != epoch",
            "xhci_hid_context_dci_for(slot_id)",
            "xhci_hid_report_transfer_pending_for(slot_id)",
            "xhci_trb_stop_endpoint(",
            "xhci_command_submit(command)",
            "xhci_command_wait_completion(command_physical)",
            "xhci_command_last_slot_id() != slot_id",
            "xhci_hid_report_drain_cancelled_for_slot(slot_id)",
            "XHCI_HID_LIFECYCLE_STATES[index].endpoint_stopped = true",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("xhci_command_submit(command)"), body.index("xhci_command_wait_completion(command_physical)"))
        self.assertLess(body.index("xhci_command_wait_completion(command_physical)"), body.index("xhci_hid_report_drain_cancelled_for_slot(slot_id)"))
        self.assertLess(body.index("xhci_hid_report_drain_cancelled_for_slot(slot_id)"), body.index("XHCI_HID_LIFECYCLE_STATES[index].endpoint_stopped = true"))

    def test_stop_cut_still_does_not_release_slot_or_identity(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        for forbidden in (
            "xhci_trb_disable_slot",
            "xhci_hid_descriptor_release_input_device_for_slot",
            "input_device_detach",
            "xhci_device_table_release(",
        ):
            self.assertNotIn(forbidden, text)

    def test_scan_is_bounded_and_refreshes_port_inventory_once(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_lifecycle_scan_detached()", 1)[1]
        body = body.split("pub fn xhci_hid_lifecycle_endpoint_stopped_for", 1)[0]
        self.assertEqual(body.count("xhci_port_scan()"), 1)
        self.assertIn("while index < XHCI_DEVICE_SLOT_CAPACITY", body)

    def test_report_cancel_drain_does_not_parse_input(self):
        text = REPORT.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_report_drain_cancelled_for_slot", 1)[1]
        body = body.split("pub fn xhci_hid_report_poll_slot_once", 1)[0]
        self.assertIn("XHCI_DEVICE_STATE_DETACH_PENDING", body)
        self.assertIn("xhci_transfer_wait_stopped_or_completed(slot_id, dci, physical)", body)
        self.assertIn("transfer_pending = false", body)
        self.assertIn("pending_trb_physical = 0", body)
        self.assertIn("pending_transfer_length = 0", body)
        self.assertNotIn("xhci_hid_report_parse_for_slot", body)
        self.assertNotIn("hid_input_events_process_report_for_device", body)

    def test_finalize_requires_endpoint_stopped_and_empty_transfer_state(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_lifecycle_can_finalize_for", 1)[1]
        body = body.split("pub fn xhci_hid_lifecycle_last_scan_ok", 1)[0]
        self.assertIn("xhci_hid_lifecycle_endpoint_stopped_for(slot_id, epoch)", body)
        self.assertIn("xhci_hid_report_transfer_pending_for(slot_id)", body)
        self.assertIn("xhci_transfer_pending_is_ready_for(slot_id)", body)


if __name__ == "__main__":
    unittest.main()
