from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APERTURE = (ROOT / "kernel/src/drivers/pci_bar_aperture.sotlas").read_text(encoding="utf-8")
SIZING = (ROOT / "kernel/src/drivers/pci_bar_sizing.sotlas").read_text(encoding="utf-8")
LAYOUT = (ROOT / "kernel/src/drivers/pci_msix_layout.sotlas").read_text(encoding="utf-8")


class PciBarApertureContracts(unittest.TestCase):
    def _body(self, text: str, name: str) -> str:
        marker = f"fn {name}"
        start = text.index(marker)
        next_fn = text.find("\n@system\n", start + len(marker))
        if next_fn == -1:
            return text[start:]
        return text[start:next_fn]

    def test_registry_is_bounded_and_smp_safe(self):
        self.assertIn("PCI_BAR_APERTURE_CAPACITY: usize = 384", APERTURE)
        self.assertIn("SpinLock", APERTURE)
        self.assertIn("x86_irq_save_disable", APERTURE)
        self.assertIn("spinlock_lock", APERTURE)
        self.assertIn("spinlock_unlock", APERTURE)

    def test_publication_is_generation_bound_write_once_and_idempotent(self):
        body = self._body(APERTURE, "pci_bar_aperture_publish")
        self.assertIn("entry.bdf == bdf", body)
        self.assertIn("entry.device_generation == device_generation", body)
        self.assertIn("entry.bar_index == bar_index", body)
        self.assertIn("entry.base == base && entry.size == size", body)
        self.assertIn("entry.is_64bit == is_64bit", body)
        self.assertIn("return same", body)
        self.assertNotIn("PCI_BAR_APERTURES[slot] =", body)

    def test_publication_rejects_nonsensical_or_generationless_apertures(self):
        body = self._body(APERTURE, "pci_bar_aperture_publish")
        self.assertIn("device_generation == DEVICE_GENERATION_INVALID", body)
        self.assertIn("bar_index >= 6", body)
        self.assertIn("base == 0", body)
        self.assertIn("pci_bar_aperture_size_valid(size)", body)
        self.assertIn("(base & (size - 1)) != 0", body)

    def test_registry_contains_metadata_not_ownership_handles(self):
        struct = APERTURE[APERTURE.index("pub struct PciBarAperture"):APERTURE.index("static mut PCI_BAR_APERTURES")]
        self.assertIn("pub device_generation: u32", struct)
        for token in ("DeviceHandle", "DriverHandle", "ResourceHandle", "IrqHandle"):
            self.assertNotIn(token, struct)

    def test_snapshot_requires_exact_device_generation(self):
        body = self._body(APERTURE, "pci_bar_aperture_snapshot")
        self.assertIn("device_generation == DEVICE_GENERATION_INVALID", body)
        self.assertIn("entry.device_generation == device_generation", body)
        self.assertIn("entry.bdf == bdf", body)
        self.assertIn("entry.bar_index == bar_index", body)

    def test_sizing_publishes_only_after_restored_measurement_and_revalidation(self):
        body = self._body(SIZING, "pci_measure_owned_bar")
        measured = body.index("measurement.restored")
        verify = body.index("let verify_owner", measured)
        publish = body.index("pci_bar_aperture_publish", verify)
        result = body.rindex("valid: true")
        self.assertLess(measured, verify)
        self.assertLess(verify, publish)
        self.assertLess(publish, result)
        self.assertIn("pci_bar_aperture_snapshot", body)

    def test_sizing_binds_aperture_to_live_device_generation(self):
        body = self._body(SIZING, "pci_measure_owned_bar")
        self.assertIn("device.generation == DEVICE_GENERATION_INVALID", body)
        self.assertIn("bdf, device.generation, claim.bar_index, base", body)
        self.assertIn("bdf, device.generation, claim.bar_index,", body)
        self.assertIn("aperture.device_generation != device.generation", body)

    def test_sizing_does_not_mutate_global_pci_inventory(self):
        self.assertNotIn(".bars[", SIZING.split("pci_bar_aperture_publish", 1)[1])
        self.assertNotIn("size = measurement.size", SIZING)
        self.assertNotIn("pci_scan_all(", SIZING)

    def test_layout_consumes_generation_bound_registry_without_measurement(self):
        self.assertIn("pci_bar_aperture_snapshot", LAYOUT)
        self.assertIn("device_generation", self._body(LAYOUT, "pci_msix_layout_known_bar_size"))
        self.assertIn("device.generation", self._body(LAYOUT, "pci_msix_layout_window_proof"))
        self.assertNotIn("pci_config_measure_memory_bar", LAYOUT)
        self.assertNotIn("pci_bar_aperture_publish", LAYOUT)


if __name__ == "__main__":
    unittest.main()
