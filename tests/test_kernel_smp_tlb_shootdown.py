"""Guardrails da coerencia de page tables/TLB em SMP."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT / "kernel/src/memory/active_page_tables.sotlas"
TLB = ROOT / "kernel/src/memory/tlb_shootdown.sotlas"
XAPIC = ROOT / "kernel/src/interrupts/xapic_ipi.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
SMP = ROOT / "kernel/src/arch/x86_64/smp.sotlas"
SPIN = ROOT / "kernel/src/sync/spinlock.sotlas"
PROBE = ROOT / "kernel/src/scheduler/smp_probe.sotlas"
BACKEND = ROOT / "tools/sotlas_compile/x86_intrinsics.py"
WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class KernelSmpTlbShootdownTests(unittest.TestCase):
    def test_dedicated_ipi_vector_has_real_arch_stub(self):
        irq = IRQ.read_text(encoding="utf-8")
        backend = BACKEND.read_text(encoding="utf-8")
        self.assertIn("IRQ_VECTOR_TLB_SHOOTDOWN_IPI: u16 = 0x45", irq)
        self.assertIn("irq_install_gate(IRQ_VECTOR_TLB_SHOOTDOWN_IPI)", irq)
        self.assertIn("SOTLAS_X86_IRQ_STUB(69)", backend)
        self.assertRegex(backend, r"case\s+69:\s*return")
        handler = irq.split("if vector == IRQ_VECTOR_TLB_SHOOTDOWN_IPI as u64", 1)[1]
        handler = handler.split("if vector == IRQ_VECTOR_TIMER", 1)[0]
        self.assertIn("tlb_shootdown_handle_ipi()", handler)
        self.assertIn("lapic_eoi();", handler)
        self.assertNotIn("irq_schedule_with_fpu", handler)

    def test_shootdown_handler_is_allocation_free_and_lock_free(self):
        text = TLB.read_text(encoding="utf-8")
        handler = text.split("pub fn tlb_shootdown_handle_ipi() -> bool", 1)[1]
        for forbidden in ("pmm_", "kernel_heap", "spinlock_lock", "spinlock_try_lock"):
            self.assertNotIn(forbidden, handler)
        self.assertIn("x86_invlpg(address)", handler)
        self.assertIn("TLB_SHOOTDOWN_ACK", handler)
        self.assertIn("x86_mmio_write32", handler)
        self.assertIn("TLB_SHOOTDOWN_CPU_ROOT[slot] = current_root", handler)

    def test_shootdown_transport_is_decoupled_and_supports_broadcast_and_directed_ipi(self):
        text = TLB.read_text(encoding="utf-8")
        xapic = XAPIC.read_text(encoding="utf-8")
        self.assertNotIn("scheduler::", text)
        self.assertNotIn("arch::x86_64::smp", text)
        self.assertNotIn("active_page_tables", text)
        self.assertNotIn("active_page_tables", xapic)
        self.assertIn("XAPIC_IPI_DEST_ALL_EXCLUDING_SELF", xapic)
        self.assertIn("pub fn xapic_ipi_send_fixed(destination_apic_id: u8, vector: u8) -> bool", xapic)
        self.assertIn("(destination_apic_id as u32) << 24", xapic)
        self.assertIn("xapic_ipi_send_fixed_all_excluding_self", xapic)

    def test_process_root_targets_only_matching_or_unknown_cpus(self):
        text = TLB.read_text(encoding="utf-8")
        selective = text.split("fn tlb_shootdown_send_address_space_targets", 1)[1]
        selective = selective.split("fn tlb_shootdown_page", 1)[0]
        self.assertIn("slot != requester_slot", selective)
        self.assertIn("let published_root = TLB_SHOOTDOWN_CPU_ROOT[slot]", selective)
        self.assertIn("if published_root == 0 || published_root == root", selective)
        self.assertIn("xapic_ipi_send_fixed(", selective)
        self.assertIn("TLB_SHOOTDOWN_CPU_APIC_ID[slot]", selective)
        self.assertNotIn("xapic_ipi_send_fixed_all_excluding_self", selective)
        self.assertIn("return TLB_SHOOTDOWN_TARGET_FAILURE", selective)

    def test_kernel_root_keeps_global_broadcast(self):
        text = TLB.read_text(encoding="utf-8")
        body = text.split("fn tlb_shootdown_page(address: u64, root: u64) -> bool", 1)[1]
        body = body.split("pub fn tlb_shootdown_kernel_page", 1)[0]
        self.assertIn("if root == 0", body)
        self.assertIn("expected = active_count - 1", body)
        self.assertIn("xapic_ipi_send_fixed_all_excluding_self", body)
        self.assertIn("tlb_shootdown_send_address_space_targets(root, requester_slot)", body)
        self.assertIn("tlb_shootdown_wait_ack(generation, requester_slot, expected)", body)

    def test_page_table_mutation_uses_irq_safe_try_lock_and_shootdown(self):
        active = ACTIVE.read_text(encoding="utf-8")
        spin = SPIN.read_text(encoding="utf-8")
        self.assertIn("pub fn spinlock_try_lock", spin)
        self.assertIn("spinlock_try_lock(&mut ACTIVE_PAGE_TABLE_LOCK)", active)
        self.assertIn("x86_irq_restore(flags);", active)
        self.assertIn("pub fn active_runtime_remap", active)
        for function in ("active_runtime_map", "active_runtime_remap", "active_runtime_protect", "active_runtime_unmap"):
            body = active.split(f"pub fn {function}", 1)[1].split("@system", 1)[0]
            self.assertIn("active_page_tables_lock_irq()", body)
            self.assertIn("active_page_tables_publish_locked", body)
        self.assertIn("return tlb_shootdown_kernel_page(address);", active)

    def test_bsp_and_aps_are_symmetric_shootdown_participants(self):
        text = TLB.read_text(encoding="utf-8")
        self.assertIn("if slot == 0 { TLB_SHOOTDOWN_CPU_ACTIVE[slot] = true; }", text)
        self.assertIn("pub fn tlb_shootdown_active_cpu_count() -> u32", text)
        self.assertIn("slot != requester_slot", text)
        handler = text.split("pub fn tlb_shootdown_handle_ipi() -> bool", 1)[1]
        self.assertNotIn("slot == 0", handler)
        self.assertIn("TLB_SHOOTDOWN_CPU_ACTIVE[slot]", handler)

    def test_smp_registers_then_activates_shootdown_participants(self):
        smp = SMP.read_text(encoding="utf-8")
        self.assertIn("tlb_shootdown_register_cpu(slot, apic_id)", smp)
        release = smp.split("pub fn smp_release_aps_for_scheduler() -> bool", 1)[1]
        self.assertIn("tlb_shootdown_activate_cpu(slot)", release)
        self.assertIn("tlb_shootdown_active_ap_count() == expected", release)

    def test_qemu_probe_primes_remaps_and_observes_remote_va(self):
        probe = PROBE.read_text(encoding="utf-8")
        self.assertIn("SCHEDULER_SMP_PROBE_MODE_TLB: u32 = 3", probe)
        self.assertIn("x86_mmio_read32(SCHEDULER_SMP_TLB_ADDRESS) != SCHEDULER_SMP_TLB_OLD_VALUE", probe)
        self.assertIn("active_runtime_remap(SCHEDULER_SMP_TLB_ADDRESS, second, true, false)", probe)
        self.assertIn("SCHEDULER_SMP_TLB_NEW_VALUE", probe)
        self.assertIn("scheduler_smp_probe_emit_tlb_marker()", probe)
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_tlb_shootdown.py", workflow)
        self.assertIn("BAKEN:SMP_TLB_SHOOTDOWN_READY", workflow)
        self.assertIn("require_marker 'BAKEN:SMP_TLB_SHOOTDOWN_READY'", workflow)


if __name__ == "__main__":
    unittest.main()
