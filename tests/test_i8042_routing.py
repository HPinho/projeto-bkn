#!/usr/bin/env python3
"""Safety contracts for the shared i8042 input controller."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
I8042 = ROOT / "kernel/src/drivers/i8042.sotlas"
MOUSE = ROOT / "kernel/src/drivers/ps2_mouse.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def _code_only(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class I8042RoutingTests(unittest.TestCase):
    def test_only_controller_owns_raw_ps2_ports(self):
        controller = I8042.read_text(encoding="utf-8")
        mouse = _code_only(MOUSE.read_text(encoding="utf-8"))
        self.assertIn("I8042_DATA_PORT: u16 = 0x60", controller)
        self.assertIn("I8042_STATUS_PORT: u16 = 0x64", controller)
        self.assertNotIn("__inb(", mouse)
        self.assertNotIn("__outb(", mouse)
        self.assertNotIn("0x60", mouse)
        self.assertNotIn("0x64", mouse)

    def test_controller_routes_keyboard_and_aux_to_distinct_queues(self):
        text = I8042.read_text(encoding="utf-8")
        for token in (
            "KBD_QUEUE",
            "AUX_QUEUE",
            "i8042_queue_kbd(data)",
            "i8042_queue_aux(data)",
            "pub fn i8042_pop_keyboard",
            "pub fn i8042_pop_aux",
            "I8042_STATUS_AUX_DATA",
        ):
            self.assertIn(token, text)

    def test_polling_mode_does_not_enable_irq1_or_irq12_early(self):
        text = I8042.read_text(encoding="utf-8")
        self.assertIn("config = config & 0xCC", text)
        self.assertIn("pub fn i8042_enable_native_irqs()", text)
        main = MAIN.read_text(encoding="utf-8")
        self.assertNotIn("i8042_enable_native_irqs(", main)
        self.assertNotIn("i8042_enable_keyboard_irq_only(", main)

    def test_keyboard_only_mode_sets_irq1_and_explicitly_keeps_aux_off(self):
        text = I8042.read_text(encoding="utf-8")
        self.assertIn("pub fn i8042_enable_keyboard_irq_only()", text)
        body = text.split("pub fn i8042_enable_keyboard_irq_only()", 1)[1].split(
            "pub fn i8042_enable_native_irqs()", 1
        )[0]
        self.assertIn("i8042_set_native_irq_mask(true, false)", body)
        self.assertIn("pub fn i8042_keyboard_irq_enabled()", text)
        self.assertIn("pub fn i8042_aux_irq_enabled()", text)

    def test_irq_mask_rewrites_both_bits_from_scratch(self):
        text = I8042.read_text(encoding="utf-8")
        body = text.split("fn i8042_set_native_irq_mask", 1)[1].split(
            "pub fn i8042_enable_keyboard_irq_only", 1
        )[0]
        self.assertIn("config = config & 0xFC", body)
        self.assertIn("if keyboard { config = config | 0x01; }", body)
        self.assertIn("if aux { config = config | 0x02; }", body)
        self.assertIn("I8042_KEYBOARD_IRQ_ENABLED = keyboard", body)
        self.assertIn("I8042_AUX_IRQ_ENABLED = aux", body)

    def test_mouse_consumes_only_aux_queue(self):
        text = MOUSE.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::i8042::*;", text)
        self.assertIn("i8042_pop_aux(&mut data)", text)
        self.assertNotIn("i8042_pop_keyboard", text)


if __name__ == "__main__":
    unittest.main()
