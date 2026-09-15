import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "kernel/src/drivers/intel_gpio_generation_catalog.sotlas"


class IntelGpioGenerationCatalogContract(unittest.TestCase):
    def test_generations_are_distinct(self):
        text = CATALOG.read_text(encoding="utf-8")
        for name in ("TIGER_LAKE", "ALDER_LAKE", "RAPTOR_LAKE", "METEOR_LAKE", "LUNAR_LAKE"):
            self.assertIn("INTEL_GPIO_GEN_" + name, text)

    def test_unknown_layout_cannot_touch_hardware(self):
        text = CATALOG.read_text(encoding="utf-8")
        self.assertIn("INTEL_GPIO_LAYOUT_UNAVAILABLE", text)
        self.assertIn("hardware_access_allowed: false", text)


if __name__ == "__main__":
    unittest.main()
