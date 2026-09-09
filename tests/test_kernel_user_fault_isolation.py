"""Contratos da recuperação de page fault CPL3 sem derrubar o kernel."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXCEPTIONS = ROOT / "kernel/src/arch/x86_64/exceptions.sotlas"
LOADER = ROOT / "kernel/src/process/userspace_loader.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class KernelUserFaultIsolationTests(unittest.TestCase):
    def test_fault_probe_reads_unmapped_user_guard_page(self):
        text = LOADER.read_text(encoding="utf-8")
        body = text.split("fn userspace_materialize_fault_probe", 1)[1].split(
            "fn userspace_materialize_migration_probe", 1
        )[0]
        self.assertIn("USERSPACE_STACK_GUARD", body)
        self.assertIn("USERSPACE_FAULT_PROBE_CODE_BYTES", body)
        self.assertIn("72,184,0,224,31,0,0,0,32,0,138,0", body)

    def test_user_fault_requires_cpl3_pf_reaper_and_address_space_teardown(self):
        loader = LOADER.read_text(encoding="utf-8")
        exceptions = EXCEPTIONS.read_text(encoding="utf-8")
        wait = loader.split("pub fn userspace_loader_wait_fault_probe", 1)[1].split(
            "pub fn userspace_loader_finish_fault_probe", 1
        )[0]
        finish = loader.split("pub fn userspace_loader_finish_fault_probe", 1)[1].split(
            "fn userspace_emit", 1
        )[0]
        for token in (
            "exception_cpu_has_snapshot(cpu_slot)",
            "exception_cpu_last_was_user(cpu_slot)", "EXCEPTION_PAGE_FAULT",
            "page_fault_was_user(exception_cpu_last_error_code(cpu_slot))",
            "exception_cpu_last_process_id(cpu_slot) == USERSPACE_FAULT_PID",
            "process_reference_count(USERSPACE_FAULT_PID) == 0",
        ):
            self.assertIn(token, wait)
        for token in (
            "process_unmap_user_page(USERSPACE_FAULT_PID, USERSPACE_CODE_ADDRESS)",
            "process_unmap_user_page(USERSPACE_FAULT_PID, USERSPACE_DATA_ADDRESS)",
            "process_unmap_user_page(USERSPACE_FAULT_PID, USERSPACE_STACK_ADDRESS)",
            "userspace_release_frames(code, data, stack)", "process_destroy(USERSPACE_FAULT_PID)",
        ):
            self.assertIn(token, finish)
        self.assertIn("scheduler_terminate_current()", exceptions)
        self.assertIn("irq_schedule_terminated_current(frame_address)", exceptions)

    def test_smp_fault_probe_is_pinned_to_ap_and_required_by_workflow(self):
        loader = LOADER.read_text(encoding="utf-8")
        runtime = RUNTIME.read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/baken_smp.yml").read_text(encoding="utf-8")
        body = loader.split("pub fn userspace_loader_run_ap_fault_probe", 1)[1].split(
            "fn userspace_migration_wait_ap", 1
        )[0]
        for token in (
            "userspace_loader_start_fault_probe_on_cpu(USERSPACE_MIGRATION_CPU_SLOT)",
            "smp_cpu_apic_id(USERSPACE_MIGRATION_CPU_SLOT)",
            "lapic_send_fixed(apic_id, IRQ_VECTOR_RESCHEDULE_IPI as u8)",
            "userspace_loader_wait_fault_probe()",
            "userspace_loader_finish_fault_probe()",
            "BAKEN:SMP_USER_FAULT_ISOLATED_READY",
        ):
            self.assertIn(token, body if token != "BAKEN:SMP_USER_FAULT_ISOLATED_READY" else workflow)
        run = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertLess(run.index("scheduler_smp_probe_run()"), run.index("userspace_loader_run_ap_fault_probe()"))
        self.assertLess(run.index("userspace_loader_run_ap_fault_probe()"), run.index("userspace_loader_run_migration_probe()"))
        self.assertIn("require_marker 'BAKEN:SMP_USER_FAULT_ISOLATED_READY'", workflow)
        self.assertIn("timeout-minutes: 6", workflow)
        self.assertIn("for i in $(seq 1 3000); do", workflow)

    def test_runtime_requires_fault_isolation_before_smp_probes(self):
        body = RUNTIME.read_text(encoding="utf-8").split("pub fn baken_native_kernel_run", 1)[1]
        start = body.index("userspace_loader_start_fault_probe()")
        wait = body.index("userspace_loader_wait_fault_probe()")
        finish = body.index("userspace_loader_finish_fault_probe()")
        marker = body.index("userspace_loader_emit_fault_isolation_marker()")
        smp = body.index("scheduler_smp_probe_run()")
        self.assertLess(start, wait)
        self.assertLess(wait, finish)
        self.assertLess(finish, marker)
        self.assertLess(marker, smp)


if __name__ == "__main__":
    unittest.main()
