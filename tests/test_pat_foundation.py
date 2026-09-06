#!/usr/bin/env python3
"""Guardrails dos helpers PAT para PTEs 4 KiB e framebuffer WC pós-cutover."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]; PAT=ROOT/"kernel/src/arch/x86_64/pat.sotlas"; POST=ROOT/"kernel/src/arch/x86_64/post_cutover.sotlas"
class PatFoundationTests(unittest.TestCase):
    def setUp(self): self.pat=PAT.read_text(encoding="utf-8"); self.post=POST.read_text(encoding="utf-8")
    def test_pat_index_uses_pwt_pcd_pat_bits(self):
        for token in ("X86_PAT_PWT_BIT","X86_PAT_PCD_BIT","X86_PAT_PTE_BIT: u64 = 1 << 7","if (index & 1) != 0","if (index & 2) != 0","if (index & 4) != 0"): self.assertIn(token,self.pat)
    def test_all_eight_indices_are_representable(self):
        for token in ("X86_PAT_INDEX_COUNT: u8 = 8","pub fn x86_pat_index_valid","pub fn x86_pat_index_from_pte"): self.assertIn(token,self.pat)
    def test_pat_helper_module_does_not_program_ia32_pat_directly(self):
        code="\n".join(line.split("//",1)[0] for line in self.pat.splitlines())
        for token in ("__wrmsr","wrmsr","0x277","IA32_PAT"): self.assertNotIn(token,code)
    def test_post_cutover_enables_framebuffer_wc_only_after_storage_foundations(self):
        entry=self.post.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !",1)[1]; nvme=entry.index("foundation_nvme_probe()"); wc=entry.index("active_framebuffer_write_combining(",nvme); ready=entry.index("x86_serial_write_bare_metal_ready_marker()",wc)
        self.assertLess(nvme,wc); self.assertLess(wc,ready)
if __name__ == "__main__": unittest.main()
