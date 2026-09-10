from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "kernel/src/acpi/aml_platform.sotlas"
INVENTORY = ROOT / "kernel/src/platform/inventory.sotlas"
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"


class AmlPlatformTests(unittest.TestCase):
    def test_platform_objects_are_explicit_and_bounded(self):
        text = PLATFORM.read_text(encoding="utf-8")
        for token in (
            "AML_PLATFORM_NAME_PIC",
            "AML_PLATFORM_NAME_PRT",
            "AML_PLATFORM_NAME_S5",
            "AML_PLATFORM_MAX_PRT_ENTRIES: usize = 256",
            "aml_platform_parse_s5",
            "aml_platform_parse_prt",
            "aml_platform_try_pic",
        ):
            self.assertIn(token, text)
        for forbidden in ("kernel_heap", "malloc", "calloc", "realloc"):
            self.assertNotIn(forbidden, text)

    def test_pic_is_apic_mode_and_not_a_raw_hardware_path(self):
        text = PLATFORM.read_text(encoding="utf-8")
        body = text.split("fn aml_platform_try_pic", 1)[1]
        body = body.split("pub fn aml_platform_is_ready", 1)[0]
        self.assertIn("let argument = aml_eval_integer(1);", body)
        self.assertIn("aml_evaluator_execute_method", body)
        for forbidden in (
            "__outb", "__outw", "__outl",
            "x86_mmio_write32", "pci_write_config32",
        ):
            self.assertNotIn(forbidden, body)

    def test_prt_validates_four_element_entries_and_pin_range(self):
        text = PLATFORM.read_text(encoding="utf-8")
        self.assertIn("view.count != 4", text)
        self.assertIn("pin.value > 3", text)
        self.assertIn("AML_PLATFORM_HARD_FAILURE = true", text)
        self.assertIn("AML_PLATFORM_PRT_UNRESOLVED", text)
        # Mutable boolean passed by pointer must remain explicitly typed. Sotlas
        # otherwise historically lowered it to int* while C expects _Bool*.
        self.assertIn("let mut source_is_link: bool = false;", text)

    def test_s5_sleep_types_are_three_bit_values(self):
        text = PLATFORM.read_text(encoding="utf-8")
        self.assertIn("first.value > 7", text)
        self.assertIn("second.value > 7", text)
        self.assertIn("AML_PLATFORM_S5_TYP_A", text)
        self.assertIn("AML_PLATFORM_S5_TYP_B", text)

    def test_platform_ready_is_after_aml7_and_aml8(self):
        inventory = INVENTORY.read_text(encoding="utf-8")
        self.assertLess(inventory.index("aml_regions_init()"),
                        inventory.index("aml_platform_init()"))
        self.assertLess(inventory.index("aml_platform_init()"),
                        inventory.index("PLATFORM_INFO.valid = true"))
        smoke = SMOKE.read_text(encoding="utf-8")
        for marker in (
            "ACPI_AML_PLATFORM_READY",
            "ACPI_AML_PLATFORM_FAILED",
        ):
            self.assertIn(marker, smoke)


if __name__ == "__main__":
    unittest.main()
