#!/usr/bin/env python3
"""Guardrails da rota gráfica nativa pós-cutover."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
COMPAT = ROOT / "kernel/src/baken_runtime.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"

class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.text = RUNTIME.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")
        self.post = POST.read_text(encoding="utf-8")

    def test_compatibility_runtime_is_retired(self):
        self.assertFalse(COMPAT.exists())
        self.assertNotIn("baken_runtime", self.main)
        self.assertNotIn("baken_kernel_main", self.main)

    def test_runtime_has_no_firmware_bridge(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.text.splitlines())
        for token in ("Efi", "UEFI", "BootServices", "SystemTable", "Stall(", "baken_efi_"):
            with self.subTest(token=token): self.assertNotIn(token, code)

    def test_native_timer_has_single_frame_pacer(self):
        self.assertIn("x86_timer_calibrate_from_acpi_pm()", self.text)
        self.assertIn("x86_timer_spin_wait_us", self.text)
        display = (ROOT / "kernel/src/drivers/display_driver.sotlas").read_text(encoding="utf-8")
        wait = display.split("pub fn display_driver_wait_vsync", 1)[1].split("pub fn", 1)[0]
        self.assertNotIn("baken_efi_frame_wait", display)
        self.assertNotIn("baken_rdtsc()", wait)

    def test_native_input_does_not_block_xhci_platforms(self):
        self.assertIn("ps2_keyboard_init();", self.text)
        self.assertIn("ps2_mouse_init();", self.text)
        prepare = self.text.split("pub fn baken_native_runtime_prepare", 1)[1].split("pub fn", 1)[0]
        self.assertIn("return true;", prepare)

    def test_final_gate_precedes_graphical_runtime(self):
        entry = self.post.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        self.assertLess(entry.index("x86_serial_write_bare_metal_ready_marker()"),
                        entry.index("baken_native_kernel_run("))

if __name__ == "__main__": unittest.main()
