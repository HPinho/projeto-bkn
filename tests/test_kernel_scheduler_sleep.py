#!/usr/bin/env python3
"""Contratos do sleep não-busy do scheduler do Baken OS."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SLEEP = ROOT / "kernel" / "src" / "scheduler" / "sleep.sotlas"
IRQ = ROOT / "kernel" / "src" / "interrupts" / "irq.sotlas"
PROBE = ROOT / "kernel" / "src" / "scheduler" / "wait_queue_probe.sotlas"
WORKFLOW = ROOT / ".github" / "workflows" / "baken_nvme_only.yml"


class KernelSchedulerSleepTests(unittest.TestCase):
    def test_sleep_blocks_instead_of_busy_waiting(self):
        text = SLEEP.read_text(encoding="utf-8")
        for token in (
            "pub fn scheduler_sleep_ticks(ticks: u64) -> bool",
            "!x86_interrupts_enabled()",
            "let flags = x86_irq_save_disable()",
            "scheduler_block_current()",
            "x86_scheduler_block_switch()",
            "SCHEDULER_SLEEP_WAKE_TICKS[slot] = wake_tick",
        ):
            self.assertIn(token, text)
        body = text.split("pub fn scheduler_sleep_ticks", 1)[1].split("pub fn scheduler_sleep_on_timer_tick", 1)[0]
        self.assertNotIn("x86_timer_spin_wait_us", body)
        self.assertNotIn("x86_cpu_pause", body)

    def test_timer_irq_drives_deadlines_before_reschedule(self):
        irq = IRQ.read_text(encoding="utf-8")
        self.assertIn("import kernel::scheduler::sleep::*;", irq)
        timer = irq.split("if vector == IRQ_VECTOR_TIMER as u64", 1)[1].split("if vector == IRQ_VECTOR_KEYBOARD", 1)[0]
        eoi = timer.index("lapic_eoi()")
        wake = timer.index("scheduler_sleep_on_timer_tick(timer_count)")
        schedule = timer.index("scheduler_on_timer_interrupt(frame_address)")
        self.assertLess(eoi, wake)
        self.assertLess(wake, schedule)

    def test_sleep_rejects_tick_overflow_and_duplicate_wait(self):
        text = SLEEP.read_text(encoding="utf-8")
        self.assertIn("SCHEDULER_SLEEP_MAX_TICK - now", text)
        self.assertIn("scheduler_sleep_find_thread_locked(thread_id)", text)
        self.assertIn("scheduler_sleep_find_free_locked()", text)
        self.assertIn("resume_tick >= wake_tick", text)

    def test_dynamic_probe_requires_three_real_ticks(self):
        probe = PROBE.read_text(encoding="utf-8")
        for token in (
            "pub const SCHEDULER_SLEEP_PROBE_TICKS: u64 = 3",
            "scheduler_sleep_ticks(SCHEDULER_SLEEP_PROBE_TICKS)",
            "WAIT_PROBE_SLEEP_COMPLETE = true",
            "WAIT_PROBE_RESUMED && WAIT_PROBE_WOKEN && WAIT_PROBE_SLEEP_COMPLETE",
        ):
            self.assertIn(token, probe)

    def test_nvme_qemu_gate_requires_sleep_proof_markers(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        for marker in ("BAKEN:SLEEP_BLOCKED", "BAKEN:SLEEP_WAKE", "BAKEN:SLEEP_RESUME"):
            self.assertIn(marker, workflow)
        self.assertIn('grep -Fq "$marker"', workflow)
        self.assertIn('require_serial_marker "$marker"', workflow)


if __name__ == "__main__":
    unittest.main()
