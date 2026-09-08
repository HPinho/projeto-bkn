"""Guardrails da prova CPL3 real no AP sem fingir preempcao de processo."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "kernel/src/scheduler/smp_probe.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class KernelSmpRing3Tests(unittest.TestCase):
    def test_probe_has_dedicated_ring3_mode_and_private_user_mapping(self):
        text = PROBE.read_text(encoding="utf-8")
        for token in (
            "SCHEDULER_SMP_PROBE_MODE_RING3: u32 = 4",
            "SCHEDULER_SMP_RING3_CODE_ADDRESS: u64 = PROCESS_USER_BASE",
            "SCHEDULER_SMP_RING3_DATA_ADDRESS: u64 = PROCESS_USER_BASE + 0x1000",
            "SCHEDULER_SMP_RING3_STACK_ADDRESS",
            "process_create()",
            "process_retain(pid)",
            "process_borrow_root(pid)",
            "process_map_user_page(pid, SCHEDULER_SMP_RING3_CODE_ADDRESS, code, false, true)",
            "process_map_user_page(pid, SCHEDULER_SMP_RING3_DATA_ADDRESS, data, false, false)",
            "process_map_user_page(pid, SCHEDULER_SMP_RING3_STACK_ADDRESS, stack, true, false)",
        ):
            self.assertIn(token, text)

    def test_ap_entry_masks_timer_switches_cr3_and_uses_cpu_local_tss(self):
        text = PROBE.read_text(encoding="utf-8")
        body = text.split("if mode == SCHEDULER_SMP_PROBE_MODE_RING3", 1)[1].split(
            "if mode != SCHEDULER_SMP_PROBE_MODE_THREAD", 1
        )[0]
        for token in (
            "cpu_slot != SCHEDULER_SMP_PROBE_CPU_SLOT",
            "lapic_timer_mask()",
            "x86_write_cr3_raw(root)",
            "process_current_id() != expected_pid",
            "tss_set_rsp0_for_cpu(cpu_slot, kernel_stack_top)",
            "x86_mmio_write32(scheduler_smp_ring3_cpu_address(), cpu_slot as u32)",
            "__enter_user(SCHEDULER_SMP_RING3_CODE_ADDRESS, SCHEDULER_SMP_RING3_STACK_TOP)",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("lapic_timer_mask()"), body.index("x86_write_cr3_raw(root)"))
        self.assertLess(body.index("tss_set_rsp0_for_cpu"), body.index("__enter_user"))

    def test_ring3_proof_requires_syscalls_idle_teardown_and_timer_restore(self):
        text = PROBE.read_text(encoding="utf-8")
        body = text.split("fn scheduler_smp_probe_run_ring3", 1)[1].split(
            "fn scheduler_smp_probe_run_tlb", 1
        )[0]
        for token in (
            "let syscall_before = syscall_count();",
            "let exit_before = syscall_exit_count();",
            "scheduler_smp_probe_wait_flag(scheduler_smp_ring3_entered_address())",
            "scheduler_smp_probe_wait_idle(tid, SCHEDULER_SMP_PROBE_CPU_SLOT, idle_before)",
            "syscall_count() < syscall_before + 2",
            "syscall_exit_count() <= exit_before",
            "process_unmap_user_page(pid, SCHEDULER_SMP_RING3_CODE_ADDRESS)",
            "process_release(pid)",
            "process_destroy(pid)",
            "scheduler_smp_probe_restore_ap_timer(apic_id)",
            "scheduler_smp_probe_emit_ring3_ready_marker()",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("process_destroy(pid)"), body.index("scheduler_smp_probe_restore_ap_timer(apic_id)"))
        self.assertLess(body.index("scheduler_smp_probe_restore_ap_timer(apic_id)"),
                        body.index("scheduler_smp_probe_emit_ring3_ready_marker()"))

    def test_ring3_runs_only_after_tlb_proof(self):
        text = PROBE.read_text(encoding="utf-8")
        run = text.split("pub fn scheduler_smp_probe_run() -> bool", 1)[1]
        self.assertIn("if !scheduler_smp_probe_run_tlb(apic_id) { return false; }", run)
        self.assertIn("return scheduler_smp_probe_run_ring3(apic_id);", run)
        self.assertLess(run.index("scheduler_smp_probe_run_tlb(apic_id)"),
                        run.index("scheduler_smp_probe_run_ring3(apic_id)"))

    def test_workflow_waits_for_runtime_ring3_ap_ready_marker(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_ring3.py", workflow)
        self.assertIn("BAKEN:SMP_RING3_ON_AP_READY", workflow)
        self.assertIn("BAKEN:SMP_RING3_ON_AP", workflow)
        self.assertIn("grep -Fxq 'BAKEN:SMP_RING3_ON_AP_READY'", workflow)


if __name__ == "__main__":
    unittest.main()
