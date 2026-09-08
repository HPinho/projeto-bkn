"""Guardrails da prova de process thread CPL3 preemptada, retomada e com TLB user coerente no AP."""
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

    def test_user_data_remap_requires_real_root_aware_tlb_invalidation(self):
        text = PROBE.read_text(encoding="utf-8")
        run = text.split("fn scheduler_smp_probe_run_ring3", 1)[1].split(
            "fn scheduler_smp_probe_run_tlb", 1
        )[0]
        for token in (
            "let data_new = pmm_alloc_page();",
            "let started_address = data_virtual + SCHEDULER_SMP_RING3_STARTED_OFFSET;",
            "let release_old_address = data_virtual + SCHEDULER_SMP_RING3_RELEASE_OFFSET;",
            "let release_new_address = data_new_virtual + SCHEDULER_SMP_RING3_RELEASE_OFFSET;",
            "let resumed_address = data_new_virtual + SCHEDULER_SMP_RING3_RESUMED_OFFSET;",
            "x86_mmio_write32(release_old_address, 0)",
            "x86_mmio_write32(release_new_address, 1)",
            "process_remap_user_page(pid, SCHEDULER_SMP_RING3_DATA_ADDRESS",
            "data_new, true, false",
            "if remapped_data != data { return false; }",
            "scheduler_smp_probe_wait_flag(resumed_address)",
            "unmapped_data != data_new",
            "pmm_free_pages(data, 1)",
            "pmm_free_pages(data_new, 1)",
            "scheduler_smp_probe_emit_process_tlb_marker()",
        ):
            self.assertIn(token, run)

        start = run.index("scheduler_smp_probe_wait_flag(started_address)")
        tick = run.index("scheduler_smp_probe_wait_timer_tick")
        publish_new = run.index("x86_mmio_write32(release_new_address, 1)")
        remap = run.index("process_remap_user_page(pid, SCHEDULER_SMP_RING3_DATA_ADDRESS")
        resumed = run.index("scheduler_smp_probe_wait_flag(resumed_address)")
        self.assertLess(start, tick)
        self.assertLess(tick, publish_new)
        self.assertLess(publish_new, remap)
        self.assertLess(remap, resumed)
        self.assertNotIn("x86_mmio_write32(release_old_address, 1)", run)

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
            "scheduler_smp_probe_emit_process_tlb_marker()",
            "scheduler_smp_probe_emit_ring3_ready_marker()",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("scheduler_smp_probe_wait_process_reaped"),
                        body.index("process_unmap_user_page"))
        self.assertLess(body.rindex("process_destroy(pid)"),
                        body.index("scheduler_smp_probe_emit_process_tlb_marker()"))
        self.assertLess(body.index("scheduler_smp_probe_emit_process_tlb_marker()"),
                        body.index("scheduler_smp_probe_emit_ring3_ready_marker()"))

    def test_ring3_runs_only_after_existing_kernel_tlb_proof(self):
        text = PROBE.read_text(encoding="utf-8")
        run = text.split("pub fn scheduler_smp_probe_run() -> bool", 1)[1]
        self.assertIn("if !scheduler_smp_probe_run_tlb(apic_id) { return false; }", run)
        self.assertIn("return scheduler_smp_probe_run_ring3(apic_id);", run)
        self.assertLess(run.index("scheduler_smp_probe_run_tlb(apic_id)"),
                        run.index("scheduler_smp_probe_run_ring3(apic_id)"))

    def test_workflow_requires_process_tlb_user_resume_and_final_ready_markers(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_ring3.py", workflow)
        for marker in (
            "BAKEN:SMP_RING3_ON_AP",
            "BAKEN:SMP_RING3_RESUMED_ON_AP",
            "BAKEN:SMP_PROCESS_TLB_READY",
            "BAKEN:SMP_RING3_ON_AP_READY",
        ):
            self.assertIn(marker, workflow)
        self.assertIn("grep -Fxq 'BAKEN:SMP_RING3_ON_AP'", workflow)
        self.assertIn("grep -Fxq 'BAKEN:SMP_RING3_RESUMED_ON_AP'", workflow)
        self.assertIn("grep -Fxq 'BAKEN:SMP_PROCESS_TLB_READY'", workflow)
        self.assertIn("grep -Fxq 'BAKEN:SMP_RING3_ON_AP_READY'", workflow)


if __name__ == "__main__":
    unittest.main()
