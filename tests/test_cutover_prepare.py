#!/usr/bin/env python3
"""Guardrails da preparação pura das estruturas de cutover."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "kernel/src/memory/cutover_prepare.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class CutoverPrepareTests(unittest.TestCase):
    def setUp(self):
        self.text = PREPARE.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_prepare_builds_arena_image_stack_and_tables_in_order(self):
        body = self.text.split("pub fn cutover_prepare", 1)[1]
        arena = body.index("page_table_arena_make(")
        image = body.index("transition_image_layout(")
        stack = body.index("transition_stack_layout(")
        tables = body.index("transition_page_tables_build(")
        self.assertLess(arena, image)
        self.assertLess(image, stack)
        self.assertLess(stack, tables)

    def test_result_exposes_only_prepared_addresses_and_counts(self):
        for token in (
            "root_physical: tables.root_physical",
            "stack_top: stack.stack_top",
            "table_pages_used: tables.table_pages_used",
            "direct_map_bytes: tables.direct_map_bytes",
        ):
            self.assertIn(token, self.text)

    def test_prepare_has_no_firmware_or_activation_side_effects(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.text.splitlines())
        for token in (
            "ExitBootServices", "GetMemoryMap", "BootServices", "AllocatePages",
            "x86_write_cr3", "x86_mmu_activate_root", "x86_lgdt_raw", "x86_lidt_raw",
            "x86_ltr_raw", "__sti", "__cli",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_hybrid_main_only_registers_prepare_module(self):
        self.assertIn("import kernel::memory::cutover_prepare::*;", self.main)
        body = self.main.split("pub fn baken_kernel_main", 1)[1]
        self.assertNotIn("cutover_prepare(", body)


if __name__ == "__main__":
    unittest.main()
