#!/usr/bin/env python3
"""Guardrails da porta fail-closed que abre somente o LAPIC timer."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "kernel/src/interrupts/interrupt_enable.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
CPU = ROOT / "kernel/src/arch/x86_64/cpu.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"


class InterruptEnableGateTests(unittest.TestCase):
    def test_cpu_exposes_explicit_cli_sti_wrappers(self):
        text = CPU.read_text(encoding="utf-8")
        self.assertIn("pub fn x86_cli_raw()", text)
        self.assertIn("pub fn x86_sti_raw()", text)
        self.assertIn("__cli();", text)
        self.assertIn("__sti();", text)

    def test_gate_requires_all_irq_timer_prerequisites(self):
        text = GATE.read_text(encoding="utf-8")
        for token in (
            "lapic_is_ready()", "ioapic_is_ready()", "irq_idt_ready()",
            "irq_routes_ready()", "lapic_timer_is_ready()",
        ):
            self.assertIn(token, text)
        self.assertLess(text.index("x86_cli_raw()"), text.index("lapic_timer_unmask_periodic()"))
        self.assertLess(text.index("lapic_timer_unmask_periodic()"), text.index("x86_sti_raw()"))

    def test_timer_dispatch_counts_and_acknowledges(self):
        text = IRQ.read_text(encoding="utf-8")
        body = text.split("if vector == IRQ_VECTOR_TIMER as u64", 1)[1].split(
            "if vector == IRQ_VECTOR_KEYBOARD as u64", 1
        )[0]
        self.assertIn("IRQ_TIMER_COUNT += 1", body)
        self.assertIn("lapic_eoi();", body)
        self.assertLess(body.index("IRQ_TIMER_COUNT += 1"), body.index("lapic_eoi();"))

    def test_post_cutover_opens_only_timer_and_requires_observed_tick(self):
        text = POST.read_text(encoding="utf-8")
        self.assertIn("pub fn post_cutover_enable_timer_interrupts()", text)
        body = text.split("pub fn post_cutover_enable_timer_interrupts()", 1)[1].split(
            "pub fn sotlas_x86_post_cutover_entry", 1
        )[0]
        self.assertIn("let before = irq_timer_count();", body)
        self.assertIn("interrupt_enable_timer_only()", body)
        self.assertIn("irq_timer_count() != before", body)
        self.assertIn("interrupt_disable_all();", body)
        self.assertIn("POST_CUTOVER_TIMER_LIVE = true", body)

    def test_entry_emits_live_marker_only_after_tick_proof(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        enable = body.index("post_cutover_enable_timer_interrupts()")
        marker = body.index("x86_serial_write_stage_marker('T' as u8)")
        self.assertLess(enable, marker)


if __name__ == "__main__":
    unittest.main()
