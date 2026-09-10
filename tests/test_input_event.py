from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "kernel/src/drivers/input_event.sotlas"


class InputEventTests(unittest.TestCase):
    def test_event_core_is_transport_and_protocol_independent(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("module kernel::drivers::input_event", text)
        self.assertIn("INPUT_EVENT_QUEUE_CAPACITY: usize = 512", text)
        for forbidden in ("xhci_", "dma_", "acpi_", "hid_input_report", "hid_report_descriptor"):
            self.assertNotIn(forbidden, text)

    def test_event_abi_covers_keyboard_pointer_and_future_touch(self):
        text = EVENT.read_text(encoding="utf-8")
        for token in (
            "INPUT_DEVICE_CLASS_KEYBOARD", "INPUT_DEVICE_CLASS_POINTER",
            "INPUT_DEVICE_CLASS_TOUCH", "INPUT_EVENT_KIND_KEY_DOWN",
            "INPUT_EVENT_KIND_KEY_UP", "INPUT_EVENT_KIND_BUTTON_DOWN",
            "INPUT_EVENT_KIND_BUTTON_UP", "INPUT_EVENT_KIND_RELATIVE",
            "INPUT_EVENT_KIND_ABSOLUTE", "pub usage_page: u32", "pub usage: u32",
            "pub value: i64", "pub report_id: u8",
        ):
            self.assertIn(token, text)

    def test_queue_is_fixed_capacity_non_heap_and_reports_overflow(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("static mut INPUT_EVENT_QUEUE: [InputEvent; INPUT_EVENT_QUEUE_CAPACITY]", text)
        self.assertIn("if INPUT_EVENT_COUNT >= INPUT_EVENT_QUEUE_CAPACITY", text)
        self.assertIn("INPUT_EVENT_DROPPED += 1", text)
        self.assertNotIn("kernel_heap", text)
        self.assertNotIn("alloc(", text)

    def test_queue_has_monotonic_sequence_and_fifo_pop(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("INPUT_EVENT_NEXT_SEQUENCE", text)
        self.assertIn("event.sequence = INPUT_EVENT_NEXT_SEQUENCE", text)
        self.assertIn("pub fn input_event_peek()", text)
        self.assertIn("pub fn input_event_pop()", text)
        self.assertIn("INPUT_EVENT_HEAD += 1", text)
        self.assertIn("INPUT_EVENT_COUNT -= 1", text)

    def test_self_test_covers_key_and_relative_event(self):
        text = EVENT.read_text(encoding="utf-8")
        body = text.split("pub fn input_event_queue_self_test()", 1)[1]
        self.assertIn("INPUT_EVENT_KIND_KEY_DOWN", body)
        self.assertIn("0x07, 0x04", body)
        self.assertIn("INPUT_EVENT_KIND_RELATIVE", body)
        self.assertIn("0x30, -2", body)


if __name__ == "__main__":
    unittest.main()
