from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "kernel/src/drivers/gpio_core.sotlas"
PHYSICAL = ROOT / "kernel/src/drivers/gpio_physical.sotlas"
TGL = ROOT / "kernel/src/drivers/intel_tigerlake_gpio.sotlas"
MANAGER = ROOT / "kernel/src/drivers/i2c_hid_manager.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
X86 = ROOT / "tools/sotlas_compile/x86_intrinsics.py"


class IntelTigerLakeGpioPhys0ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = CORE.read_text(encoding="utf-8")
        cls.physical = PHYSICAL.read_text(encoding="utf-8")
        cls.tgl = TGL.read_text(encoding="utf-8")
        cls.manager = MANAGER.read_text(encoding="utf-8")
        cls.irq = IRQ.read_text(encoding="utf-8")
        cls.x86 = X86.read_text(encoding="utf-8")

    def test_gpio_core_remains_vendor_neutral(self):
        for vendor in ("tigerlake", "intel_", "amd_", "qualcomm", "mediatek", "tegra"):
            self.assertNotIn(vendor, self.core.lower())
        self.assertIn("GPIO_PIN_STATE_CONFIGURED", self.core)
        self.assertIn("pub fn gpio_connection_activate", self.core)
        self.assertIn("pub fn gpio_connection_deactivate", self.core)

    def test_registration_is_configured_before_physical_arm(self):
        register = self.core.index("pub fn gpio_connection_register_from_acpi")
        activate = self.core.index("pub fn gpio_connection_activate")
        register_body = self.core[register:activate]
        self.assertIn("gpio.pin_count != 1", register_body)
        self.assertIn("state = GPIO_PIN_STATE_CONFIGURED", register_body)
        self.assertNotIn("state = GPIO_PIN_STATE_ACTIVE", register_body)

    def test_unregister_refuses_live_connection(self):
        start = self.core.index("pub fn gpio_connection_unregister")
        end = self.core.index("pub fn gpio_connection_mask", start)
        body = self.core[start:end]
        self.assertIn("GPIO_PIN_STATE_CONFIGURED", body)
        self.assertIn("GPIO_PIN_STATE_DETACHED", body)
        self.assertNotIn("GPIO_PIN_STATE_ACTIVE ||", body)
        self.assertNotIn("GPIO_PIN_STATE_MASKED ||", body)

    def test_consumers_use_vendor_neutral_dispatcher(self):
        self.assertIn("import kernel::drivers::gpio_physical::*;", self.manager)
        self.assertIn("gpio_physical_probe_all();", self.manager)
        self.assertIn("gpio_physical_arm_connection(", self.manager)
        self.assertIn("gpio_physical_disarm_connection(", self.manager)
        self.assertNotIn("intel_tigerlake_gpio", self.manager)
        self.assertIn("import kernel::drivers::gpio_physical::*;", self.irq)
        self.assertIn("gpio_physical_irq_dispatch();", self.irq)
        self.assertNotIn("intel_tigerlake_gpio", self.irq)

    def test_dispatcher_is_extension_point_not_core_policy(self):
        self.assertIn("module kernel::drivers::gpio_physical;", self.physical)
        self.assertIn("import kernel::drivers::intel_tigerlake_gpio::*;", self.physical)
        self.assertIn("pub fn gpio_physical_probe_all", self.physical)
        self.assertIn("pub fn gpio_physical_arm_connection", self.physical)
        self.assertIn("pub fn gpio_physical_disarm_connection", self.physical)
        self.assertIn("pub fn gpio_physical_irq_dispatch", self.physical)

    def test_tiger_lake_backend_has_only_initial_acpi_ids(self):
        self.assertIn("INTEL_TGL_FAMILY_LP", self.tgl)
        self.assertIn("INTEL_TGL_FAMILY_H", self.tgl)
        self.assertIn("73,78,84,51,52,67,53", self.tgl)  # INT34C5
        self.assertIn("73,78,84,67,49,48,53,53", self.tgl)  # INTC1055
        self.assertIn("73,78,84,51,52,67,54", self.tgl)  # INT34C6

    def test_probe_uses_validated_runtime_crs_and_real_mmio(self):
        for token in (
            "aml_runtime_resource_count(device_slot)",
            "aml_runtime_resource_at(device_slot, index)",
            "AML_RESOURCE_KIND_LARGE",
            "INTEL_TGL_ACPI_FIXED_MEMORY32",
            "INTEL_TGL_ACPI_EXTENDED_IRQ",
            "active_page_tables_map_mmio_identity_4k",
            "x86_mmio_read32",
            "x86_mmio_write32",
        ):
            self.assertIn(token, self.tgl)

    def test_pad_stride_is_discovered_from_hardware_revision(self):
        self.assertIn("INTEL_TGL_REVID", self.tgl)
        self.assertIn("INTEL_TGL_PADBAR", self.tgl)
        self.assertIn("if revision >= 0x0092 { stride = 16; }", self.tgl)
        self.assertIn("INTEL_TGL_COMMUNITY_STRIDE", self.tgl)

    def test_pad_ownership_and_locks_fail_closed(self):
        for token in (
            "INTEL_TGL_PAD_OWN",
            "INTEL_TGL_LP_PADCFGLOCK",
            "INTEL_TGL_H_PADCFGLOCK",
            "INTEL_TGL_LP_HOSTSW_OWN",
            "INTEL_TGL_H_HOSTSW_OWN",
            "intel_tgl_pad_owned_by_host",
            "intel_tgl_pad_unlocked_and_hostsw",
        ):
            self.assertIn(token, self.tgl)
        self.assertNotIn("x86_mmio_write32(base + intel_tgl_hostown_offset", self.tgl)

    def test_pad_programming_is_gpio_input_only(self):
        for token in (
            "INTEL_TGL_PADCFG0_PMODE_MASK",
            "INTEL_TGL_PADCFG0_GPIORXDIS",
            "INTEL_TGL_PADCFG0_GPIROUTIOXAPIC",
            "INTEL_TGL_PADCFG0_RXEVCFG_MASK",
            "INTEL_TGL_PADCFG0_RXINV",
        ):
            self.assertIn(token, self.tgl)
        self.assertIn("intel_tgl_restore_pad", self.tgl)

    def test_real_interrupt_path_uses_status_enable_and_logical_signal(self):
        self.assertIn("INTEL_TGL_GPI_IS", self.tgl)
        self.assertIn("INTEL_TGL_GPI_IE", self.tgl)
        self.assertIn("intel_tgl_controller_ie_is_owned", self.tgl)
        self.assertIn("gpio_connection_signal(armed.connection_id)", self.tgl)
        self.assertIn("x86_mmio_write32(is_addr, pending)", self.tgl)

    def test_gpio_has_dedicated_x86_vector_and_real_stub(self):
        self.assertIn("pub const IRQ_VECTOR_GPIO: u16 = 0x46;", self.irq)
        self.assertIn("irq_install_gate(IRQ_VECTOR_GPIO)", self.irq)
        self.assertIn("if vector == IRQ_VECTOR_GPIO as u64", self.irq)
        self.assertIn("SOTLAS_X86_IRQ_STUB(70)", self.x86)
        self.assertIn("case 70:return(uint64_t)(uintptr_t)&__sotlas_x86_irq_70;", self.x86)

    def test_hid_is_exposed_only_after_physical_arm(self):
        arm = self.manager.index("gpio_physical_arm_connection(")
        bind = self.manager.index("i2c_device_set_gpio(")
        descriptor = self.manager.index("i2c_hid_read_descriptor_physical(")
        self.assertLess(arm, bind)
        self.assertLess(bind, descriptor)
        self.assertIn("No synthetic/polled IRQ fallback", self.manager)

    def test_no_foreign_os_runtime_or_source_dependency_is_introduced(self):
        combined = "\n".join((self.core, self.physical, self.tgl, self.manager, self.irq)).lower()
        for token in ("#include <linux", "windows.h", "freebsd", "netbsd", "openbsd", "darwin/xnu"):
            self.assertNotIn(token, combined)


if __name__ == "__main__":
    unittest.main()
