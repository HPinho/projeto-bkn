#!/usr/bin/env python3
"""Guardrails da arena bootstrap de page tables."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARENA = ROOT / "kernel" / "src" / "memory" / "page_table_arena.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class PageTableArenaTests(unittest.TestCase):
    def setUp(self):
        self.arena = ARENA.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_page_keeps_physical_and_virtual_identity_separate(self):
        self.assertIn("pub physical_address: u64", self.arena)
        self.assertIn("pub virtual_address: u64", self.arena)
        self.assertIn("pub fn page_table_arena_make", self.arena)
        self.assertIn("x86_page_aligned(physical_base)", self.arena)
        self.assertIn("x86_page_aligned(virtual_base)", self.arena)

    def test_allocator_advances_both_views_by_same_page_offset(self):
        self.assertIn("let offset = (*arena).next_page_index * X86_PAGE_SIZE", self.arena)
        self.assertIn("physical_base + offset", self.arena)
        self.assertIn("virtual_base + offset", self.arena)
        self.assertIn("(*arena).next_page_index += 1", self.arena)

    def test_arena_can_reopen_only_already_allocated_pages(self):
        self.assertIn("pub fn page_table_arena_page_from_physical", self.arena)
        self.assertIn("physical_address < (*arena).physical_base", self.arena)
        self.assertIn("let allocated_bytes = (*arena).next_page_index * X86_PAGE_SIZE", self.arena)
        self.assertIn("offset >= allocated_bytes", self.arena)
        self.assertIn("let virtual_address = (*arena).virtual_base + offset", self.arena)

    def test_arena_fails_closed_on_exhaustion(self):
        self.assertIn("next_page_index >= (*arena).page_count", self.arena)
        self.assertIn("return page_table_page_invalid();", self.arena)

    def test_arena_does_not_assume_identity_map_or_activate_cr3(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.arena.splitlines())
        for token in (
            "physical_base as *mut", "physical_address as *mut",
            "physical_address as *const", "physical_address as usize",
            "write_cr3", "__write_cr3", "vmm_mark_tables_ready(", "__invlpg",
        ):
            self.assertNotIn(token, code)

    def test_hybrid_main_only_registers_module(self):
        self.assertIn("import kernel::memory::page_table_arena::*;", self.main)
        for token in (
            "page_table_arena_make(", "page_table_arena_alloc(",
            "page_table_arena_page_from_physical(", "write_cr3"
        ):
            self.assertNotIn(token, self.main)


if __name__ == "__main__":
    unittest.main()
