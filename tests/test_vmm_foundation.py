#!/usr/bin/env python3
"""Guardrails do VMM fail-closed."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]; VMM=ROOT/"kernel/src/memory/vmm.sotlas"; POST=ROOT/"kernel/src/arch/x86_64/post_cutover.sotlas"
class VmmFoundationTests(unittest.TestCase):
    def setUp(self): self.vmm=VMM.read_text(encoding="utf-8"); self.post=POST.read_text(encoding="utf-8")
    def test_vmm_is_offline_by_default(self): self.assertIn("state: VMM_STATE_OFFLINE",self.vmm); self.assertIn("pub fn vmm_is_active() -> bool",self.vmm)
    def test_mapping_contract_validates_alignment_and_overflow(self):
        for token in ("pub fn vmm_mapping_make","x86_page_aligned(virtual_base)","x86_page_aligned(physical_base)","if page_count == 0","if virtual_end <= virtual_base || physical_end <= physical_base"): self.assertIn(token,self.vmm)
    def test_cache_policies_exist_without_pat_programming(self):
        for name in ("VMM_CACHE_WRITE_BACK","VMM_CACHE_WRITE_COMBINING","VMM_CACHE_UNCACHED"): self.assertIn(name,self.vmm)
        code="\n".join(line.split("//",1)[0] for line in self.vmm.splitlines())
        for token in ("__wrmsr","IA32_PAT","0x277","__write_cr3","x86_write_cr3_raw"): self.assertNotIn(token,code)
    def test_activation_requires_current_cpu_root_to_match_registered_root(self):
        body=self.vmm.split("pub fn vmm_activate_current_tables",1)[1].split("pub fn vmm_root_table_physical",1)[0]
        for token in ("vmm_mark_tables_ready(root_table_physical, direct_map_base)","x86_mmu_current_root() != root_table_physical","VMM.state = VMM_STATE_ACTIVE","VMM.state = VMM_STATE_OFFLINE"): self.assertIn(token,body)
    def test_post_cutover_activates_vmm_only_after_pmm(self):
        body=self.post.split("pub fn post_cutover_activate_vmm",1)[1].split("pub fn post_cutover_vmm_active",1)[0]
        for token in ("if !post_cutover_pmm_active()","vmm_activate_current_tables(snapshot.root_physical, BAKEN_DIRECT_MAP_BASE)","active_page_tables_resume(","active_page_tables_is_ready()"): self.assertIn(token,body)
if __name__ == "__main__": unittest.main()
