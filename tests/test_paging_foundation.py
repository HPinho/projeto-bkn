#!/usr/bin/env python3
"""Guardrails dos contratos puros de paging x86-64."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGING = ROOT / "kernel" / "src" / "arch" / "x86_64" / "paging.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class PagingFoundationTests(unittest.TestCase):
    def setUp(self):
        self.paging = PAGING.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_four_level_indices_exist(self):
        for name, shift in (
            ("x86_pml4_index", "39"),
            ("x86_pdpt_index", "30"),
            ("x86_pd_index", "21"),
            ("x86_pt_index", "12"),
        ):
            self.assertIn(f"pub fn {name}", self.paging)
            self.assertIn(f">> {shift}", self.paging)
        self.assertIn("X86_PAGE_INDEX_MASK: u64 = 0x1FF", self.paging)

    def test_4k_page_contract_and_address_mask(self):
        self.assertIn("X86_PAGE_SIZE: u64 = 4096", self.paging)
        self.assertIn("X86_PAGE_ADDRESS_MASK: u64 = 0x000FFFFFFFFFF000", self.paging)
        self.assertIn("pub fn x86_pte_make", self.paging)
        self.assertIn("pub fn x86_pte_address", self.paging)

    def test_core_pte_flags_exist(self):
        for flag in (
            "X86_PTE_PRESENT", "X86_PTE_WRITABLE", "X86_PTE_USER",
            "X86_PTE_WRITE_THROUGH", "X86_PTE_CACHE_DISABLE",
            "X86_PTE_HUGE", "X86_PTE_GLOBAL", "X86_PTE_NX",
        ):
            self.assertIn(flag, self.paging)

    def test_paging_module_does_not_activate_mmu(self):
        code = "\n".join(
            line.split("//", 1)[0] for line in self.paging.splitlines()
        )
        for token in ("__write_cr3", "write_cr3", "mov %", "invlpg(", "__invlpg"):
            self.assertNotIn(token, code)

    def test_hybrid_main_only_uses_pure_helper(self):
        self.assertIn("x86_page_aligned(X86_PAGE_SIZE);", self.main)
        for token in ("write_cr3", "vmm_activate", "pmm_allocator_activate_after_exit_boot_services();"):
            self.assertNotIn(token, self.main)


if __name__ == "__main__":
    unittest.main()
