"""Guardrails da prova de process thread CPL3 preemptada e retomada no AP."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "kernel/src/scheduler/smp_probe.sotlas"
CORE = ROOT / "kernel/src/scheduler/core.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class KernelSmpRing3Tests(unittest.TestCase):
    def test_scheduler_can_publish_process_thread_to_registered_ap_atomically(self):
        text = CORE.read_text(encoding="utf-8")
        body = text.split("pub fn scheduler_create_process_thread_on_cpu", 1)[1].split(
            "pub fn scheduler_block_current", 1
        )[0]
        for token in (
            "cpu_slot == 0 || cpu_slot >= SCHEDULER_CPU_SLOT_COUNT",
            "SCHEDULER_CPU_REGISTERED[cpu_slot]",
            "let flags = x86_irq_save_disable();",
            "scheduler_create_process_thread(pid, entry_rip, stack_pages)",
            "SCHEDULER_THREADS[slot].process_id != pid",
            "SCHEDULER_THREADS[slot].address_space_root == 0",
            "SCHEDULER_THREAD_OWNER_CPU[slot] != SCHEDULER_CPU_NONE",
            "SCHEDULER_THREAD_AFFINITY_CPU[slot] = cpu_slot as u32",
            "x86_irq_restore(flags)",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("x86_irq_save_disable()"),
                        body.index("scheduler_create_process_thread(pid, entry_rip, stack_pages)"))
        self.assertLess(body.index("scheduler_create_process_thread(pid, entry_rip, stack_pages)"),
                        body.index("SCHEDULER_THREAD_AFFINITY_CPU[slot] = cpu_slot as u32"))
        self.assertLess(body.index("SCHEDULER_THREAD_AFFINITY_CPU[slot] = cpu_slot as u32"),
                        body.rindex("x86_irq_restore(flags)"))

    def test_probe_uses_real_process_thread_and_scheduler_owned_cr3(self):
        text = PROBE.read_text(encoding="utf-8")
        run = text.split("fn scheduler_smp_probe_run_ring3", 1)[1].split(
            "fn scheduler_smp_probe_run_tlb", 1
        )[0]
        for token in (
            "process_create()",
            "process_map_user_page(pid, SCHEDULER_SMP_RING3_CODE_ADDRESS, code, false, true)",
            "process_map_user_page(pid, SCHEDULER_SMP_RING3_DATA_ADDRESS, data, true, false)",
            "process_map_user_page(pid, SCHEDULER_SMP_RING3_STACK_ADDRESS, stack, true, false)",
            "scheduler_create_process_thread_on_cpu(pid, entry",
            "SCHEDULER_SMP_PROBE_CPU_SLOT",
            "if process_destroy(pid) { return false; }",
        ):
            self.assertIn(token, run)

        entry = text.split("if mode == SCHEDULER_SMP_PROBE_MODE_RING3", 1)[1].split(
            "if mode != SCHEDULER_SMP_PROBE_MODE_THREAD", 1
        )[0]
        self.assertIn("process_current_id() != expected_pid", entry)
        self.assertIn("let root = process_borrow_root(expected_pid);", entry)
        self.assertIn("(x86_read_cr3_raw() & X86_PAGE_ADDRESS_MASK) != root", entry)
        self.assertIn("tss_set_rsp0_for_cpu(cpu_slot, kernel_stack_top)", entry)
        self.assertIn("__enter_user(SCHEDULER_SMP_RING3_CODE_ADDRESS, SCHEDULER_SMP_RING3_STACK_TOP)", entry)
        self.assertNotIn("x86_write_cr3_raw", entry)
        self.assertNotIn("lapic_timer_mask", entry)

    def test_user_program_blocks_until_post_cpl3_timer_tick_then_marks_resume(self):
        text = PROBE.read_text(encoding="utf-8")
        for token in (
            "SCHEDULER_SMP_RING3_STARTED_OFFSET: u64 = 32",
            "SCHEDULER_SMP_RING3_RELEASE_OFFSET: u64 = 36",
            "SCHEDULER_SMP_RING3_RESUMED_OFFSET: u64 = 40",
            "SCHEDULER_SMP_RING3_RESUMED_MARKER_OFFSET: u64 = 64",
            "BAKEN:SMP_RING3_ON_AP",
            "BAKEN:SMP_RING3_RESUMED_ON_AP",
        ):
            self.assertIn(token, text)
        run = text.split("fn scheduler_smp_probe_run_ring3", 1)[1].split(
            "fn scheduler_smp_probe_run_tlb", 1
        )[0]
        self.assertIn("scheduler_smp_probe_wait_flag(started_address)", run)
        self.assertIn("let timer_after_user_start = irq_timer_count_for_cpu", run)
        self.assertIn("scheduler_smp_probe_wait_timer_tick(SCHEDULER_SMP_PROBE_CPU_SLOT, timer_after_user_start)", run)
        self.assertIn("x86_mmio_write32(release_address, 1)", run)
        self.assertIn("scheduler_smp_probe_wait_flag(resumed_address)", run)
        self.assertLess(run.index("scheduler_smp_probe_wait_flag(started_address)"),
                        run.index("let timer_after_user_start"))
        self.assertLess(run.index("scheduler_smp_probe_wait_timer_tick"),
                        run.index("x86_mmio_write32(release_address, 1)"))
        self.assertLess(run.index("x86_mmio_write32(release_address, 1)"),
                        run.index("scheduler_smp_probe_wait_flag(resumed_address)"))

    def test_exit_requires_idle_reaper_and_full_address_space_teardown(self):
        text = PROBE.read_text(encoding="utf-8")
        body = text.split("fn scheduler_smp_probe_run_ring3", 1)[1].split(
            "fn scheduler_smp_probe_run_tlb", 1
        )[0]
        for token in (
            "let syscall_before = syscall_count();",
            "let exit_before = syscall_exit_count();",
            "let reap_before = scheduler_reap_count();",
            "scheduler_smp_probe_wait_idle(tid, SCHEDULER_SMP_PROBE_CPU_SLOT, idle_before)",
            "syscall_count() < syscall_before + 3",
            "syscall_exit_count() <= exit_before",
            "scheduler_smp_probe_wait_process_reaped(pid, reap_before)",
            "process_unmap_user_page(pid, SCHEDULER_SMP_RING3_CODE_ADDRESS)",
            "process_unmap_user_page(pid, SCHEDULER_SMP_RING3_DATA_ADDRESS)",
            "process_unmap_user_page(pid, SCHEDULER_SMP_RING3_STACK_ADDRESS)",
            "process_destroy(pid)",
            "scheduler_smp_probe_emit_ring3_ready_marker()",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("scheduler_smp_probe_wait_process_reaped"),
                        body.index("process_unmap_user_page"))
        self.assertLess(body.rindex("process_destroy(pid)"),
                        body.index("scheduler_smp_probe_emit_ring3_ready_marker()"))

    def test_ring3_runs_only_after_existing_tlb_proof(self):
        text = PROBE.read_text(encoding="utf-8")
        run = text.split("pub fn scheduler_smp_probe_run() -> bool", 1)[1]
        self.assertIn("if !scheduler_smp_probe_run_tlb(apic_id) { return false; }", run)
        self.assertIn("return scheduler_smp_probe_run_ring3(apic_id);", run)
        self.assertLess(run.index("scheduler_smp_probe_run_tlb(apic_id)"),
                        run.index("scheduler_smp_probe_run_ring3(apic_id)"))

    def test_workflow_requires_user_resume_and_final_ready_markers(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_ring3.py", workflow)
        for marker in (
            "BAKEN:SMP_RING3_ON_AP",
            "BAKEN:SMP_RING3_RESUMED_ON_AP",
            "BAKEN:SMP_RING3_ON_AP_READY",
        ):
            self.assertIn(marker, workflow)
        self.assertIn("grep -Fxq 'BAKEN:SMP_RING3_ON_AP'", workflow)
        self.assertIn("grep -Fxq 'BAKEN:SMP_RING3_RESUMED_ON_AP'", workflow)
        self.assertIn("grep -Fxq 'BAKEN:SMP_RING3_ON_AP_READY'", workflow)


if __name__ == "__main__":
    unittest.main()
