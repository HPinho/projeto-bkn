"""Guardrails do tracking per-CPU do CR3 ativo usado pela coerencia TLB SMP."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TLB = ROOT / "kernel/src/memory/tlb_shootdown.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"


class ActiveAddressSpaceTrackingTests(unittest.TestCase):
    def test_tlb_layer_owns_per_cpu_root_tracking_without_scheduler_dependency(self):
        text = TLB.read_text(encoding="utf-8")
        self.assertIn(
            "static mut TLB_SHOOTDOWN_CPU_ROOT: [u64; TLB_SHOOTDOWN_MAX_CPUS]",
            text,
        )
        self.assertIn("pub fn tlb_shootdown_publish_current_root() -> bool", text)
        self.assertIn("pub fn tlb_shootdown_cpu_root(slot: usize) -> u64", text)
        self.assertIn("x86_read_cr3_raw() & X86_PAGE_ADDRESS_MASK", text)
        self.assertNotIn("scheduler::", text)
        self.assertNotIn("process::", text)

    def test_tracking_starts_unknown_and_is_published_only_for_active_registered_cpu(self):
        text = TLB.read_text(encoding="utf-8")
        self.assertIn("TLB_SHOOTDOWN_CPU_ROOT[slot] = 0;", text)
        body = text.split("pub fn tlb_shootdown_publish_current_root() -> bool", 1)[1]
        body = body.split("pub fn tlb_shootdown_cpu_root", 1)[0]
        self.assertIn("tlb_shootdown_slot_for_current_cpu()", body)
        self.assertIn("TLB_SHOOTDOWN_CPU_REGISTERED[slot]", body)
        self.assertIn("TLB_SHOOTDOWN_CPU_ACTIVE[slot]", body)
        self.assertIn("TLB_SHOOTDOWN_CPU_ROOT[slot] = root", body)
        self.assertIn("__dma_fence()", body)

    def test_irq_paths_publish_only_after_scheduler_selected_cr3(self):
        irq = IRQ.read_text(encoding="utf-8")
        plain = irq.split("fn irq_schedule_publish_root(frame_address: u64) -> u64", 1)[1]
        plain = plain.split("fn irq_schedule_with_fpu", 1)[0]
        self.assertLess(
            plain.index("scheduler_on_timer_interrupt(frame_address)"),
            plain.index("tlb_shootdown_publish_current_root()"),
        )

        fpu = irq.split("fn irq_schedule_with_fpu(frame_address: u64) -> u64", 1)[1]
        fpu = fpu.split("@system\n@export", 1)[0]
        save = fpu.index("fpu_save_thread(old_tid)")
        select = fpu.index("let selected = scheduler_on_timer_interrupt(frame_address);")
        publish = fpu.index("tlb_shootdown_publish_current_root()")
        restore = fpu.index("fpu_restore_thread(new_tid)")
        self.assertLess(save, select)
        self.assertLess(select, publish)
        self.assertLess(publish, restore)

    def test_no_fpu_scheduling_paths_use_publication_wrapper(self):
        irq = IRQ.read_text(encoding="utf-8")
        self.assertEqual(
            irq.count("return irq_schedule_publish_root(frame_address);"),
            2,
        )
        self.assertIn(
            "let selected = scheduler_on_timer_interrupt(frame_address);\n    if !tlb_shootdown_publish_current_root()",
            irq,
        )


if __name__ == "__main__":
    unittest.main()
