from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
AMD = ROOT / "kernel/src/drivers/amd_gpio.sotlas"
PHYSICAL = ROOT / "kernel/src/drivers/gpio_physical.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class AmdGpioContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = AMD.read_text(encoding="utf-8")

    def test_backend_is_separate_and_wired_vendor_neutrally(self):
        main = MAIN.read_text(encoding="utf-8")
        physical = PHYSICAL.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::amd_gpio::*;", main)
        self.assertIn("import kernel::drivers::amd_gpio::*;", physical)
        for token in (
            "amd_gpio_probe()", "amd_gpio_arm_connection(connection_id, generation)",
            "amd_gpio_disarm_connection(connection_id, generation)",
            "amd_gpio_irq_dispatch()",
        ):
            self.assertIn(token, physical)

    def test_identification_is_bounded_to_real_amd_acpi_ids(self):
        self.assertIn("AMDI0030 and AMDIF031", self.text)
        self.assertIn("65,77,68,73,48,48,51,48", self.text)
        self.assertIn("65,77,68,73,70,48,51,49", self.text)
        self.assertNotIn("vendor_id", self.text)

    def test_resources_come_only_from_validated_runtime_crs(self):
        for token in (
            "aml_runtime_resource_count(device_slot)",
            "aml_runtime_resource_at(device_slot, index)",
            "AMD_GPIO_ACPI_FIXED_MEMORY32",
            "AMD_GPIO_ACPI_EXTENDED_IRQ",
            "AMD_GPIO_ACPI_SMALL_IRQ",
            "active_page_tables_map_mmio_identity_4k",
            "ioapic_program_route_masked",
        ):
            self.assertIn(token, self.text)
        self.assertNotIn("0xFED", self.text)
        self.assertIn("level_triggered = (flags & 0x01) != 0", self.text)
        self.assertIn("active_low = (flags & 0x08) != 0", self.text)

    def test_arm_refuses_existing_irq_ownership_and_output_pins(self):
        arm = self.text.split("pub fn amd_gpio_arm_connection", 1)[1].split(
            "pub fn amd_gpio_disarm_connection", 1
        )[0]
        self.assertIn("AMD_GPIO_INTERRUPT_ENABLE | AMD_GPIO_INTERRUPT_UNMASK", arm)
        self.assertIn("AMD_GPIO_OUTPUT_ENABLE", arm)
        self.assertIn("gpio_connection_activate(connection_id, generation)", arm)
        self.assertIn("ioapic_program_route_unmasked", arm)

    def test_irq_checks_pending_and_emits_controller_eoi(self):
        irq = self.text.split("pub fn amd_gpio_irq_dispatch", 1)[1]
        self.assertIn("AMD_GPIO_IRQ_PENDING", irq)
        self.assertIn("gpio_connection_signal(armed.connection_id)", irq)
        self.assertIn("AMD_GPIO_WAKE_INT_MASTER", irq)
        self.assertIn("AMD_GPIO_MASTER_EOI", irq)

    def test_teardown_is_generation_safe_and_restores_register(self):
        disarm = self.text.split("pub fn amd_gpio_disarm_connection", 1)[1].split(
            "pub fn amd_gpio_irq_dispatch", 1
        )[0]
        self.assertIn("AMD_GPIO_ARMED[i].generation == generation", disarm)
        self.assertIn("gpio_connection_deactivate(connection_id, generation)", disarm)
        self.assertIn("armed.original_register", disarm)
        self.assertIn("ioapic_program_route_masked", disarm)


if __name__ == "__main__":
    unittest.main()
