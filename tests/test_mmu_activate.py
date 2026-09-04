#!/usr/bin/env python3
"""Guardrails da ativação CR3 pós-cutover."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MMU = ROOT / "kernel/src/memory/mmu_activate.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class MmuActivateTests(unittest.TestCase):
    def setUp(self):
        self.text = MMU.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_root_must_be_nonzero_aligned_and_representable(self):
        self.assertIn("if root_physical == 0 { return false; }", self.text)
        self.assertIn("if !x86_page_aligned(root_physical) { return false; }", self.text)
        self.assertIn("(root_physical & ~X86_PAGE_ADDRESS_MASK) != 0", self.text)

    def test_activation_writes_cr3_and_verifies_readback(self):
        self.assertIn("x86_write_cr3_raw(root_physical);", self.text)
        self.assertIn("return x86_mmu_current_root() == root_physical;", self.text)
        self.assertIn("x86_read_cr3_raw() & X86_PAGE_ADDRESS_MASK", self.text)

    def test_module_does_not_hide_other_cutover_side_effects(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.text.splitlines())
        for token in (
            "ExitBootServices", "GetMemoryMap", "x86_lgdt_raw", "x86_lidt_raw",
            "x86_ltr_raw", "__sti", "__cli", "AllocatePages", "BootServices",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, code)

    def test_hybrid_kernel_only_imports_activation_mechanism(self):
        self.assertIn("import kernel::memory::mmu_activate::*;", self.main)
        body = self.main.split("pub fn baken_kernel_main", 1)[1]
        self.assertNotIn("x86_mmu_activate_root(", body)
        self.assertNotIn("x86_write_cr3_raw(", body)


if __name__ == "__main__":
    unittest.main()
