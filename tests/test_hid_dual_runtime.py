import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATE = ROOT / "kernel/src/platform/hid_late_attach.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_hid_dual.yml"


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
        self.assertIn("xhci_hid_report_last_length_for(second_slot)", text)
        self.assertIn("XHCI_HID_BOOT_MOUSE_MIN_LENGTH", text)

    def test_dual_ready_marker_is_only_after_real_mouse_report(self):
        text = LATE.read_text(encoding="utf-8")
        poll = text.index("xhci_hid_report_poll_slot_once(second_slot)")
        length = text.index("xhci_hid_report_last_length_for(second_slot)")
        marker = text.index("platform_hid_late_attach_emit_ready_marker()", poll)
        publish = text.index("PLATFORM_HID_LATE_ATTACH_READY = true", marker)
        self.assertLess(poll, length)
        self.assertLess(length, marker)
        self.assertLess(marker, publish)

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

    def test_qemu_dual_workflow_keeps_keyboard_first_and_requires_runtime_marker(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        keyboard = text.index("usb-kbd,bus=xhci.0")
        mouse = text.index("usb-mouse,bus=xhci.0")
        self.assertLess(keyboard, mouse)
        self.assertIn("sendkey a", text)
        self.assertIn("mouse_move 5 3", text)
        self.assertIn("BAKEN:USB_HID_DUAL_READY", text)
        self.assertIn("python3 tests/test_hid_dual_runtime.py", text)


if __name__ == "__main__":
    unittest.main()
