#!/usr/bin/env python3
"""Guardrails DF-9c4: runtime PAT capability probe."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "kernel/src/memory/mmio_pat_policy.sotlas"
PAT = ROOT / "kernel/src/arch/x86_64/pat.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class MmioPatPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = POLICY.read_text(encoding="utf-8")
        cls.pat = PAT.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_probe_module_is_in_native_graph(self):
        self.assertIn("import kernel::memory::mmio_pat_policy::*;", self.main)

    def test_probe_reads_pat_without_programming_it(self):
        self.assertIn("IA32_PAT_MSR: u32 = 0x277", self.text)
        self.assertIn("x86_read_msr(IA32_PAT_MSR)", self.text)
        self.assertNotIn("x86_write_msr", self.text)
        self.assertNotIn("__wrmsr", self.text)

    def test_memory_type_catalog_covers_mmio_contract(self):
        for token in (
            "PAT_MEMORY_TYPE_UC: u8 = 0x00",
            "PAT_MEMORY_TYPE_WC: u8 = 0x01",
            "PAT_MEMORY_TYPE_WT: u8 = 0x04",
            "PAT_MEMORY_TYPE_WB: u8 = 0x06",
            "MMIO_PAT_INDEX_INVALID: u8 = 0xFF",
        ):
            self.assertIn(token, self.text)

    def test_index_search_is_runtime_value_driven_not_hardcoded(self):
        body = self.text.split("pub fn mmio_pat_find_index_in_value", 1)[1].split(
            "@system", 1
        )[0]
        self.assertIn("while index < X86_PAT_INDEX_COUNT", body)
        self.assertIn("mmio_pat_entry_type(pat, index) == memory_type", body)
        self.assertNotIn("return 0;", body)
        self.assertNotIn("return 1;", body)
        self.assertNotIn("return 7;", body)

    def test_arch_pat_helper_remains_pure(self):
        code = "\n".join(
            line.split("//", 1)[0] for line in self.pat.splitlines()
        )
        for token in ("x86_read_msr", "x86_write_msr", "__rdmsr", "__wrmsr", "0x277"):
            self.assertNotIn(token, code)


if __name__ == "__main__":
    unittest.main()
