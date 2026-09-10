from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "kernel/src/drivers/input_device.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class InputDeviceTests(unittest.TestCase):
    def test_registry_is_bounded_non_heap_and_transport_agnostic(self):
        text = DEVICE.read_text(encoding="utf-8")
        self.assertIn("INPUT_DEVICE_CAPACITY: usize = 16", text)
        self.assertIn("static mut INPUT_DEVICES: [InputDeviceRecord; INPUT_DEVICE_CAPACITY]", text)
        self.assertNotIn("kernel_heap", text)
        self.assertNotIn("xhci_", text)
        self.assertNotIn("hid_input", text)
        self.assertNotIn("acpi_", text)
        self.assertNotIn("dma_", text)

    def test_identity_uses_device_id_plus_generation(self):
        text = DEVICE.read_text(encoding="utf-8")
        for token in (
            "pub device_id: u32", "pub generation: u32",
            "INPUT_DEVICE_GENERATION_INVALID", "input_device_generation_next",
            "INPUT_DEVICES[slot].generation == generation",
        ):
            self.assertIn(token, text)

    def test_lifecycle_is_explicit_and_stale_generation_is_invalidated(self):
        text = DEVICE.read_text(encoding="utf-8")
        for token in (
            "INPUT_DEVICE_STATE_ATTACHED", "INPUT_DEVICE_STATE_ACTIVE",
            "INPUT_DEVICE_STATE_DETACHED", "INPUT_DEVICE_STATE_FAILED",
            "pub fn input_device_attach", "pub fn input_device_activate",
            "pub fn input_device_detach", "pub fn input_device_mark_failed",
            "pub fn input_device_is_active",
        ):
            self.assertIn(token, text)
        detach = text.split("pub fn input_device_detach", 1)[1]
        self.assertIn("INPUT_DEVICES[slot].valid = false", detach)
        self.assertIn("INPUT_DEVICES[slot].generation = input_device_generation_next(generation)", detach)

    def test_registry_mutation_is_irq_safe_and_smp_serialized(self):
        text = DEVICE.read_text(encoding="utf-8")
        lock = text.split("fn input_device_lock_irq()", 1)[1].split(
            "fn input_device_unlock_irq", 1)[0]
        self.assertLess(lock.index("x86_irq_save_disable()"),
                        lock.index("spinlock_lock(&mut INPUT_DEVICE_LOCK)"))
        self.assertIn("spinlock_unlock(&mut INPUT_DEVICE_LOCK)", text)
        self.assertIn("x86_irq_restore(flags)", text)

    def test_transport_route_metadata_is_preserved_without_owning_transport(self):
        text = DEVICE.read_text(encoding="utf-8")
        for token in (
            "INPUT_TRANSPORT_USB", "INPUT_TRANSPORT_I2C",
            "pub transport_instance: u32", "pub transport_address: u32",
            "pub interface_number: u16",
        ):
            self.assertIn(token, text)

    def test_kernel_graph_registers_device_registry(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::input_device::*;", text)


if __name__ == "__main__":
    unittest.main()
