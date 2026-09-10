from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID_EVENTS = ROOT / "kernel/src/drivers/hid_input_events.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class HidInputEventsTests(unittest.TestCase):
    def test_translator_only_depends_on_hid2_and_generic_event_core(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        self.assertIn("module kernel::drivers::hid_input_events", text)
        self.assertIn("import kernel::drivers::hid_input_report::*;", text)
        self.assertIn("import kernel::drivers::input_event::*;", text)
        for forbidden in ("xhci_", "dma_", "pci_", "acpi_"):
            self.assertNotIn(forbidden, text)

    def test_keyboard_previous_state_is_partitioned_by_report_id(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        self.assertIn("HID_EVENT_REPORT_SLOTS: usize = 256", text)
        self.assertIn("HID_EVENT_PREVIOUS_KEY_WORDS", text)
        self.assertIn("rid * HID_EVENT_KEYBOARD_WORDS", text)
        self.assertIn("INPUT_EVENT_KIND_KEY_DOWN", text)
        self.assertIn("INPUT_EVENT_KIND_KEY_UP", text)
        self.assertIn("decoded.usage != 0", text)

    def test_mouse_buttons_and_signed_relative_axes_are_normalized(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        for token in (
            "HID_EVENT_BUTTON_USAGE_PAGE", "INPUT_EVENT_KIND_BUTTON_DOWN",
            "INPUT_EVENT_KIND_BUTTON_UP", "HID_EVENT_USAGE_X",
            "HID_EVENT_USAGE_Y", "HID_EVENT_USAGE_WHEEL",
            "INPUT_EVENT_KIND_RELATIVE", "decoded.numeric_value",
            "INPUT_EVENT_FLAG_RELATIVE",
        ):
            self.assertIn(token, text)

    def test_report_is_hid2_validated_before_translation(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        body = text.split("pub fn hid_input_events_process_report", 1)[1]
        self.assertIn("hid_input_report_validate(report, length)", body)
        self.assertIn("hid_input_events_wire_report_id(report, length)", body)
        self.assertIn("hid_input_report_decode_field(report, length, index)", body)

    def test_queue_initialization_does_not_rebuild_descriptor_map(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        body = text.split("pub fn hid_input_events_initialize()", 1)[1]
        body = body.split("pub fn hid_input_events_is_ready", 1)[0]
        self.assertIn("hid_input_report_map_is_ready()", body)
        self.assertIn("input_event_queue_self_test()", body)
        self.assertNotIn("hid_input_report_map_build", body)

    def test_main_registers_event_layers(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::input_event::*;", text)
        self.assertIn("import kernel::drivers::hid_input_events::*;", text)


if __name__ == "__main__":
    unittest.main()
