#!/usr/bin/env python3
"""Guardrails do plano histórico de cutover e da rota canônica pós-cutover."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "kernel/src/memory/cutover_plan.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
def code_without_line_comments(text: str) -> str: return "\n".join(line.split("//",1)[0] for line in text.splitlines())
class CutoverPlanTests(unittest.TestCase):
    def test_hybrid_plan_is_fail_closed(self):
        text=PLAN.read_text(encoding="utf-8"); body=text.split("pub fn cutover_plan_blocked_hybrid",1)[1].split("pub fn cutover_plan_ready",1)[0]
        self.assertIn("uefi_bridge_active: true",body)
        for field in ("handoff_valid","final_memory_map_ready","page_tables_ready","transition_image_ready","transition_stack_ready","native_timer_ready","native_input_ready","native_storage_ready"): self.assertIn(f"{field}: false",body)
    def test_core_cutover_requires_all_runtime_preconditions_except_storage(self):
        text=PLAN.read_text(encoding="utf-8"); body=text.split("pub fn cutover_plan_ready",1)[1].split("pub fn cutover_native_foundation_ready",1)[0]
        self.assertIn("if plan.uefi_bridge_active { return false; }",body)
        for field in ("handoff_valid","final_memory_map_ready","page_tables_ready","transition_image_ready","transition_stack_ready","native_timer_ready","native_input_ready"): self.assertIn(f"if !plan.{field} {{ return false; }}",body)
        self.assertNotIn("if !plan.native_storage_ready",body); self.assertIn("return true;",body)
    def test_full_native_foundation_adds_storage_requirement(self):
        body=PLAN.read_text(encoding="utf-8").split("pub fn cutover_native_foundation_ready",1)[1]
        self.assertIn("if !cutover_plan_ready(plan) { return false; }",body); self.assertIn("if !plan.native_storage_ready { return false; }",body); self.assertIn("return true;",body)
    def test_plan_has_no_privileged_or_firmware_side_effects(self):
        code=code_without_line_comments(PLAN.read_text(encoding="utf-8"))
        for token in ("ExitBootServices","GetMemoryMap","__write_cr3","x86_write_cr3","__invlpg","__wrmsr","BootServices","MMIO"): self.assertNotIn(token,code)
    def test_hybrid_plan_is_not_reachable_from_canonical_runtime_path(self):
        main=code_without_line_comments(MAIN.read_text(encoding="utf-8")); post=code_without_line_comments(POST.read_text(encoding="utf-8"))
        self.assertNotIn("cutover_plan_blocked_hybrid",main); self.assertNotIn("cutover_plan_ready(",main); self.assertNotIn("cutover_plan_blocked_hybrid",post)
        self.assertIn("sotlas_x86_post_cutover_entry",post); self.assertIn("baken_native_kernel_run(",post)
if __name__ == "__main__": unittest.main()
