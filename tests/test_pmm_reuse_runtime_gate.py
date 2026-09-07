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
        self.assertIn("let failure_stage = pmm_allocator_reuse_self_test_failure_stage();", activate)
        self.assertIn("PMM_REUSE_SELF_TEST_FAILURE_STAGE = failure_stage", activate)
        self.assertIn("PMM_REUSE_SELF_TEST_PASSED = true", activate)

    def test_reuse_self_test_has_persistent_failure_stage(self):
        text = ALLOC.read_text(encoding="utf-8")
        self.assertIn("PMM_REUSE_SELF_TEST_FAILURE_STAGE", text)
        self.assertIn("pmm_allocator_reuse_self_test_failure_stage() -> u32", text)
        body = text.split("fn pmm_allocator_self_test_reuse() -> bool", 1)[1].split(
            "pub fn pmm_allocator_activate_after_exit_boot_services", 1
        )[0]
        for stage in range(2, 9):
            self.assertIn(f"PMM_REUSE_SELF_TEST_FAILURE_STAGE = {stage}", body)

    def test_stage_p_is_emitted_only_after_allocator_activation_returns(self):
        post = POST.read_text(encoding="utf-8")
        entry = post.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        activate = entry.index("post_cutover_activate_pmm(context)")
        marker = entry.index("x86_serial_write_stage_marker('P' as u8)", activate)
        vmm = entry.index("post_cutover_activate_vmm(context)", marker)
        self.assertLess(activate, marker)
        self.assertLess(marker, vmm)

    def test_pmm_entry_reports_inventory_or_reuse_failure_to_serial(self):
        post = POST.read_text(encoding="utf-8")
        body = post.split("pub fn post_cutover_activate_pmm", 1)[1].split(
            "pub fn post_cutover_pmm_active", 1
        )[0]
        self.assertIn("x86_serial_write_stage_marker('p' as u8)", body)
        self.assertIn("x86_serial_write_stage_marker('q' as u8)", body)
        self.assertIn("x86_serial_write_stage_marker('r' as u8)", body)
        self.assertIn("x86_serial_write_hex32_marker('P' as u8, 1)", body)
        self.assertIn("pmm_allocator_reuse_self_test_failure_stage()", body)


if __name__ == "__main__":
    unittest.main()
