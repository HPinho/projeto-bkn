from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"
XHCI_DESCRIPTOR = ROOT / "kernel/src/drivers/xhci_hid_descriptor.sotlas"
XHCI_REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"


class Hid3RuntimeContractTests(unittest.TestCase):
    def test_smoke_requires_model_and_a_real_published_event(self):
        text = SMOKE.read_text(encoding="utf-8")
        self.assertIn('"USB_HID_EVENT_MODEL_READY"', text)
        self.assertIn('"USB_HID_EVENT_READY"', text)
        self.assertIn("BAKEN:USB_HID_EVENT_MODEL_FAILED", text)
        self.assertIn("BAKEN:USB_HID_EVENT_FAILED", text)

    def test_event_model_marker_is_after_hid2_map(self):
        text = XHCI_DESCRIPTOR.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_descriptor_probe_internal() -> bool", 1)[1]
        body = body.split("pub fn xhci_hid_descriptor_emit_ready_marker()", 1)[0]
        self.assertLess(body.index("xhci_hid_input_map_emit_ready_marker()"),
                        body.index("xhci_hid_event_model_emit_ready_marker()"))

    def test_real_event_marker_is_not_emitted_for_neutral_report_only(self):
        text = XHCI_REPORT.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_report_parse_for_slot(slot_id: u8, length: u32) -> bool", 1)[1]
        body = body.split("pub fn xhci_hid_report_is_ready_for", 1)[0]
        self.assertIn("let before_events = hid_input_events_events_published()", body)
        self.assertIn("let after_events = hid_input_events_events_published()", body)
        self.assertIn("after_events > before_events", body)
        self.assertIn("XHCI_HID_REPORT_STATES[state_index].event_marker_emitted", body)
        marker_test = body.index("after_events > before_events")
        ready_marker = body.index("xhci_hid_report_emit_event_ready_marker()")
        self.assertLess(marker_test, ready_marker)


if __name__ == "__main__":
    unittest.main()
