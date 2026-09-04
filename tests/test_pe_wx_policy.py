#!/usr/bin/env python3
"""Guardrails da política W^X aplicada às seções PE32+."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "kernel/src/memory/pe_wx_policy.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class PeWxPolicyTests(unittest.TestCase):
    def setUp(self):
        self.text = POLICY.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_write_execute_is_rejected(self):
        self.assertIn("if section.writable && section.executable { return false; }", self.text)
        self.assertIn("if !pe_section_wx_safe(section) { return 0; }", self.text)

    def test_writable_data_becomes_rw_nx(self):
        body = self.text.split("pub fn pe_section_pte_flags", 1)[1]
        self.assertIn("if section.writable { flags |= X86_PTE_WRITABLE; }", body)
        self.assertIn("if !section.executable { flags |= X86_PTE_NX; }", body)

    def test_executable_code_is_not_writable_by_default(self):
        body = self.text.split("pub fn pe_section_pte_flags", 1)[1]
        self.assertIn("let mut flags = X86_PTE_PRESENT;", body)
        self.assertNotIn("flags = X86_PTE_PRESENT | X86_PTE_WRITABLE", body)

    def test_headers_are_present_read_only_nx(self):
        body = self.text.split("pub fn pe_header_pte_flags", 1)[1]
        self.assertIn("X86_PTE_PRESENT | X86_PTE_NX", body)
        self.assertNotIn("X86_PTE_WRITABLE", body)

    def test_policy_has_no_side_effects(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.text.splitlines())
        for token in (
            "page_table_map_4k", "page_table_map_2m", "x86_write_cr3", "__write_cr3",
            "ExitBootServices", "GetMemoryMap", "AllocatePages", "pmm_alloc_page(",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_main_registers_policy_without_using_it_in_hybrid_boot(self):
        self.assertIn("import kernel::memory::pe_wx_policy::*;", self.main)
        self.assertNotIn("pe_section_pte_flags(", self.main)
        self.assertNotIn("pe_header_pte_flags(", self.main)


if __name__ == "__main__":
    unittest.main()
