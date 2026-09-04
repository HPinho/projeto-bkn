#!/usr/bin/env python3
"""Guardrails do planejamento IRQ -> GSI -> vetor IDT."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ROUTE = ROOT / "kernel/src/interrupts/route.sotlas"


class InterruptRouteTests(unittest.TestCase):
    def test_legacy_irq_uses_madt_override(self):
        text = ROUTE.read_text(encoding="utf-8")
        self.assertIn("madt_irq_to_gsi(irq)", text)
        self.assertIn("madt_irq_flags(irq)", text)
        self.assertIn("interrupt_route_keyboard", text)
        self.assertIn("interrupt_route_ps2_mouse", text)
        self.assertIn("interrupt_route_legacy_irq(1, vector)", text)
        self.assertIn("interrupt_route_legacy_irq(12, vector)", text)

    def test_reserved_acpi_flag_encodings_are_rejected(self):
        text = ROUTE.read_text(encoding="utf-8")
        self.assertIn("(flags & 0xFFF0) != 0", text)
        self.assertIn("polarity == 2 || trigger == 2", text)
        self.assertIn("route.active_low = polarity == 3", text)
        self.assertIn("route.level_triggered = trigger == 3", text)

    def test_exception_vectors_are_not_used_for_external_irqs(self):
        text = ROUTE.read_text(encoding="utf-8")
        self.assertIn("IRQ_ROUTE_MIN_VECTOR: u16 = 32", text)
        self.assertIn("IRQ_ROUTE_MAX_VECTOR: u16 = 255", text)
        self.assertIn("vector < IRQ_ROUTE_MIN_VECTOR", text)

    def test_planner_does_not_touch_interrupt_hardware(self):
        text = ROUTE.read_text(encoding="utf-8")
        for forbidden in ("__sti", "__cli", "__out", "mmio_read", "mmio_write", "__wrmsr"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
