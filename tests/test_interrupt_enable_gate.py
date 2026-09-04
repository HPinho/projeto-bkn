#!/usr/bin/env python3
"""Guardrails da habilitação progressiva de interrupções pós-cutover."""

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

    def test_timer_gate_requires_prerequisites_and_orders_cli_unmask_sti(self):
        text = GATE.read_text(encoding="utf-8")
        body = text.split("pub fn interrupt_enable_timer_only()", 1)[1].split(
            "pub fn interrupt_enable_keyboard_after_timer()", 1
        )[0]
        for token in (
            "lapic_is_ready()", "ioapic_is_ready()", "irq_idt_ready()",
            "irq_routes_ready()", "lapic_timer_is_ready()",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("x86_cli_raw()"), body.index("lapic_timer_unmask_periodic()"))
        self.assertLess(body.index("lapic_timer_unmask_periodic()"), body.index("x86_sti_raw()"))

    def test_timer_dispatch_counts_and_acknowledges(self):
        text = IRQ.read_text(encoding="utf-8")
        body = text.split("if vector == IRQ_VECTOR_TIMER as u64", 1)[1].split(
            "if vector == IRQ_VECTOR_KEYBOARD as u64", 1
        )[0]
        self.assertIn("IRQ_TIMER_COUNT += 1", body)
        self.assertIn("lapic_eoi();", body)
        self.assertLess(body.index("IRQ_TIMER_COUNT += 1"), body.index("lapic_eoi();"))

    def test_keyboard_dispatch_drains_counts_and_acknowledges(self):
        text = IRQ.read_text(encoding="utf-8")
        body = text.split("if vector == IRQ_VECTOR_KEYBOARD as u64", 1)[1].split(
            "if vector == IRQ_VECTOR_MOUSE as u64", 1
        )[0]
        self.assertIn("i8042_drain_irq_output();", body)
        self.assertIn("IRQ_KEYBOARD_COUNT += 1", body)
        self.assertIn("lapic_eoi();", body)
        self.assertLess(body.index("i8042_drain_irq_output();"), body.index("lapic_eoi();"))

    def test_post_cutover_requires_observed_timer_tick(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_enable_timer_interrupts()", 1)[1].split(
            "pub fn post_cutover_enable_keyboard_interrupts()", 1
        )[0]
        self.assertIn("let before = irq_timer_count();", body)
        self.assertIn("interrupt_enable_timer_only()", body)
        self.assertIn("irq_timer_count() != before", body)
        self.assertIn("interrupt_disable_all();", body)
        self.assertIn("POST_CUTOVER_TIMER_LIVE = true", body)

    def test_keyboard_gate_requires_timer_live_state_and_first_port(self):
        text = GATE.read_text(encoding="utf-8")
        body = text.split("pub fn interrupt_enable_keyboard_after_timer()", 1)[1].split(
            "pub fn keyboard_interrupt_enabled()", 1
        )[0]
        self.assertIn("!EXTERNAL_INTERRUPTS_ENABLED", body)
        self.assertIn("lapic_timer_is_ready()", body)
        self.assertIn("i8042_initialize_polling()", body)
        self.assertIn("i8042_first_port_present()", body)
        self.assertIn("interrupt_route_keyboard(IRQ_VECTOR_KEYBOARD)", body)
        self.assertLess(body.index("x86_cli_raw()"), body.index("i8042_initialize_polling()"))

    def test_keyboard_route_is_changed_under_cli_and_only_irq1_is_unmasked(self):
        text = GATE.read_text(encoding="utf-8")
        body = text.split("pub fn interrupt_enable_keyboard_after_timer()", 1)[1].split(
            "pub fn keyboard_interrupt_enabled()", 1
        )[0]
        self.assertLess(body.index("x86_cli_raw()"), body.index("ioapic_program_route_unmasked"))
        self.assertLess(body.index("ioapic_program_route_unmasked"), body.rindex("x86_sti_raw()"))
        self.assertNotIn("interrupt_route_ps2_mouse", body)
        self.assertNotIn("IRQ_VECTOR_MOUSE", body)

    def test_keyboard_enable_rolls_back_on_ioapic_failure(self):
        text = GATE.read_text(encoding="utf-8")
        body = text.split("pub fn interrupt_enable_keyboard_after_timer()", 1)[1].split(
            "pub fn keyboard_interrupt_enabled()", 1
        )[0]
        self.assertIn("i8042_disable_native_irqs();", body)
        self.assertIn("ioapic_program_route_masked(&keyboard, destination);", body)

    def test_post_cutover_requires_observed_keyboard_irq_with_timer_timeout(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_enable_keyboard_interrupts()", 1)[1].split(
            "pub fn sotlas_x86_post_cutover_entry", 1
        )[0]
        self.assertIn("post_cutover_timer_live()", body)
        self.assertIn("let keyboard_before = irq_keyboard_count();", body)
        self.assertIn("let timer_start = irq_timer_count();", body)
        self.assertIn("interrupt_enable_keyboard_after_timer()", body)
        self.assertIn("irq_keyboard_count() != keyboard_before", body)
        self.assertIn("POST_CUTOVER_KEYBOARD_LIVE = true", body)
        self.assertIn("POST_CUTOVER_KEYBOARD_TIMEOUT_TICKS", body)
        self.assertIn("interrupt_disable_all();", body)

    def test_entry_markers_prove_timer_before_keyboard(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        timer_enable = body.index("post_cutover_enable_timer_interrupts()")
        timer_marker = body.index("x86_serial_write_stage_marker('T' as u8)")
        keyboard_enable = body.index("post_cutover_enable_keyboard_interrupts()")
        keyboard_marker = body.index("x86_serial_write_stage_marker('K' as u8)")
        self.assertLess(timer_enable, timer_marker)
        self.assertLess(timer_marker, keyboard_enable)
        self.assertLess(keyboard_enable, keyboard_marker)


if __name__ == "__main__":
    unittest.main()
