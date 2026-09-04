#!/usr/bin/env python3
"""Guardrails do mapping PE W^X de transição."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAPPER = ROOT / "kernel/src/memory/transition_image_wx.sotlas"
POLICY = ROOT / "kernel/src/memory/pe_wx_policy.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class TransitionImageWxTests(unittest.TestCase):
    def setUp(self):
        self.mapper = MAPPER.read_text(encoding="utf-8")
        self.policy = POLICY.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_policy_rejects_writable_executable_sections(self):
        self.assertIn("if section.writable && section.executable { return false; }", self.policy)
        self.assertIn("if !pe_section_wx_safe(section)", self.mapper)

    def test_headers_are_read_only_and_nx(self):
        self.assertIn("return X86_PTE_PRESENT | X86_PTE_NX;", self.policy)
        self.assertIn("pe_header_pte_flags()", self.mapper)

    def test_mapper_uses_pe_section_permissions(self):
        self.assertIn("let flags = pe_section_pte_flags(section);", self.mapper)
        self.assertIn("transition_map_range(", self.mapper)
        self.assertIn("sections_mapped == image.section_count", self.mapper)

    def test_mapper_has_no_cutover_side_effects(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.mapper.splitlines())
        for token in (
            "ExitBootServices", "GetMemoryMap", "__write_cr3", "x86_write_cr3",
            "__invlpg", "__wrmsr", "BootServices", "AllocatePages",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_hybrid_main_registers_but_never_calls_mapper(self):
        self.assertIn("import kernel::memory::transition_image_wx::*;", self.main)
        body = self.main.split("pub fn baken_kernel_main", 1)[1]
        self.assertNotIn("transition_image_map_wx(", body)


if __name__ == "__main__":
    unittest.main()
