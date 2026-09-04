#!/usr/bin/env python3
"""Guardrails da entrada x86-64 depois de ExitBootServices."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def code_without_comments(text: str) -> str:
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


class PostCutoverEntryTests(unittest.TestCase):
    def test_entry_is_real_export_and_registered_in_graph(self):
        text = POST.read_text(encoding="utf-8")
        main = MAIN.read_text(encoding="utf-8")
        self.assertIn("@export\npub fn sotlas_x86_post_cutover_entry", text)
        self.assertIn("import kernel::arch::x86_64::post_cutover::*;", main)
        main_body = main.split("pub fn baken_kernel_main", 1)[1]
        self.assertNotIn("sotlas_x86_post_cutover_entry(", main_body)
        self.assertNotIn("post_cutover_activate_cpu(", main_body)

    def test_cpu_activation_order_is_cr3_gdt_ltr_lidt(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_activate_cpu", 1)[1].split("pub fn post_cutover_cpu_tables_active", 1)[0]
        cr3 = body.index("x86_mmu_activate(context.root_physical)")
        gdt = body.index("x86_gdt_activate_segments_raw(")
        ltr = body.index("x86_ltr_raw(GDT_TSS_SELECTOR)")
        lidt = body.index("x86_lidt_table_raw(idt_address, idt_limit())")
        self.assertLess(cr3, gdt)
        self.assertLess(gdt, ltr)
        self.assertLess(ltr, lidt)

    def test_tss_and_exception_stubs_are_ready_before_activation(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_activate_cpu", 1)[1].split("pub fn post_cutover_cpu_tables_active", 1)[0]
        self.assertLess(body.index("tss_prepare_default_stacks()"), body.index("x86_ltr_raw(GDT_TSS_SELECTOR)"))
        self.assertLess(body.index("idt_prepare_exceptions()"), body.index("x86_lidt_table_raw(idt_address, idt_limit())"))
        self.assertIn("tss_is_prepared()", body)
        self.assertIn("idt_exceptions_ready()", body)

    def test_interrupts_remain_disabled_in_this_phase(self):
        code = code_without_comments(POST.read_text(encoding="utf-8"))
        for token in ("__sti(", "x86_sti", "sti("):
            with self.subTest(token=token):
                self.assertNotIn(token, code)


if __name__ == "__main__":
    unittest.main()
