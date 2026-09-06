#!/usr/bin/env python3
"""Locks the real external IRQ foundation proof used by the QEMU gate."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION = ROOT / "kernel/src/storage/foundation_probe.sotlas"
I8042 = ROOT / "kernel/src/drivers/i8042.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
FIXTURE = ROOT / "tools/scripts/extend_foundation_fixture.py"


class FoundationExternalIrqGateTests(unittest.TestCase):
    def test_probe_requires_two_real_i8042_irq_deliveries(self):
        text = FOUNDATION.read_text(encoding="utf-8")
        body = text.split("pub fn foundation_external_irq_probe() -> bool {", 1)[1].split("\n}\n\n@system", 1)[0]
        for token in (
            "while pass < 2",
            "let before = irq_keyboard_count();",
            "i8042_trigger_irq_probe()",
            "while irq_keyboard_count() == before",
            "if irq_keyboard_count() == before { return false; }",
            "pass += 1;",
            "x86_serial_write_stage_marker('&' as u8);",
        ):
            self.assertIn(token, body)
        self.assertNotIn("irq_dispatch(", body)
        self.assertNotIn("IRQ_KEYBOARD_COUNT +=", body)

    def test_i8042_probe_asserts_controller_irq_instead_of_calling_isr(self):
        text = I8042.read_text(encoding="utf-8")
        body = text.split("pub fn i8042_trigger_irq_probe() -> bool {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("i8042_keyboard_irq_enabled()", body)
        self.assertIn("i8042_command(0xD2)", body)
        self.assertIn("i8042_write_data(0x00)", body)
        self.assertNotIn("irq_dispatch", body)
        self.assertNotIn("lapic_eoi", body)

    def test_keyboard_isr_drains_hardware_counts_delivery_and_eois(self):
        text = IRQ.read_text(encoding="utf-8")
        self.assertIn("i8042_drain_irq_output();", text)
        self.assertIn("IRQ_KEYBOARD_COUNT += 1", text)
        self.assertIn("lapic_eoi();", text)
        drain = text.index("i8042_drain_irq_output();")
        count = text.index("IRQ_KEYBOARD_COUNT += 1", drain)
        eoi = text.index("lapic_eoi();", count)
        self.assertLess(drain, count)
        self.assertLess(count, eoi)

    def test_irq_probe_runs_after_memory_gate_and_before_storage_extensions(self):
        text = POST.read_text(encoding="utf-8")
        memory = text.index("foundation_memory_probe()")
        irq = text.index("foundation_external_irq_probe()", memory)
        mbr = text.index("foundation_protective_mbr()", irq)
        self.assertLess(memory, irq)
        self.assertLess(irq, mbr)

    def test_qemu_fixture_requires_external_irq_marker(self):
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertIn("'BAKEN:STEP=&'", text)


if __name__ == "__main__":
    unittest.main()
