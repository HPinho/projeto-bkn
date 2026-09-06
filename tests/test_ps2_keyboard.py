#!/usr/bin/env python3
"""Contracts for native PS/2 keyboard input after UEFI runtime retirement."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
KEYBOARD = ROOT / "kernel/src/drivers/ps2_keyboard.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
COMPAT = ROOT / "kernel/src/baken_runtime.sotlas"


class Ps2KeyboardTests(unittest.TestCase):
    def test_keyboard_consumes_shared_kbd_queue_only(self):
        text = KEYBOARD.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::i8042::*;", text)
        self.assertIn("i8042_pop_keyboard(&mut raw)", text)
        self.assertNotIn("__inb(", text)
        self.assertNotIn("__outb(", text)

    def test_set1_decoder_tracks_shift_and_key_releases(self):
        text = KEYBOARD.read_text(encoding="utf-8")
        self.assertIn("PS2_KEYBOARD_SHIFT", text)
        self.assertIn("let released = (raw & 0x80) != 0", text)
        self.assertIn("code == 0x2A || code == 0x36", text)
        self.assertIn("ps2_keyboard_ascii", text)

    def test_runtime_uses_native_keyboard_without_uefi_fallback(self):
        text = RUNTIME.read_text(encoding="utf-8")
        compat = COMPAT.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::ps2_keyboard::*;", text)
        self.assertIn("ps2_keyboard_init();", text)
        self.assertIn("while ps2_keyboard_poll(&mut scancode, &mut unicode) == 1", text)
        self.assertNotIn("baken_efi_poll_key", text)
        self.assertNotIn("baken_efi_poll_key", compat)
        self.assertNotIn("ReadKeyStroke", compat)


if __name__ == "__main__":
    unittest.main()
