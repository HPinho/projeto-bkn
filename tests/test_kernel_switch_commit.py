"""Guardrails do commit em duas fases de context switch SMP.

Uma thread que acabou de ser preemptada/bloqueada/terminada ainda possui o
frame de IRQ fisicamente ativo até a CPU trocar de %rsp. O scheduler deve
manter ownership durante essa janela e só publicar owner=NONE numa entrada
posterior do scheduler na mesma CPU.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "kernel/src/scheduler/core.sotlas"
PROBE = ROOT / "kernel/src/scheduler/smp_probe.sotlas"


class KernelSwitchCommitTests(unittest.TestCase):
    def test_scheduler_has_deferred_owner_release(self):
        text = CORE.read_text(encoding="utf-8")
        self.assertIn("fn scheduler_confirm_switched_away_for_cpu", text)
        helper = text.split("fn scheduler_confirm_switched_away_for_cpu", 1)[1].split("@system", 1)[0]
        for token in (
            "let current = scheduler_current_slot_for_cpu(cpu_slot);",
            "slot != current",
            "SCHEDULER_THREAD_OWNER_CPU[slot] == cpu_slot as u32",
            "SCHEDULER_THREAD_OWNER_CPU[slot] = SCHEDULER_CPU_NONE",
        ):
            self.assertIn(token, helper)

    def test_owner_release_happens_before_next_selection_pass(self):
        text = CORE.read_text(encoding="utf-8")
        timer = text.split("pub fn scheduler_on_timer_interrupt", 1)[1].split(
            "pub fn scheduler_wait_first_round_trip", 1
        )[0]
        confirm = timer.index("scheduler_confirm_switched_away_for_cpu(cpu_slot)")
        secondary = timer.index("scheduler_on_secondary_interrupt")
        self.assertLess(confirm, secondary)

    def test_dynamic_switch_away_does_not_publish_none_in_same_irq(self):
        text = CORE.read_text(encoding="utf-8")
        secondary = text.split("fn scheduler_on_secondary_interrupt", 1)[1].split(
            "pub fn scheduler_on_timer_interrupt", 1
        )[0]
        running = secondary.split("KERNEL_THREAD_RUNNING", 1)[1].split(
            "let mut start", 1
        )[0]
        self.assertIn("KERNEL_THREAD_READY", running)
        self.assertNotIn("SCHEDULER_THREAD_OWNER_CPU[current] = SCHEDULER_CPU_NONE", running)

        timer = text.split("pub fn scheduler_on_timer_interrupt", 1)[1].split(
            "pub fn scheduler_wait_first_round_trip", 1
        )[0]
        normal = timer.split("let current_id", 1)[1].split("let mut start", 1)[0]
        self.assertIn("KERNEL_THREAD_READY", normal)
        self.assertNotIn("SCHEDULER_THREAD_OWNER_CPU[current] = SCHEDULER_CPU_NONE", normal)

    def test_wakeup_does_not_steal_retirement_ownership(self):
        text = CORE.read_text(encoding="utf-8")
        wake = text.split("pub fn scheduler_wake_thread", 1)[1].split(
            "pub fn scheduler_terminate_current", 1
        )[0]
        self.assertIn("SCHEDULER_THREADS[slot].state = KERNEL_THREAD_READY", wake)
        self.assertNotIn("SCHEDULER_THREAD_OWNER_CPU[slot] = SCHEDULER_CPU_NONE", wake)

    def test_idle_probe_does_not_equate_switch_commit_with_reaping(self):
        text = PROBE.read_text(encoding="utf-8")
        wait = text.split("fn scheduler_smp_probe_wait_idle", 1)[1].split(
            "fn scheduler_smp_probe_wait_timer_enabled", 1
        )[0]
        self.assertIn("scheduler_secondary_idle_epoch(cpu_slot) > idle_epoch_before", wait)
        self.assertNotIn("scheduler_thread_owner_cpu", wait)


if __name__ == "__main__":
    unittest.main()
