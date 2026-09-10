from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVENT = ROOT / "kernel/src/drivers/input_event.sotlas"


class InputEventTests(unittest.TestCase):
    def test_event_core_stays_protocol_and_transport_independent(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("module kernel::drivers::input_event", text)
        self.assertIn("INPUT_EVENT_QUEUE_CAPACITY: usize = 512", text)
        self.assertIn("import kernel::drivers::input_device::*;", text)
        for forbidden in ("xhci_", "dma_", "acpi_", "hid_input_report", "hid_report_descriptor"):
            self.assertNotIn(forbidden, text)

    def test_event_abi_carries_generation_safe_source_identity(self):
        text = EVENT.read_text(encoding="utf-8")
        for token in (
            "pub device_id: u32", "pub device_generation: u32",
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
        self.assertIn("INPUT_EVENT_COUNT >= INPUT_EVENT_QUEUE_CAPACITY", text)
        self.assertIn("INPUT_EVENT_DROPPED += 1", text)
        self.assertNotIn("kernel_heap", text)
        self.assertNotIn("alloc(", text)

    def test_queue_operations_are_irq_safe_and_smp_serialized(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("static mut INPUT_EVENT_LOCK: SpinLock", text)
        lock = text.split("fn input_event_lock_irq()", 1)[1].split(
            "fn input_event_unlock_irq", 1)[0]
        self.assertLess(lock.index("x86_irq_save_disable()"),
                        lock.index("spinlock_lock(&mut INPUT_EVENT_LOCK)"))
        for function in (
            "input_event_queue_count", "input_event_queue_dropped",
            "input_event_publish_for_device", "input_event_peek",
            "input_event_pop", "input_event_purge_device",
        ):
            body = text.split(f"pub fn {function}", 1)[1]
            body = body.split("\n@system", 1)[0]
            self.assertIn("input_event_lock_irq()", body)

    def test_publish_revalidates_active_generation_inside_queue_lock(self):
        text = EVENT.read_text(encoding="utf-8")
        body = text.split("pub fn input_event_publish_for_device", 1)[1]
        body = body.split("pub fn input_event_peek", 1)[0]
        first = body.index("input_device_is_active(device_id, device_generation)")
        lock = body.index("input_event_lock_irq()")
        second = body.index("input_device_is_active(device_id, device_generation)", first + 1)
        append = body.index("input_event_append_locked")
        self.assertLess(first, lock)
        self.assertLess(lock, second)
        self.assertLess(second, append)

    def test_detach_support_can_purge_only_old_generation(self):
        text = EVENT.read_text(encoding="utf-8")
        body = text.split("pub fn input_event_purge_device", 1)[1]
        body = body.split("pub fn input_event_queue_self_test", 1)[0]
        self.assertIn("event.device_id == device_id", body)
        self.assertIn("event.device_generation == device_generation", body)
        self.assertIn("let original = INPUT_EVENT_COUNT", body)

    def test_sequence_and_fifo_self_test_include_source_identity(self):
        text = EVENT.read_text(encoding="utf-8")
        self.assertIn("INPUT_EVENT_NEXT_SEQUENCE", text)
        self.assertIn("event.sequence = INPUT_EVENT_NEXT_SEQUENCE", text)
        body = text.split("pub fn input_event_queue_self_test()", 1)[1]
        self.assertIn("INPUT_EVENT_KIND_KEY_DOWN", body)
        self.assertIn("0, 0x07, 0x04, 1", body)
        self.assertIn("INPUT_EVENT_KIND_RELATIVE", body)
        self.assertIn("5, 0x01, 0x30, -2", body)
        self.assertIn("first.device_generation != 1", body)
        self.assertIn("second.device_generation != 7", body)


if __name__ == "__main__":
    unittest.main()
