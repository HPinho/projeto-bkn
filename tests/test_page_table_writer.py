#!/usr/bin/env python3
"""Guardrails do writer bootstrap de page tables."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "kernel" / "src" / "memory" / "page_table_writer.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class PageTableWriterTests(unittest.TestCase):
    def setUp(self):
        self.writer = WRITER.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_writer_has_exactly_512_entries_per_table(self):
        self.assertIn("X86_PAGE_TABLE_ENTRY_COUNT: u16 = 512", self.writer)
        self.assertIn("while index < X86_PAGE_TABLE_ENTRY_COUNT", self.writer)
        self.assertIn("index >= X86_PAGE_TABLE_ENTRY_COUNT", self.writer)

    def test_writer_accepts_metadata_by_value(self):
        self.assertIn("pub fn page_table_page_writable(page: PageTablePage)", self.writer)
        self.assertIn("pub fn page_table_zero(page: PageTablePage)", self.writer)
        self.assertIn("pub fn page_table_write_entry(page: PageTablePage", self.writer)
        self.assertNotIn("*const PageTablePage", self.writer)

    def test_writer_uses_virtual_address_only_for_dereference(self):
        self.assertIn("page.virtual_address as *mut u64", self.writer)
        self.assertIn("page.virtual_address as usize", self.writer)
        code = "\n".join(line.split("//", 1)[0] for line in self.writer.splitlines())
        for token in (
            "physical_address as *mut", "physical_address as usize",
            "physical_address as *const",
        ):
            self.assertNotIn(token, code)

    def test_writer_validates_both_physical_and_virtual_alignment(self):
        self.assertIn("x86_page_aligned(page.physical_address)", self.writer)
        self.assertIn("x86_page_aligned(page.virtual_address)", self.writer)

    def test_writer_does_not_activate_mmu_or_allocate(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.writer.splitlines())
        for token in (
            "write_cr3", "__write_cr3", "__invlpg", "pmm_alloc_page(",
            "pmm_alloc_pages(", "vmm_mark_tables_ready(",
        ):
            self.assertNotIn(token, code)

    def test_hybrid_main_does_not_write_page_tables(self):
        self.assertIn("import kernel::memory::page_table_writer::*;", self.main)
        for token in ("page_table_zero(", "page_table_write_entry(", "page_table_read_entry("):
            self.assertNotIn(token, self.main)


if __name__ == "__main__":
    unittest.main()
