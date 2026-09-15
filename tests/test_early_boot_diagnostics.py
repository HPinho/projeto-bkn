import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class EarlyBootDiagnosticsContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.post = POST.read_text(encoding="utf-8")

    def test_diagnostics_need_only_the_mapped_gop_framebuffer(self):
        begin = self.runtime.split("pub fn baken_early_boot_begin", 1)[1].split(
            "pub fn baken_early_boot_stage", 1)[0]
        for token in ("display_init", "baken_native_bind_assets", "raster_fill_rect",
                      "display_swap_buffers_rect"):
            self.assertIn(token, begin)
        for forbidden in ("aml_", "pci_", "smp_", "scheduler_", "dma_"):
            self.assertNotIn(forbidden, begin)

    def test_mandatory_cutover_failures_have_visible_stable_codes(self):
        entry = self.post.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        for code in ("E-CPU-001", "E-PMM-001", "E-VMM-001", "E-HEAP-001",
                     "E-ACPI-001", "E-ACPI-ROOT", "E-MADT-001",
                     "E-APIC-001", "E-IRQ-001", "E-TIMER-001",
                     "E-TIMER-002", "E-FBWC-001"):
            self.assertIn(code, entry)
        self.assertLess(entry.index("baken_early_boot_begin"),
                        entry.index("post_cutover_activate_cpu"))

    def test_late_kernel_gates_report_component_names(self):
        kernel = self.runtime.split("pub fn baken_native_kernel_run", 1)[1]
        for token in ("E-AML-001", "E-PLAT-001", "E-SMP-001", "E-PROC-001",
                      "E-FPU-001", "E-SCHED-001", "E-SMP-004",
                      "ALL KERNEL BOOT GATES"):
            self.assertIn(token, kernel)
        self.assertIn("Photograph this screen and report the code", self.runtime)


if __name__ == "__main__":
    unittest.main()
