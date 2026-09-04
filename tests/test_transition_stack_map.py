#!/usr/bin/env python3
"""Guardrails do mapping da stack de transição."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
STACK_MAP = ROOT / "kernel/src/memory/transition_stack_map.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class TransitionStackMapTests(unittest.TestCase):
    def setUp(self):
        self.text = STACK_MAP.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_only_usable_pages_are_mapped(self):
        self.assertIn("layout.usable_virtual_base", self.text)
        self.assertIn("layout.usable_physical_base", self.text)
        self.assertIn("layout.usable_page_count * X86_PAGE_SIZE", self.text)
        self.assertNotIn("layout.guard_page_virtual_base", self.text)

    def test_stack_mapping_is_rw_and_nx(self):
        self.assertIn("X86_PTE_WRITABLE", self.text)
        self.assertIn("X86_PTE_NX", self.text)
        self.assertIn("transition_map_range(", self.text)

    def test_mapper_does_not_activate_mmu_or_switch_stack(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.text.splitlines())
        for token in (
            "ExitBootServices", "GetMemoryMap", "AllocatePages", "__write_cr3",
            "x86_write_cr3", "__invlpg", "asm", "mov %rsp",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_main_registers_but_does_not_execute_stack_mapping(self):
        self.assertIn("import kernel::memory::transition_stack_map::*;", self.main)
        self.assertNotIn("transition_stack_map(", self.main)
        self.assertNotIn("x86_write_cr3(", self.main)


if __name__ == "__main__":
    unittest.main()
