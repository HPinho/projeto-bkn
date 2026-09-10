from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID_EVENTS = ROOT / "kernel/src/drivers/hid_input_events.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class HidInputEventsTests(unittest.TestCase):
    def test_translator_stays_transport_independent(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        self.assertIn("module kernel::drivers::hid_input_events", text)
        self.assertIn("import kernel::drivers::input_device::*;", text)
        self.assertIn("import kernel::drivers::hid_input_report::*;", text)
        self.assertIn("import kernel::drivers::input_event::*;", text)
        for forbidden in ("xhci_", "dma_", "pci_", "acpi_"):
            self.assertNotIn(forbidden, text)

    def test_previous_state_is_partitioned_by_device_and_report_id(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        self.assertIn("HID_EVENT_DEVICE_CAPACITY: usize = INPUT_DEVICE_CAPACITY", text)
        self.assertIn("HID_EVENT_REPORT_SLOTS: usize = 256", text)
        self.assertIn("HID_EVENT_DEVICE_KEY_WORDS", text)
        self.assertIn("device_slot * HID_EVENT_REPORT_SLOTS", text)
        self.assertIn("HID_EVENT_DEVICE_GENERATIONS", text)
        self.assertIn("HID_EVENT_DEVICE_ACTIVE", text)
        self.assertIn("INPUT_EVENT_KIND_KEY_DOWN", text)
        self.assertIn("INPUT_EVENT_KIND_KEY_UP", text)
        self.assertIn("decoded.usage != 0", text)

    def test_bind_unbind_are_generation_safe_and_clear_device_state(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        for token in (
            "pub fn hid_input_events_bind_device",
            "pub fn hid_input_events_unbind_device",
            "hid_input_events_clear_device_locked(device_slot)",
            "HID_EVENT_DEVICE_GENERATIONS[device_slot] == device_generation",
            "input_device_is_active(device_id, device_generation)",
        ):
            self.assertIn(token, text)

    def test_state_mutation_is_irq_safe_and_smp_serialized(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        self.assertIn("static mut HID_EVENT_LOCK: SpinLock", text)
        lock = text.split("fn hid_input_events_lock_irq()", 1)[1].split(
            "fn hid_input_events_unlock_irq", 1)[0]
        self.assertLess(lock.index("x86_irq_save_disable()"),
                        lock.index("spinlock_lock(&mut HID_EVENT_LOCK)"))
        process = text.split("pub fn hid_input_events_process_report_for_device", 1)[1]
        self.assertIn("let state_flags = hid_input_events_lock_irq()", process)
        self.assertIn("HID_EVENT_DEVICE_GENERATIONS[device_slot] != device_generation", process)

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

    def test_report_is_hid2_validated_before_generation_locked_translation(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        body = text.split("pub fn hid_input_events_process_report_for_device", 1)[1]
        self.assertIn("hid_input_report_validate(report, length)", body)
        self.assertIn("hid_input_events_wire_report_id(report, length)", body)
        self.assertIn("hid_input_report_decode_field(report, length, index)", body)
        validate = body.index("hid_input_report_validate(report, length)")
        lock = body.index("let state_flags = hid_input_events_lock_irq()")
        self.assertLess(validate, lock)

    def test_publish_carries_device_id_and_generation(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        body = text.split("fn hid_input_events_publish(", 1)[1]
        body = body.split("fn hid_input_events_set_keyboard_usage", 1)[0]
        self.assertIn("input_event_publish_for_device(device_id, device_generation", body)

    def test_initialization_does_not_rebuild_descriptor_map_or_reset_per_attach(self):
        text = HID_EVENTS.read_text(encoding="utf-8")
        body = text.split("pub fn hid_input_events_initialize()", 1)[1]
        body = body.split("pub fn hid_input_events_is_ready", 1)[0]
        self.assertIn("hid_input_report_map_is_ready()", body)
        self.assertIn("input_event_queue_self_test()", body)
        self.assertNotIn("hid_input_report_map_build", body)
        bind = text.split("pub fn hid_input_events_bind_device", 1)[1]
        bind = bind.split("pub fn hid_input_events_unbind_device", 1)[0]
        self.assertNotIn("input_event_initialize", bind)

    def test_main_registers_identity_and_event_layers(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::input_device::*;", text)
        self.assertIn("import kernel::drivers::input_event::*;", text)
        self.assertIn("import kernel::drivers::hid_input_events::*;", text)


if __name__ == "__main__":
    unittest.main()
