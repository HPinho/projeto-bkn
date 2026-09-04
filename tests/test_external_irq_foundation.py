#!/usr/bin/env python3
"""Guardrails da fundação de IRQs externos pós-cutover."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
IOAPIC = ROOT / "kernel/src/interrupts/ioapic.sotlas"
I8042 = ROOT / "kernel/src/drivers/i8042.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
X86 = ROOT / "tools/sotlas_compile/x86_intrinsics.py"


class ExternalIrqFoundationTests(unittest.TestCase):
    def test_vectors_are_outside_exception_range(self):
        text = IRQ.read_text(encoding="utf-8")
        self.assertIn("IRQ_VECTOR_TIMER: u16 = 0x40", text)
        self.assertIn("IRQ_VECTOR_KEYBOARD: u16 = 0x41", text)
        self.assertIn("IRQ_VECTOR_MOUSE: u16 = 0x42", text)
        self.assertIn("IRQ_VECTOR_SPURIOUS: u16 = 0xFF", text)

    def test_backend_saves_context_and_returns_with_iretq(self):
        text = X86.read_text(encoding="utf-8")
        self.assertIn("__sotlas_x86_irq_common", text)
        self.assertIn("pushq %r15", text)
        self.assertIn("pushq %rax", text)
        self.assertIn("call sotlas_x86_irq_dispatch", text)
        self.assertIn("popq %rax", text)
        self.assertIn("iretq", text)
        self.assertIn("__irq_stub_address", text)

    def test_spurious_vector_never_sends_eoi(self):
        text = IRQ.read_text(encoding="utf-8")
        body = text.split("if vector == IRQ_VECTOR_SPURIOUS", 1)[1].split("if vector == IRQ_VECTOR_TIMER", 1)[0]
        self.assertIn("IRQ_SPURIOUS_COUNT", body)
        self.assertNotIn("lapic_eoi()", body)

    def test_real_irq_vectors_send_lapic_eoi(self):
        text = IRQ.read_text(encoding="utf-8")
        for vector in ("IRQ_VECTOR_TIMER", "IRQ_VECTOR_KEYBOARD", "IRQ_VECTOR_MOUSE"):
            body = text.split(f"if vector == {vector}", 1)[1].split("return;", 1)[0]
            self.assertIn("lapic_eoi()", body)

    def test_keyboard_mouse_use_bounded_irq_drain_before_eoi(self):
        text = IRQ.read_text(encoding="utf-8")
        for vector in ("IRQ_VECTOR_KEYBOARD", "IRQ_VECTOR_MOUSE"):
            body = text.split(f"if vector == {vector}", 1)[1].split("return;", 1)[0]
            self.assertIn("i8042_drain_irq_output();", body)
            self.assertNotIn("i8042_initialize_polling", body)
            self.assertLess(body.index("i8042_drain_irq_output();"), body.index("lapic_eoi();"))

    def test_i8042_irq_path_never_initializes_or_waits_for_ack(self):
        text = I8042.read_text(encoding="utf-8")
        body = text.split("pub fn i8042_drain_irq_output", 1)[1].split("pub fn i8042_pop_keyboard", 1)[0]
        self.assertIn("I8042_INITIALIZED", body)
        self.assertIn("I8042_NATIVE_IRQS_ENABLED", body)
        self.assertIn("i8042_drain_ready_output();", body)
        self.assertNotIn("i8042_initialize_polling", body)
        self.assertNotIn("i8042_wait_output", body)
        self.assertNotIn("i8042_aux_command", body)

    def test_ioapic_route_state_is_rebuilt_not_blindly_unmasked(self):
        text = IOAPIC.read_text(encoding="utf-8")
        self.assertIn("fn ioapic_program_route_state", text)
        self.assertIn("ioapic_program_route_masked", text)
        self.assertIn("ioapic_program_route_unmasked", text)
        self.assertIn("if masked { low |= IOAPIC_REDIR_MASKED; }", text)
        self.assertIn("IOAPIC_REDIR_ACTIVE_LOW", text)
        self.assertIn("IOAPIC_REDIR_LEVEL", text)
        self.assertIn("let high = (destination_apic_id as u32) << 24", text)
        self.assertIn("ioapic_write(base, high_reg, high)", text)
        self.assertIn("ioapic_write(base, low_reg, low)", text)

    def test_post_cutover_prepares_irqs_but_never_enables_sti(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        self.assertIn("post_cutover_prepare_irqs()", body)
        code = "\n".join(line.split("//", 1)[0] for line in text.splitlines())
        self.assertNotIn("__sti(", code)
        self.assertNotIn("x86_sti", code)


if __name__ == "__main__":
    unittest.main()
