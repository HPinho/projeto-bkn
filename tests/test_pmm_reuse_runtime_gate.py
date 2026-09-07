#!/usr/bin/env python3
"""A etapa P do boot deve depender da autocertificação de reutilização física."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ALLOC = ROOT / "kernel/src/memory/pmm_allocator.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class PmmReuseRuntimeGateTests(unittest.TestCase):
    def test_activation_is_fail_closed_on_reuse_self_test(self):
        text = ALLOC.read_text(encoding="utf-8")
        activate = text.split("pub fn pmm_allocator_activate_after_exit_boot_services", 1)[1]
        self.assertIn("if !pmm_allocator_self_test_reuse()", activate)
        self.assertIn("pmm_allocator_reset_locked();", activate)
        self.assertIn("PMM_REUSE_SELF_TEST_PASSED = true", activate)

    def test_stage_p_is_emitted_only_after_allocator_activation_returns(self):
        post = POST.read_text(encoding="utf-8")
        entry = post.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        activate = entry.index("post_cutover_activate_pmm(context)")
        marker = entry.index("x86_serial_write_stage_marker('P' as u8)", activate)
        vmm = entry.index("post_cutover_activate_vmm(context)", marker)
        self.assertLess(activate, marker)
        self.assertLess(marker, vmm)


if __name__ == "__main__":
    unittest.main()
