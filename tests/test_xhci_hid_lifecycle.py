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
        self.assertNotIn("xhci_hid_lifecycle_mark_detached_for(", post)

    def test_detach_pending_has_dedicated_generation_safe_transition(self):
        text = DEVICE_TABLE.read_text(encoding="utf-8")
        self.assertIn("pub const XHCI_DEVICE_STATE_DETACH_PENDING: u8 = 6", text)
        self.assertIn("pub fn xhci_device_table_mark_detach_pending(slot_id: u8, epoch: u32)", text)
        generic = text.split("pub fn xhci_device_table_set_state", 1)[1]
        generic = generic.split("pub fn xhci_device_table_mark_detach_pending", 1)[0]
        self.assertIn("state > XHCI_DEVICE_STATE_FAILED", generic)
        self.assertNotIn("XHCI_DEVICE_STATE_DETACH_PENDING", generic.split("// DETACH_PENDING", 1)[-1])
        dedicated = text.split("pub fn xhci_device_table_mark_detach_pending", 1)[1]
        dedicated = dedicated.split("pub fn xhci_device_table_set_active", 1)[0]
        self.assertIn("XHCI_DEVICE_SLOTS[index].epoch != epoch", dedicated)
        self.assertIn("state != XHCI_DEVICE_STATE_HID_READY", dedicated)
        self.assertIn("state != XHCI_DEVICE_STATE_DETACH_PENDING", dedicated)
        self.assertIn("XHCI_DEVICE_SLOTS[index].state = XHCI_DEVICE_STATE_DETACH_PENDING", dedicated)

    def test_detach_detection_is_read_only_and_same_epoch(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_lifecycle_mark_detached_for", 1)[1]
        body = body.split("pub fn xhci_hid_lifecycle_scan_detached", 1)[0]
        self.assertIn("xhci_device_table_slot_epoch(slot_id) != epoch", body)
        self.assertIn("xhci_device_table_port_id(slot_id)", body)
        self.assertIn("xhci_port_snapshot(port_id)", body)
        self.assertIn("(*snapshot).connected", body)
        self.assertIn("xhci_device_table_mark_detach_pending(slot_id, epoch)", body)

    def test_lifecycle_cut_is_non_destructive(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        for forbidden in (
            "xhci_trb_disable_slot",
            "xhci_command_submit",
            "xhci_hid_descriptor_release_input_device_for_slot",
            "input_device_detach",
            "xhci_device_table_release(",
        ):
            self.assertNotIn(forbidden, text)

    def test_scan_is_bounded_and_refreshes_port_inventory_once(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_lifecycle_scan_detached()", 1)[1]
        body = body.split("pub fn xhci_hid_lifecycle_can_finalize_for", 1)[0]
        self.assertEqual(body.count("xhci_port_scan()"), 1)
        self.assertIn("while index < XHCI_DEVICE_SLOT_CAPACITY", body)
        self.assertIn("XHCI_DEVICE_STATE_HID_READY", body)
        self.assertIn("XHCI_DEVICE_STATE_DETACH_PENDING", body)

    def test_new_prepare_and_submit_stop_after_quarantine_but_complete_can_drain(self):
        text = REPORT.read_text(encoding="utf-8")
        prepare = text.split("pub fn xhci_hid_report_prepare_for_slot", 1)[1]
        prepare = prepare.split("pub fn xhci_hid_report_prepare()", 1)[0]
        submit = text.split("pub fn xhci_hid_report_submit_for_slot", 1)[1]
        submit = submit.split("pub fn xhci_hid_report_complete_for_slot", 1)[0]
        complete = text.split("pub fn xhci_hid_report_complete_for_slot", 1)[1]
        complete = complete.split("pub fn xhci_hid_report_poll_slot_once", 1)[0]
        gate = "xhci_device_table_state(slot_id) != XHCI_DEVICE_STATE_HID_READY"
        self.assertIn(gate, prepare)
        self.assertIn(gate, submit)
        self.assertNotIn(gate, complete)
        self.assertIn("xhci_transfer_wait_completion(slot_id, dci, physical)", complete)

    def test_finalize_gate_requires_no_report_td_and_no_transfer_mailbox(self):
        text = LIFECYCLE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_lifecycle_can_finalize_for", 1)[1]
        body = body.split("pub fn xhci_hid_lifecycle_last_scan_ok", 1)[0]
        self.assertIn("xhci_hid_lifecycle_is_detach_pending_for(slot_id, epoch)", body)
        self.assertIn("xhci_hid_report_transfer_pending_for(slot_id)", body)
        self.assertIn("xhci_transfer_pending_is_ready_for(slot_id)", body)


if __name__ == "__main__":
    unittest.main()
