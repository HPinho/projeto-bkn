"""DF-4b1: Generic IRQ Registry integrado ao dispatcher x86 sem regressao bootstrap."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (ROOT / "kernel/src/interrupts/registry.sotlas").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "kernel/src/interrupts/irq.sotlas").read_text(encoding="utf-8")
DRIVERS = (ROOT / "kernel/src/device/driver_registry.sotlas").read_text(encoding="utf-8")
SELF_TEST = (ROOT / "kernel/src/device/foundation_self_test.sotlas").read_text(encoding="utf-8")


class GenericIrqRegistryTests(unittest.TestCase):
    def test_dynamic_window_preserves_bootstrap_vectors_and_is_installed(self):
        self.assertIn("IRQ_DYNAMIC_VECTOR_FIRST: u16 = 0x50", REGISTRY)
        self.assertIn("IRQ_DYNAMIC_VECTOR_LAST: u16 = 0xEF", REGISTRY)
        for vector in ("0x40", "0x41", "0x42", "0x43", "0x44", "0x45", "0x46", "0xFF"):
            self.assertIn(vector, BOOTSTRAP)

        self.assertIn("import kernel::interrupts::registry::*;", BOOTSTRAP)
        helper = BOOTSTRAP.split("fn irq_install_dynamic_gates", 1)[1].split(
            "pub fn irq_prepare_idt", 1
        )[0]
        self.assertIn("let mut vector: u16 = IRQ_DYNAMIC_VECTOR_FIRST", helper)
        self.assertIn("while vector <= IRQ_DYNAMIC_VECTOR_LAST", helper)
        self.assertIn("irq_install_gate(vector)", helper)

        prepare = BOOTSTRAP.split("pub fn irq_prepare_idt", 1)[1].split(
            "pub fn irq_prepare_masked_ioapic_routes", 1
        )[0]
        self.assertIn("irq_registry_init()", prepare)
        self.assertIn("irq_registry_is_ready()", prepare)
        self.assertIn("irq_install_dynamic_gates()", prepare)
        self.assertIn("irq_install_user_gate(IRQ_VECTOR_RESCHEDULE)", prepare)

    def test_dynamic_dispatch_uses_registry_then_single_core_eoi(self):
        dispatch = BOOTSTRAP.split("pub fn sotlas_x86_irq_dispatch", 1)[1]
        dynamic = dispatch.split("// Generic device IRQs", 1)[1]
        self.assertIn("vector >= IRQ_DYNAMIC_VECTOR_FIRST as u64", dynamic)
        self.assertIn("vector <= IRQ_DYNAMIC_VECTOR_LAST as u64", dynamic)
        registry_call = dynamic.index("irq_registry_dispatch(vector as u16)")
        eoi = dynamic.index("lapic_eoi()")
        returned = dynamic.index("return frame_address")
        self.assertLess(registry_call, eoi)
        self.assertLess(eoi, returned)
        self.assertIn("IRQ_DYNAMIC_COUNT += 1", dynamic)
        self.assertIn("IRQ_DYNAMIC_UNHANDLED_COUNT += 1", dynamic)
        self.assertNotIn("lapic_eoi", REGISTRY)

    def test_public_registration_uses_descriptor_callback_abi(self):
        self.assertIn("pub struct IrqDescriptor", REGISTRY)
        self.assertIn("pub handler: fn(DeviceHandle, u16) -> bool", REGISTRY)
        signature = REGISTRY.split("pub fn irq_registry_register", 1)[1].split("{", 1)[0]
        self.assertIn("descriptor: IrqDescriptor", signature)
        self.assertNotIn("handler: fn(", signature)
        register = REGISTRY.split("pub fn irq_registry_register", 1)[1].split(
            "pub fn irq_registry_vector", 1
        )[0]
        self.assertIn("handler: descriptor.handler", register)
        self.assertIn("IrqDescriptor {", SELF_TEST)
        self.assertIn("handler: df_self_test_irq_handler", SELF_TEST)

    def test_registration_uses_resource_manager_as_vector_owner(self):
        register = REGISTRY.split("pub fn irq_registry_register", 1)[1].split(
            "pub fn irq_registry_vector", 1
        )[0]
        self.assertIn("RESOURCE_KIND_IRQ", register)
        self.assertIn("resource_claim(device, driver", register)
        self.assertIn("irq_owner_can_register(device, driver)", register)
        owner = REGISTRY.split("fn irq_owner_can_register", 1)[1].split(
            "pub fn irq_registry_init", 1
        )[0]
        self.assertIn("driver_handle_equal(snapshot.driver, driver)", owner)
        self.assertIn("DEVICE_STATE_BINDING", owner)
        self.assertIn("DEVICE_STATE_ACTIVE", owner)
        self.assertIn("IRQ_GENERATIONS", REGISTRY)
        self.assertIn("IRQ_RECORDS[slot].handle.generation == handle.generation", REGISTRY)

    def test_handler_runs_outside_registry_lock_with_inflight_accounting(self):
        dispatch = REGISTRY.split("pub fn irq_registry_dispatch", 1)[1].split(
            "pub fn irq_registry_active_count", 1
        )[0]
        unlock = dispatch.index("irq_unlock_irq(flags)")
        callback = dispatch.index("selected.handler(selected.owner_device, vector)")
        self.assertLess(unlock, callback)
        self.assertIn("operations_in_flight += 1", dispatch)
        self.assertIn("operations_in_flight -= 1", dispatch)

    def test_unregister_releases_resource_outside_irq_lock(self):
        unregister = REGISTRY.split("pub fn irq_registry_unregister", 1)[1].split(
            "pub fn irq_registry_release_all", 1
        )[0]
        self.assertIn("operations_in_flight == 0", unregister)
        self.assertIn("device_handle_equal(IRQ_RECORDS[slot].owner_device, device)", unregister)
        self.assertIn("driver_handle_equal(IRQ_RECORDS[slot].owner_driver, driver)", unregister)
        unlock = unregister.index("irq_unlock_irq(flags)")
        release = unregister.index("resource_release(resource, device, driver)")
        self.assertLess(unlock, release)

    def test_failed_probe_cleans_irq_registry_before_raw_resources(self):
        bind = DRIVERS.split("pub fn driver_bind", 1)[1].split("pub fn driver_unbind", 1)[0]
        irq_cleanup = bind.index("irq_registry_release_all(device, selected)")
        raw_cleanup = bind.index("resource_release_all(device, selected)")
        abort = bind.index("device_core_abort_bind(device, selected)")
        self.assertLess(irq_cleanup, raw_cleanup)
        self.assertLess(raw_cleanup, abort)

    def test_runtime_self_test_covers_register_dispatch_and_remove(self):
        for token in (
            "irq_registry_init()",
            "irq_registry_register",
            "irq_registry_dispatch(vector)",
            "irq_registry_unregister",
            "irq_registry_active_count() != 1",
            "resource_count != 3",
        ):
            self.assertIn(token, SELF_TEST)


if __name__ == "__main__":
    unittest.main()
