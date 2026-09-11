from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID_EVENTS = ROOT / "kernel/src/drivers/hid_input_events.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def _code_only(text: str) -> str:
    """Hide comments/strings so brace matching follows Sotlas structure."""
    out = []
    i = 0
    state = "code"
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                out.extend("  ")
                i += 2
                state = "line_comment"
                continue
            if char == "/" and nxt == "*":
                out.extend("  ")
                i += 2
                state = "block_comment"
                continue
            if char == '"':
                out.append(" ")
                i += 1
                state = "string"
                continue
            out.append(char)
            i += 1
            continue
        if state == "line_comment":
            if char == "\n":
                out.append("\n")
                state = "code"
            else:
                out.append(" ")
            i += 1
            continue
        if state == "block_comment":
            if char == "*" and nxt == "/":
                out.extend("  ")
                i += 2
                state = "code"
            else:
                out.append("\n" if char == "\n" else " ")
                i += 1
            continue
        if state == "string":
            if char == "\\" and i + 1 < len(text):
                out.extend("  ")
                i += 2
                continue
            if char == '"':
                out.append(" ")
                i += 1
                state = "code"
            else:
                out.append("\n" if char == "\n" else " ")
                i += 1
    return "".join(out)


def function_body(source: str, name: str) -> str:
    code = _code_only(source)
    marker = f"fn {name}("
    start = code.find(marker)
    if start < 0:
        raise AssertionError(f"function not found: {name}")
    brace = code.find("{", start)
    if brace < 0:
        raise AssertionError(f"function body not found: {name}")
    depth = 0
    for pos in range(brace, len(code)):
        if code[pos] == "{":
            depth += 1
        elif code[pos] == "}":
            depth -= 1
            if depth == 0:
                return code[brace + 1 : pos]
    raise AssertionError(f"unterminated function: {name}")


class HidInputEventsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = HID_EVENTS.read_text(encoding="utf-8")

    def test_translator_stays_transport_independent(self):
        text = self.text
        self.assertIn("module kernel::drivers::hid_input_events", text)
        self.assertIn("import kernel::drivers::input_device::*;", text)
        self.assertIn("import kernel::drivers::hid_input_device_map::*;", text)
        self.assertIn("import kernel::drivers::input_event::*;", text)
        for forbidden in ("xhci_", "dma_", "pci_", "acpi_"):
            self.assertNotIn(forbidden, text)

    def test_previous_state_is_partitioned_by_device_and_report_id(self):
        text = self.text
        self.assertIn("HID_EVENT_DEVICE_CAPACITY: usize = INPUT_DEVICE_CAPACITY", text)
        self.assertIn("HID_EVENT_REPORT_SLOTS: usize = 256", text)
        self.assertIn("HID_EVENT_DEVICE_KEY_WORDS", text)
        self.assertIn("device_slot * HID_EVENT_REPORT_SLOTS", text)
        self.assertIn("HID_EVENT_DEVICE_GENERATIONS", text)
        self.assertIn("HID_EVENT_DEVICE_ACTIVE", text)
        self.assertIn("INPUT_EVENT_KIND_KEY_DOWN", text)
        self.assertIn("INPUT_EVENT_KIND_KEY_UP", text)
        self.assertIn("decoded.usage != 0", text)

    def test_bind_requires_generation_specific_map_and_clears_state(self):
        body = function_body(self.text, "hid_input_events_bind_device")
        self.assertIn("input_device_is_active(device_id, device_generation)", body)
        self.assertIn("hid_input_device_map_is_ready(device_id, device_generation)", body)
        self.assertIn("hid_input_events_clear_device_locked(device_slot)", body)
        self.assertIn("HID_EVENT_DEVICE_GENERATIONS[device_slot] = device_generation", body)

    def test_state_mutation_is_irq_safe_and_smp_serialized(self):
        text = self.text
        self.assertIn("static mut HID_EVENT_LOCK: SpinLock", text)
        lock = function_body(text, "hid_input_events_lock_irq")
        self.assertLess(
            lock.index("x86_irq_save_disable()"),
            lock.index("spinlock_lock(&mut HID_EVENT_LOCK)"),
        )
        process = function_body(text, "hid_input_events_process_report_for_device")
        self.assertIn("let state_flags = hid_input_events_lock_irq()", process)
        self.assertIn("HID_EVENT_DEVICE_GENERATIONS[device_slot] != device_generation", process)
        self.assertIn("hid_input_device_map_is_ready(device_id, device_generation)", process)

    def test_mouse_buttons_and_signed_relative_axes_are_normalized(self):
        text = self.text
        for token in (
            "HID_EVENT_BUTTON_USAGE_PAGE",
            "INPUT_EVENT_KIND_BUTTON_DOWN",
            "INPUT_EVENT_KIND_BUTTON_UP",
            "HID_EVENT_USAGE_X",
            "HID_EVENT_USAGE_Y",
            "HID_EVENT_USAGE_WHEEL",
            "INPUT_EVENT_KIND_RELATIVE",
            "decoded.numeric_value",
            "INPUT_EVENT_FLAG_RELATIVE",
        ):
            self.assertIn(token, text)

    def test_report_map_is_validated_only_after_lifecycle_lock(self):
        body = function_body(self.text, "hid_input_events_process_report_for_device")
        validate_token = "hid_input_device_map_validate(device_id, device_generation, report, length)"
        wire_token = "hid_input_events_wire_report_id("
        count_token = "hid_input_device_map_field_count(device_id, device_generation)"
        field_token = "hid_input_device_map_field(device_id, device_generation, index)"
        decode_token = "hid_input_device_map_decode_field("
        lock_token = "let state_flags = hid_input_events_lock_irq()"
        for token in (validate_token, wire_token, count_token, field_token, decode_token, lock_token):
            self.assertIn(token, body)
        self.assertNotIn("hid_input_report_validate(", body)
        self.assertNotIn("hid_input_events_device_is_bound(", body)
        lock = body.index(lock_token)
        self.assertLess(lock, body.index(validate_token))
        self.assertLess(lock, body.index(wire_token))
        self.assertLess(lock, body.index(count_token))
        self.assertLess(lock, body.index(field_token))
        self.assertLess(lock, body.index(decode_token))

    def test_publish_carries_device_id_and_generation(self):
        body = function_body(self.text, "hid_input_events_publish")
        self.assertIn("input_event_publish_for_device(device_id, device_generation", body)

    def test_initialization_requires_map_core_but_does_not_build_or_reset_maps(self):
        initialize = function_body(self.text, "hid_input_events_initialize")
        self.assertIn("hid_input_device_map_core_is_ready()", initialize)
        self.assertIn("input_event_queue_self_test()", initialize)
        self.assertNotIn("hid_input_report_map_build", initialize)
        self.assertNotIn("hid_input_device_map_build", initialize)
        bind = function_body(self.text, "hid_input_events_bind_device")
        self.assertNotIn("input_event_initialize", bind)

    def test_main_registers_identity_and_event_layers(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::input_device::*;", text)
        self.assertIn("import kernel::drivers::input_event::*;", text)
        self.assertIn("import kernel::drivers::hid_input_events::*;", text)


if __name__ == "__main__":
    unittest.main()
