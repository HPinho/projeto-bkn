#!/usr/bin/env python3
"""Guardrails do VMM fail-closed."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VMM = ROOT / "kernel" / "src" / "memory" / "vmm.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"
POST = ROOT / "kernel" / "src" / "arch" / "x86_64" / "post_cutover.sotlas"


class VmmFoundationTests(unittest.TestCase):
    def setUp(self):
        self.vmm = VMM.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")
        self.post = POST.read_text(encoding="utf-8")

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
        for token in ("__wrmsr", "IA32_PAT", "0x277", "__write_cr3", "x86_write_cr3_raw"):
            self.assertNotIn(token, code)

    def test_activation_requires_current_cpu_root_to_match_registered_root(self):
        self.assertIn("pub fn vmm_activate_current_tables", self.vmm)
        body = self.vmm.split("pub fn vmm_activate_current_tables", 1)[1].split("pub fn vmm_root_table_physical", 1)[0]
        self.assertIn("vmm_mark_tables_ready(root_table_physical, direct_map_base)", body)
        self.assertIn("x86_mmu_current_root() != root_table_physical", body)
        self.assertIn("VMM.state = VMM_STATE_ACTIVE", body)
        self.assertIn("VMM.state = VMM_STATE_OFFLINE", body)

    def test_hybrid_main_never_activates_vmm_but_post_cutover_does(self):
        self.assertIn("vmm_is_active();", self.main)
        self.assertNotIn("vmm_mark_tables_ready(", self.main)
        self.assertNotIn("vmm_activate_current_tables(", self.main)
        self.assertNotIn("write_cr3", self.main)

        self.assertIn("post_cutover_activate_vmm", self.post)
        self.assertIn("vmm_activate_current_tables(context.root_physical, BAKEN_DIRECT_MAP_BASE)", self.post)
        self.assertIn("if !post_cutover_pmm_active()", self.post)


if __name__ == "__main__":
    unittest.main()
