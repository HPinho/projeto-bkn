"""Guardrails da base SMP real do kernel Baken."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOW = ROOT / "kernel/src/memory/low_memory.sotlas"
ACTIVE = ROOT / "kernel/src/memory/active_page_tables.sotlas"
LAPIC = ROOT / "kernel/src/interrupts/lapic.sotlas"
TRAMP = ROOT / "kernel/src/arch/x86_64/smp_trampoline.sotlas"
SMP = ROOT / "kernel/src/arch/x86_64/smp.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"

class KernelSmpBaseTests(unittest.TestCase):
    def test_low_memory_page_comes_only_from_final_conventional_inventory(self):
        text = LOW.read_text(encoding="utf-8")
        for token in ("pmm_inventory_is_valid()", "pmm_get_conventional_region(ordinal)", "LOW_MEMORY_SMP_MIN: u64 = 0x00010000", "LOW_MEMORY_SMP_LIMIT: u64 = 0x000A0000", "x86_page_align_down(candidate_limit)"):
            self.assertIn(token, text)
        self.assertNotIn("return 0x7000", text)

    def test_trampoline_identity_is_rx_and_never_wx(self):
        text = ACTIVE.read_text(encoding="utf-8")
        body = text.split("pub fn active_page_tables_map_ram_identity_4k", 1)[1]
        self.assertIn("writable && executable", body)
        self.assertRegex(body, r"if !executable \{ (?:flags|pte_flags) \|= X86_PTE_NX; \}")
        smp = SMP.read_text(encoding="utf-8")
        self.assertIn("active_page_tables_map_ram_identity_4k(trampoline, false, true)", smp)

    def test_lapic_has_real_init_sipi_icr_sequence(self):
        text = LAPIC.read_text(encoding="utf-8")
        for token in ("LAPIC_REG_ICR_LOW: u64 = 0x300", "LAPIC_REG_ICR_HIGH: u64 = 0x310", "LAPIC_ICR_INIT_ASSERT: u32 = 0x0000C500", "LAPIC_ICR_INIT_DEASSERT: u32 = 0x00008500", "LAPIC_ICR_STARTUP: u32 = 0x00000600", "LAPIC_ICR_DELIVERY_STATUS", "lapic_send_init_assert", "lapic_send_init_deassert", "lapic_send_startup"):
            self.assertIn(token, text)

    def test_trampoline_enters_long_mode_with_nx_and_baken_cr3(self):
        text = TRAMP.read_text(encoding="utf-8")
        for token in ("SMP_TRAMPOLINE_BYTES: usize = 166", "SMP_TRAMPOLINE_LONG_MODE_OFFSET: u64 = 0x42", "SMP_TRAMPOLINE_CR3_VALUE_OFFSET: usize = 0x80", "SMP_TRAMPOLINE_GDT_POINTER_OFFSET: usize = 0xA0", "root_physical > 0xFFFFFFFF", "smp_trampoline_write_u32(base, SMP_TRAMPOLINE_CR3_VALUE_OFFSET", "smp_trampoline_write_u64(base, SMP_TRAMPOLINE_IDLE_OFFSET", "__dma_fence();"):
            self.assertIn(token, text)
        self.assertIn("102, 13, 0, 9, 0, 0", text)

    def test_ap_uses_private_stack_and_enters_per_cpu_runtime(self):
        text = SMP.read_text(encoding="utf-8")
        for token in ("SMP_AP_STACK_PAGES: u64 = 4", "pmm_alloc_pages(SMP_AP_STACK_PAGES)", "x86_smp_ap_runtime_entry_address()", "sotlas_x86_smp_ap_runtime_entry", "lapic_send_init_assert(apic_id)", "lapic_send_init_deassert(apic_id)", "lapic_send_startup(apic_id, vector)", "smp_wait_ap_ready(ready_address, SMP_AP_READY_TIMEOUT_US)", "smp_wait_ap_ready(runtime_ready_address, SMP_AP_RUNTIME_TIMEOUT_US)", "started != ap_targets || runtime_ready != ap_targets"):
            self.assertIn(token, text)
        self.assertNotIn("scheduler_initialize", text)
        self.assertNotIn("scheduler_on_timer_interrupt", text)
        body = text.split("pub fn sotlas_x86_smp_ap_runtime_entry", 1)[1].split("fn smp_start_one_ap", 1)[0]
        release = body.index("while x86_mmio_read32(release) != 1")
        sti = body.index("x86_sti_raw()")
        self.assertLess(release, sti)
        self.assertIn("lapic_timer_prepare_current_cpu_masked()", body)
        self.assertNotIn("lapic_timer_unmask_periodic()", body)

    def test_runtime_brings_aps_up_before_process_scheduler_and_bsp_fpu_publication(self):
        text = RUNTIME.read_text(encoding="utf-8")
        body = text.split("pub fn baken_native_kernel_run", 1)[1]
        smp = body.index("smp_initialize_base()")
        process = body.index("process_address_space_activate_foundation()")
        fpu = body.index("fpu_initialize()")
        scheduler = body.index("scheduler_initialize()")
        self.assertLess(smp, process)
        self.assertLess(smp, fpu)
        self.assertLess(smp, scheduler)
        self.assertIn("smp_emit_ready_markers()", body)

    def test_ci_proves_two_cpu_runtime_not_only_madt_enumeration(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("-machine q35 -smp 2", workflow)
        self.assertIn("BAKEN:SMP_AP_ONLINE", workflow)
        self.assertIn("BAKEN:SMP_AP_RUNTIME_READY", workflow)
        self.assertIn("BAKEN:SMP_BASE_READY", workflow)
        self.assertIn("require_marker()", workflow)
        self.assertIn("require_marker 'BAKEN:SMP_AP_RUNTIME_READY'", workflow)

    def test_standard_smoke_requires_smp_base_even_on_uniprocessor(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        self.assertIn('"SMP_BASE_READY"', smoke)

if __name__ == "__main__":
    unittest.main()
