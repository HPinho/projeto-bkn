#!/usr/bin/env python3
"""Guardrails do mapper bootstrap de page tables."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAPPER = ROOT / "kernel" / "src" / "memory" / "page_table_mapper.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class PageTableMapperTests(unittest.TestCase):
    def setUp(self):
        self.mapper = MAPPER.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_mapper_exposes_4k_and_2m_primitives(self):
        self.assertIn("pub fn page_table_map_4k", self.mapper)
        self.assertIn("pub fn page_table_map_2m", self.mapper)
        self.assertIn("X86_PAGE_SIZE_2M", self.mapper)
        self.assertIn("X86_PTE_HUGE", self.mapper)

    def test_mapper_reopens_children_only_through_arena(self):
        self.assertIn("page_table_arena_page_from_physical", self.mapper)
        self.assertIn("x86_pte_address(current)", self.mapper)
        self.assertIn("page_table_arena_alloc(arena)", self.mapper)
        self.assertIn("page_table_zero(child)", self.mapper)

    def test_mapper_is_idempotent_but_rejects_conflicting_remap(self):
        self.assertIn("if x86_pte_present(current)", self.mapper)
        self.assertIn("return current == desired;", self.mapper)

    def test_4k_mapping_clears_huge_and_2m_sets_huge(self):
        self.assertIn("(flags | X86_PTE_PRESENT) & ~X86_PTE_HUGE", self.mapper)
        self.assertIn("flags | X86_PTE_PRESENT | X86_PTE_HUGE", self.mapper)

    def test_mapper_does_not_own_policy_or_activate_mmu(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.mapper.splitlines())
        for token in (
            "__write_cr3", "write_cr3", "__invlpg", "pmm_alloc_page(",
            "pmm_alloc_pages(", "ExitBootServices", "AllocatePages",
            "framebuffer_base", "ECAM", "MMIO",
        ):
            self.assertNotIn(token, code)

    def test_hybrid_main_only_registers_mapper(self):
        self.assertIn("import kernel::memory::page_table_mapper::*;", self.main)
        for token in ("page_table_map_4k(", "page_table_map_2m(", "write_cr3"):
            self.assertNotIn(token, self.main)


if __name__ == "__main__":
    unittest.main()
