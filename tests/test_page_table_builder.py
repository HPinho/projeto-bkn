#!/usr/bin/env python3
"""Guardrails do builder bootstrap de page tables/direct-map."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "kernel" / "src" / "memory" / "page_table_builder.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class PageTableBuilderTests(unittest.TestCase):
    def setUp(self):
        self.builder = BUILDER.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_builder_materializes_all_four_levels(self):
        for symbol in (
            "x86_pml4_index", "x86_pdpt_index", "x86_pd_index", "x86_pt_index",
            "page_table_arena_alloc", "page_table_zero", "page_table_write_entry",
        ):
            self.assertIn(symbol, self.builder)

    def test_direct_map_is_nx_and_prefers_huge_pages(self):
        self.assertIn("X86_PTE_GLOBAL | X86_PTE_NX", self.builder)
        self.assertIn("page_table_direct_map_flags() | X86_PTE_HUGE", self.builder)
        self.assertIn("remaining >= X86_PAGE_SIZE_2M", self.builder)
        self.assertIn("physical_cursor += X86_PAGE_SIZE_2M", self.builder)
        self.assertIn("physical_cursor += X86_PAGE_SIZE", self.builder)

    def test_builder_uses_arena_not_pmm_or_uefi(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.builder.splitlines())
        for token in (
            "pmm_alloc_page(", "pmm_alloc_pages(", "BootServices", "SystemTable",
            "AllocatePages", "AllocatePool", "ExitBootServices",
        ):
            self.assertNotIn(token, code)

    def test_builder_does_not_activate_mmu(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.builder.splitlines())
        for token in (
            "write_cr3", "__write_cr3", "__invlpg", "vmm_mark_tables_ready(",
            "vmm_activate(", "__wrmsr",
        ):
            self.assertNotIn(token, code)

    def test_builder_requires_enough_arena_pages(self):
        self.assertIn("page_table_arena_remaining", self.builder)
        self.assertIn("< (*plan).table_page_count", self.builder)

    def test_hybrid_main_only_registers_builder(self):
        self.assertIn("import kernel::memory::page_table_builder::*;", self.main)
        self.assertNotIn("page_table_build_direct_map(", self.main)


if __name__ == "__main__":
    unittest.main()
