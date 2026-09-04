#!/usr/bin/env python3
"""Guardrails da porta fail-closed que futuramente abre STI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "kernel/src/interrupts/interrupt_enable.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
CPU = ROOT / "kernel/src/arch/x86_64/cpu.sotlas"


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

    def test_post_cutover_does_not_invoke_gate_yet(self):
        text = POST.read_text(encoding="utf-8")
        self.assertIn("import kernel::interrupts::interrupt_enable::*;", text)
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        code = "\n".join(line.split("//", 1)[0] for line in body.splitlines())
        self.assertNotIn("interrupt_enable_timer_only()", code)
        self.assertNotIn("x86_sti_raw()", code)


if __name__ == "__main__":
    unittest.main()
