import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "kernel/src/drivers/hid_input_events.sotlas"


def _code_only(text: str) -> str:
    out = []
    i = 0
    state = "code"
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ""
        if state == "code":
            if c == "/" and n == "/":
                out.extend("  ")
                i += 2
                state = "line_comment"
                continue
            if c == "/" and n == "*":
                out.extend("  ")
                i += 2
                state = "block_comment"
                continue
            if c == '"':
                out.append(" ")
                i += 1
                state = "string"
                continue
            out.append(c)
            i += 1
            continue
        if state == "line_comment":
            if c == "\n":
                out.append("\n")
                state = "code"
            else:
                out.append(" ")
            i += 1
            continue
        if state == "block_comment":
            if c == "*" and n == "/":
                out.extend("  ")
                i += 2
                state = "code"
            else:
                out.append("\n" if c == "\n" else " ")
                i += 1
            continue
        if state == "string":
            if c == "\\" and i + 1 < len(text):
                out.extend("  ")
                i += 2
                continue
            if c == '"':
                out.append(" ")
                i += 1
                state = "code"
            else:
                out.append("\n" if c == "\n" else " ")
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


class HidInputEventDetachSerializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.body = function_body(cls.source, "hid_input_events_process_report_for_device")

    def test_lifecycle_lock_precedes_all_field_map_reads(self):
        body = self.body
        lock = body.index("let state_flags = hid_input_events_lock_irq();")
        validate = body.index("hid_input_device_map_validate(")
        wire = body.index("hid_input_events_wire_report_id(")
        count = body.index("hid_input_device_map_field_count(")
        field = body.index("hid_input_device_map_field(")
        decode = body.index("hid_input_device_map_decode_field(")
        self.assertLess(lock, validate)
        self.assertLess(lock, wire)
        self.assertLess(lock, count)
        self.assertLess(lock, field)
        self.assertLess(lock, decode)

    def test_process_does_not_reenter_bound_query_while_locked(self):
        self.assertNotIn("hid_input_events_device_is_bound(", self.body)
        self.assertEqual(self.body.count("hid_input_events_lock_irq();"), 1)

    def test_all_guarded_failure_exits_release_lifecycle_lock(self):
        body = self.body
        lock = body.index("let state_flags = hid_input_events_lock_irq();")
        guarded_start = body.index("unsafe {", lock)
        guarded = body[guarded_start:]
        failures = guarded.count("return false;")
        unlocks = guarded.count("hid_input_events_unlock_irq(state_flags);")
        self.assertGreater(failures, 0)
        self.assertEqual(unlocks, failures + 1, "every guarded failure plus success must unlock")

    def test_unbind_uses_same_lifecycle_lock(self):
        unbind = function_body(self.source, "hid_input_events_unbind_device")
        self.assertIn("let flags = hid_input_events_lock_irq();", unbind)
        self.assertIn("HID_EVENT_DEVICE_ACTIVE[device_slot] = false;", unbind)
        self.assertIn("HID_EVENT_DEVICE_GENERATIONS[device_slot] = 0;", unbind)
        self.assertIn("hid_input_events_unlock_irq(flags);", unbind)


if __name__ == "__main__":
    unittest.main()
