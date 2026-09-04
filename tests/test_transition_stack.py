#!/usr/bin/env python3
"""Guardrails do layout da stack própria usada no futuro cutover."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "kernel/src/memory/transition_stack.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class TransitionStackTests(unittest.TestCase):
    def setUp(self):
        self.stack = STACK.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_layout_reserves_guard_then_context_then_stack(self):
        self.assertIn("guard_page_virtual_base: virtual_base", self.stack)
        self.assertIn("context_physical_base = physical_base + X86_PAGE_SIZE", self.stack)
        self.assertIn("context_virtual_base = virtual_base + X86_PAGE_SIZE", self.stack)
        self.assertIn("usable_physical_base = physical_base + (2 * X86_PAGE_SIZE)", self.stack)
        self.assertIn("usable_virtual_base = virtual_base + (2 * X86_PAGE_SIZE)", self.stack)
        self.assertIn("usable_page_count = page_count - 2", self.stack)

    def test_stack_top_is_16_byte_aligned(self):
        self.assertIn("let stack_top = raw_top & ~15", self.stack)
        self.assertIn("page_count < 3", self.stack)
        self.assertIn("x86_page_aligned(physical_base)", self.stack)
        self.assertIn("x86_page_aligned(virtual_base)", self.stack)

    def test_layout_is_pure_and_does_not_switch_stack_or_mmu(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.stack.splitlines())
        for token in (
            "ExitBootServices", "GetMemoryMap", "AllocatePages", "__write_cr3",
            "x86_write_cr3", "__invlpg", "mov %rsp", "asm", "page_table_map_4k",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_main_registers_layout_without_switching_rsp(self):
        self.assertIn("import kernel::memory::transition_stack::*;", self.main)
        self.assertNotIn("transition_stack_layout(", self.main)
        self.assertNotIn("x86_write_cr3(", self.main)


if __name__ == "__main__":
    unittest.main()
