#!/usr/bin/env python3
"""Guardrails dos helpers PAT para PTEs 4 KiB."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAT = ROOT / "kernel" / "src" / "arch" / "x86_64" / "pat.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class PatFoundationTests(unittest.TestCase):
    def setUp(self):
        self.pat = PAT.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_pat_index_uses_pwt_pcd_pat_bits(self):
        self.assertIn("X86_PAT_PWT_BIT", self.pat)
        self.assertIn("X86_PAT_PCD_BIT", self.pat)
        self.assertIn("X86_PAT_PTE_BIT: u64 = 1 << 7", self.pat)
        self.assertIn("if (index & 1) != 0", self.pat)
        self.assertIn("if (index & 2) != 0", self.pat)
        self.assertIn("if (index & 4) != 0", self.pat)

    def test_all_eight_indices_are_representable(self):
        self.assertIn("X86_PAT_INDEX_COUNT: u8 = 8", self.pat)
        self.assertIn("pub fn x86_pat_index_valid", self.pat)
        self.assertIn("pub fn x86_pat_index_from_pte", self.pat)

    def test_pat_module_does_not_program_ia32_pat(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.pat.splitlines())
        for token in ("__wrmsr", "wrmsr", "0x277", "IA32_PAT"):
            self.assertNotIn(token, code)

    def test_hybrid_main_does_not_enable_wc(self):
        self.assertIn("x86_pat_index_valid(0);", self.main)
        for token in ("framebuffer_wc_active = true", "vmm_activate(", "__wrmsr"):
            self.assertNotIn(token, self.main)


if __name__ == "__main__":
    unittest.main()
