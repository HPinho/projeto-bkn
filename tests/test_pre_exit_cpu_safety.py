#!/usr/bin/env python3
"""Impede ativação prematura de estado privilegiado enquanto UEFI ainda vive."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "kernel" / "src" / "main.sotlas"
CPU = ROOT / "kernel" / "src" / "arch" / "x86_64" / "cpu.sotlas"


class PreExitCpuSafetyTests(unittest.TestCase):
    def test_kernel_entry_does_not_activate_descriptor_tables_yet(self):
        text = MAIN.read_text(encoding="utf-8")
        body = text.split("pub fn baken_kernel_main", 1)[1]
        self.assertNotIn("x86_lgdt_raw(", body)
        self.assertNotIn("x86_lidt_raw(", body)
        self.assertNotIn("x86_ltr_raw(", body)
        self.assertNotIn("__lgdt(", body)
        self.assertNotIn("__lidt(", body)
        self.assertNotIn("__ltr(", body)

    def test_raw_privileged_wrappers_are_isolated_in_arch_module(self):
        text = CPU.read_text(encoding="utf-8")
        self.assertIn("__lgdt(descriptor_address)", text)
        self.assertIn("__lidt(descriptor_address)", text)
        self.assertIn("__ltr(selector)", text)
        self.assertIn("return __read_cr2()", text)
        self.assertIn("__invlpg(address)", text)


if __name__ == "__main__":
    unittest.main()
