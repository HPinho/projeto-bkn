from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "kernel/src/acpi/aml_runtime_resources.sotlas"
TIGER = ROOT / "kernel/src/drivers/intel_tigerlake_gpio.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class AcpiRuntimeResourceTests(unittest.TestCase):
    def test_runtime_view_is_in_native_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::acpi::aml_runtime_resources::*;", text)

    def test_static_and_dynamic_crs_share_one_bounded_view(self):
        text = VIEW.read_text(encoding="utf-8")
        for token in (
            "pub fn aml_runtime_resource_count",
            "pub fn aml_runtime_resource_at",
            "pub fn aml_runtime_resources_are_dynamic",
            "(*source).crs_static && !(*source).crs_requires_evaluator",
            "(*dynamic).crs_resolved",
            "AML_DYNAMIC_MAX_RESOURCE_DESCRIPTORS",
            "AML_RESOURCE_END_TAG_NAME",
            "next > length",
        ):
            self.assertIn(token, text)

    def test_dynamic_stream_is_fail_closed(self):
        text = VIEW.read_text(encoding="utf-8")
        self.assertIn("next < payload_offset", text)
        self.assertIn("payload_length != AML_RESOURCE_END_TAG_LENGTH", text)
        self.assertIn("next != length", text)
        self.assertNotIn("while true", text)

    def test_tiger_lake_consumes_runtime_view(self):
        text = TIGER.read_text(encoding="utf-8")
        self.assertIn("import kernel::acpi::aml_runtime_resources::*;", text)
        self.assertIn("aml_runtime_resource_count(device_slot)", text)
        self.assertIn("aml_runtime_resource_at(device_slot, index)", text)
        probe = text.split("fn intel_tgl_probe_device", 1)[1].split(
            "pub fn intel_tigerlake_gpio_probe", 1
        )[0]
        self.assertNotIn("crs_static", probe)
        self.assertNotIn("crs_requires_evaluator", probe)


if __name__ == "__main__":
    unittest.main()
