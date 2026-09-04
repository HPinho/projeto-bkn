#!/usr/bin/env python3
"""Impede ativação prematura de estado privilegiado enquanto UEFI ainda vive."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "kernel" / "src" / "main.sotlas"
CPU = ROOT / "kernel" / "src" / "arch" / "x86_64" / "cpu.sotlas"


class PreExitCpuSafetyTests(unittest.TestCase):
    def test_kernel_entry_does_not_activate_descriptor_tables_cr3_or_stack_yet(self):
        text = MAIN.read_text(encoding="utf-8")
        body = text.split("pub fn baken_kernel_main", 1)[1]
        for token in (
            "x86_lgdt_raw(", "x86_lidt_raw(", "x86_ltr_raw(",
            "x86_gdt_activate_segments_raw(", "x86_lidt_table_raw(",
            "x86_write_cr3_raw(", "x86_stack_switch_to_post_cutover_raw(",
            "__lgdt(", "__lidt(", "__ltr(", "__write_cr3(",
            "__gdt_activate_segments(", "__lidt_table(",
            "__stack_switch_to_post_cutover(",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, body)

    def test_raw_privileged_wrappers_are_isolated_in_arch_module(self):
        text = CPU.read_text(encoding="utf-8")
        self.assertIn("__lgdt(descriptor_address)", text)
        self.assertIn("__lidt(descriptor_address)", text)
        self.assertIn("__gdt_activate_segments(base, limit, code_selector, data_selector)", text)
        self.assertIn("__lidt_table(base, limit)", text)
        self.assertIn("__ltr(selector)", text)
        self.assertIn("return __read_cr2()", text)
        self.assertIn("return __read_cr3()", text)
        self.assertIn("__write_cr3(root_physical)", text)
        self.assertIn("__stack_switch_to_post_cutover(stack_top, argument)", text)
        self.assertIn("__invlpg(address)", text)


if __name__ == "__main__":
    unittest.main()
