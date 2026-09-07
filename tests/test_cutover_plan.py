#!/usr/bin/env python3
"""Retirement guard for the obsolete hybrid cutover plan."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class CutoverPlanRetirementTests(unittest.TestCase):
    def test_hybrid_cutover_plan_module_is_retired(self):
        self.assertFalse((ROOT / "kernel/src/memory/cutover_plan.sotlas").exists())
        main = MAIN.read_text(encoding="utf-8")
        self.assertNotIn("kernel::memory::cutover_plan", main)
        self.assertNotIn("cutover_plan_", main)

    def test_canonical_post_cutover_path_reaches_native_runtime(self):
        post = POST.read_text(encoding="utf-8")
        self.assertIn("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", post)
        self.assertIn("x86_serial_write_bare_metal_ready_marker()", post)
        self.assertIn("baken_native_kernel_run(", post)
        self.assertLess(post.index("x86_serial_write_bare_metal_ready_marker()"), post.index("baken_native_kernel_run("))


if __name__ == "__main__": unittest.main()
