#!/usr/bin/env python3
"""Guardrails do VMM fail-closed."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VMM = ROOT / "kernel" / "src" / "memory" / "vmm.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class VmmFoundationTests(unittest.TestCase):
    def setUp(self):
        self.vmm = VMM.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_vmm_is_offline_by_default(self):
        self.assertIn("state: VMM_STATE_OFFLINE", self.vmm)
        self.assertIn("pub fn vmm_is_active() -> bool", self.vmm)

    def test_mapping_contract_validates_alignment_and_overflow(self):
        self.assertIn("pub fn vmm_mapping_make", self.vmm)
        self.assertIn("x86_page_aligned(virtual_base)", self.vmm)
        self.assertIn("x86_page_aligned(physical_base)", self.vmm)
        self.assertIn("if page_count == 0", self.vmm)
        self.assertIn("if virtual_end <= virtual_base || physical_end <= physical_base", self.vmm)

    def test_cache_policies_exist_without_pat_programming(self):
        for name in (
            "VMM_CACHE_WRITE_BACK",
            "VMM_CACHE_WRITE_COMBINING",
            "VMM_CACHE_UNCACHED",
        ):
            self.assertIn(name, self.vmm)
        code = "\n".join(line.split("//", 1)[0] for line in self.vmm.splitlines())
        for token in ("__wrmsr", "IA32_PAT", "0x277", "write_cr3", "__invlpg"):
            self.assertNotIn(token, code)

    def test_hybrid_main_must_not_mark_tables_ready_or_activate(self):
        self.assertIn("vmm_is_active();", self.main)
        self.assertNotIn("vmm_mark_tables_ready(", self.main)
        self.assertNotIn("vmm_activate(", self.main)
        self.assertNotIn("write_cr3", self.main)


if __name__ == "__main__":
    unittest.main()
