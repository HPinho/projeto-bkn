#!/usr/bin/env python3
"""Guardrails do plano Sotlas para o futuro ExitBootServices."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "kernel/src/memory/cutover_plan.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class CutoverPlanTests(unittest.TestCase):
    def test_hybrid_plan_is_fail_closed(self):
        text = PLAN.read_text(encoding="utf-8")
        body = text.split("pub fn cutover_plan_blocked_hybrid", 1)[1].split("pub fn cutover_plan_ready", 1)[0]
        self.assertIn("uefi_bridge_active: true", body)
        for field in (
            "handoff_valid", "final_memory_map_ready", "page_tables_ready",
            "transition_image_ready", "transition_stack_ready", "native_timer_ready",
            "native_input_ready", "native_storage_ready",
        ):
            self.assertIn(f"{field}: false", body)

    def test_ready_requires_every_precondition(self):
        text = PLAN.read_text(encoding="utf-8")
        body = text.split("pub fn cutover_plan_ready", 1)[1]
        self.assertIn("if plan.uefi_bridge_active { return false; }", body)
        for field in (
            "handoff_valid", "final_memory_map_ready", "page_tables_ready",
            "transition_image_ready", "transition_stack_ready", "native_timer_ready",
            "native_input_ready", "native_storage_ready",
        ):
            self.assertIn(f"if !plan.{field} {{ return false; }}", body)
        self.assertIn("return true;", body)

    def test_plan_has_no_privileged_or_firmware_side_effects(self):
        text = PLAN.read_text(encoding="utf-8")
        for token in (
            "ExitBootServices", "GetMemoryMap", "__write_cr3", "x86_write_cr3",
            "__invlpg", "__wrmsr", "BootServices", "MMIO",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def test_main_only_evaluates_blocked_hybrid_plan(self):
        main = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::memory::cutover_plan::*;", main)
        self.assertIn("cutover_plan_ready(cutover_plan_blocked_hybrid());", main)
        self.assertNotIn("ExitBootServices", main)
        self.assertNotIn("x86_write_cr3", main)


if __name__ == "__main__":
    unittest.main()
