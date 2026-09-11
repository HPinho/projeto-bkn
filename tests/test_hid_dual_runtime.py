import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATE = ROOT / "kernel/src/platform/hid_late_attach.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_hid_dual.yml"
TRANSFER = ROOT / "kernel/src/drivers/xhci_transfer.sotlas"
REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"


class HidDualRuntimeContractTests(unittest.TestCase):
    def test_late_attach_uses_certified_per_slot_pipeline(self):
        text = LATE.read_text(encoding="utf-8")
        self.assertIn("pub fn platform_hid_late_attach_second_mouse() -> bool", text)
        self.assertIn("xhci_hid_enumerate_next_connected(0)", text)
        self.assertIn("xhci_hid_enumeration_is_ready_for(second_slot)", text)
        self.assertIn("xhci_hid_protocol_for(first_slot) != USB_HID_PROTOCOL_KEYBOARD", text)
        self.assertIn("xhci_hid_protocol_for(second_slot) != USB_HID_PROTOCOL_MOUSE", text)
        self.assertIn("xhci_slot_active_count() < 2", text)
        self.assertIn("xhci_hid_report_poll_slot_once(second_slot)", text)
        self.assertIn("XHCI_HID_BOOT_MOUSE_MIN_LENGTH", text)

    def test_dual_ready_marker_is_only_after_real_mouse_report(self):
        text = LATE.read_text(encoding="utf-8")
        body = text.split("pub fn platform_hid_late_attach_second_mouse() -> bool", 1)[1]
        body = body.split("pub fn platform_hid_late_attach_is_ready()", 1)[0]
        poll = body.index("xhci_hid_report_poll_slot_once(second_slot)")
        length = body.index("xhci_hid_report_last_length_for(second_slot)")
        marker = body.index("platform_hid_late_attach_emit_ready_marker()", poll)
        publish = body.index("PLATFORM_HID_LATE_ATTACH_READY = true", marker)
        self.assertLess(poll, length)
        self.assertLess(length, marker)
        self.assertLess(marker, publish)

    def test_interleave_arms_both_slots_before_routing_any_completion(self):
        text = LATE.read_text(encoding="utf-8")
        body = text.split("fn platform_hid_late_attach_prove_interleaving", 1)[1]
        body = body.split("pub fn platform_hid_late_attach_second_mouse", 1)[0]
        submit_mouse = body.index("xhci_hid_report_submit_for_slot(second_slot)")
        submit_keyboard = body.index("xhci_hid_report_submit_for_slot(first_slot)")
        route_first = body.index("xhci_transfer_route_next_event()")
        self.assertLess(submit_mouse, route_first)
        self.assertLess(submit_keyboard, route_first)
        self.assertEqual(body.count("xhci_transfer_route_next_event()"), 2)
        self.assertIn("xhci_hid_report_transfer_pending_for(first_slot)", body)
        self.assertIn("xhci_hid_report_transfer_pending_for(second_slot)", body)

    def test_interleave_requires_two_slot_mailboxes_then_completes_each_owner(self):
        text = LATE.read_text(encoding="utf-8")
        body = text.split("fn platform_hid_late_attach_prove_interleaving", 1)[1]
        body = body.split("pub fn platform_hid_late_attach_second_mouse", 1)[0]
        self.assertIn("xhci_transfer_pending_is_ready_for(first_slot)", body)
        self.assertIn("xhci_transfer_pending_is_ready_for(second_slot)", body)
        keyboard_complete = body.index("xhci_hid_report_complete_for_slot(first_slot)")
        mouse_complete = body.index("xhci_hid_report_complete_for_slot(second_slot)")
        marker = body.index("platform_hid_late_attach_emit_interleave_ready_marker()")
        self.assertLess(keyboard_complete, marker)
        self.assertLess(mouse_complete, marker)
        self.assertIn("XHCI_HID_BOOT_KEYBOARD_LENGTH", body)
        self.assertIn("XHCI_HID_BOOT_MOUSE_MIN_LENGTH", body)

    def test_transfer_demux_and_report_split_are_real_runtime_paths(self):
        transfer = TRANSFER.read_text(encoding="utf-8")
        report = REPORT.read_text(encoding="utf-8")
        self.assertIn("XHCI_TRANSFER_PENDING_EVENTS", transfer)
        self.assertIn("pub fn xhci_transfer_route_next_event()", transfer)
        self.assertNotIn("if xhci_event_slot_id(event) != slot_id { return false; }", transfer)
        self.assertIn("pub fn xhci_hid_report_submit_for_slot", report)
        self.assertIn("pub fn xhci_hid_report_complete_for_slot", report)
        self.assertIn("return xhci_hid_report_complete_for_slot(slot_id)", report)

    def test_runtime_hook_is_nonfatal_and_precedes_platform_services(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("import kernel::platform::hid_late_attach::*;", text)
        call = text.index("platform_hid_late_attach_second_mouse();")
        aml = text.index("if !aml_tables_init()")
        self.assertLess(call, aml)
        self.assertNotIn("if !platform_hid_late_attach_second_mouse()", text)

    def test_legacy_keyboard_proof_remains_unchanged_in_post_cutover(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_prove_first_usb_hid_keyboard_report()", 1)[1]
        body = body.split("@system\npub fn post_cutover_discover_first_storage_controller", 1)[0]
        self.assertIn("POST_CUTOVER_HID_REPORT_ATTEMPTS", body)
        self.assertIn("xhci_hid_report_poll_once()", body)
        self.assertIn("xhci_hid_keyboard_key0() == USB_HID_USAGE_KEYBOARD_A", body)
        self.assertNotIn("platform_hid_late_attach", text)

    def test_qemu_workflow_requires_dual_and_interleave_runtime_markers(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        keyboard = text.index("usb-kbd,bus=xhci.0")
        mouse = text.index("usb-mouse,bus=xhci.0")
        self.assertLess(keyboard, mouse)
        self.assertIn("sendkey a", text)
        self.assertIn("mouse_move 5 3", text)
        self.assertIn("BAKEN:USB_HID_DUAL_READY", text)
        self.assertIn("BAKEN:USB_HID_INTERLEAVE_READY", text)
        self.assertIn("python3 tests/test_hid_dual_runtime.py", text)
        self.assertIn("python3 tests/test_xhci_transfer.py", text)
        self.assertIn("python3 tests/test_xhci_hid_report.py", text)


if __name__ == "__main__":
    unittest.main()
