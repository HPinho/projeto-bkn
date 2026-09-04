#!/usr/bin/env python3
"""Guardrails da rota de runtime nativa pós-UEFI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.text = RUNTIME.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_runtime_has_no_firmware_bridge(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.text.splitlines())
        for token in (
            "Efi", "UEFI", "BootServices", "SystemTable", "LocateProtocol",
            "Stall(", "baken_efi_", "pointer_protocol", "block_io_protocol",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_native_timer_uses_acpi_pm_and_tsc(self):
        self.assertIn("x86_timer_calibrate_from_acpi_pm()", self.text)
        self.assertIn("x86_timer_spin_wait_us", self.text)
        self.assertIn("x86_timer_elapsed_us", self.text)
        self.assertNotIn("x86_timer_set_cycles_per_us(3000)", self.text)

    def test_native_input_is_real_ps2_and_fails_closed(self):
        self.assertIn("ps2_keyboard_init();", self.text)
        self.assertIn("ps2_mouse_init();", self.text)
        self.assertIn("ps2_keyboard_is_present() || ps2_mouse_is_present()", self.text)
        self.assertIn("if !baken_native_runtime_prepare() { loop {} }", self.text)

    def test_hybrid_main_registers_but_does_not_enter_native_runtime(self):
        self.assertIn("import kernel::baken_native_runtime::*;", self.main)
        body = self.main.split("pub fn baken_kernel_main", 1)[1]
        self.assertNotIn("baken_native_runtime_run(", body)
        self.assertIn("baken_runtime_run(", body)


if __name__ == "__main__":
    unittest.main()
