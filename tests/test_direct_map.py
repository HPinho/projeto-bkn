#!/usr/bin/env python3
"""Guardrails do planejamento de direct physical map."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIRECT = ROOT / "kernel" / "src" / "memory" / "direct_map.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class DirectMapTests(unittest.TestCase):
    def setUp(self):
        self.direct = DIRECT.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_high_half_window_and_sizes_are_explicit(self):
        self.assertIn("BAKEN_DIRECT_MAP_BASE: u64 = 0xFFFF800000000000", self.direct)
        self.assertIn("X86_PAGE_SIZE_2M: u64 = 2 * 1024 * 1024", self.direct)
        self.assertIn("X86_PAGE_SIZE_1G: u64 = 1024 * 1024 * 1024", self.direct)

    def test_plan_prefers_2m_and_reserves_only_one_tail_pt(self):
        self.assertIn("huge_page_count = physical_limit / X86_PAGE_SIZE_2M", self.direct)
        self.assertIn("tail_4k_page_count = tail_bytes / X86_PAGE_SIZE", self.direct)
        self.assertIn("if tail_4k_page_count != 0 { 1 } else { 0 }", self.direct)
        self.assertIn("1 + pdpt_table_count + pd_table_count + pt_table_count", self.direct)

    def test_plan_rejects_addresses_outside_direct_map_span(self):
        self.assertIn("highest_physical_address > BAKEN_DIRECT_MAP_SPAN", self.direct)
        self.assertIn("physical_address >= BAKEN_DIRECT_MAP_SPAN", self.direct)

    def test_direct_map_is_planning_only(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.direct.splitlines())
        for token in (
            "write_cr3", "__write_cr3", "__invlpg", "vmm_mark_tables_ready(",
            "pmm_alloc_page(", "pmm_alloc_pages(", "as *mut u64", "as *mut u8",
        ):
            self.assertNotIn(token, code)

    def test_hybrid_main_only_imports_planner(self):
        self.assertIn("import kernel::memory::direct_map::*;", self.main)
        for token in ("direct_map_plan_make(", "vmm_mark_tables_ready(", "write_cr3"):
            self.assertNotIn(token, self.main)

    def test_reference_table_count_for_4gib(self):
        physical_limit = 4 * 1024 * 1024 * 1024
        one_gib = 1024 * 1024 * 1024
        pml4_span = 512 * one_gib
        pd_tables = (physical_limit + one_gib - 1) // one_gib
        pdpt_tables = (physical_limit + pml4_span - 1) // pml4_span
        pt_tables = 0
        self.assertEqual(1 + pdpt_tables + pd_tables + pt_tables, 6)


if __name__ == "__main__":
    unittest.main()
