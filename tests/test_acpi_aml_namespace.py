"""Contratos do núcleo read-only do namespace AML."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
NAMESPACE = ROOT / "kernel/src/acpi/aml_namespace.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class AcpiAmlNamespaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = NAMESPACE.read_text(encoding="utf-8")

    def test_namespace_is_fixed_capacity_and_does_not_depend_on_heap(self):
        self.assertIn("AML_NAMESPACE_MAX_NODES: usize = 256", self.source)
        self.assertIn("static mut AML_NAMESPACE_NODES", self.source)
        self.assertIn("[AmlNamespaceNode; AML_NAMESPACE_MAX_NODES]", self.source)
        lower = self.source.lower()
        for forbidden in ("heap_alloc", "kmalloc", "malloc(", "free("):
            self.assertNotIn(forbidden, lower)

    def test_public_api_is_read_only_after_foundation_ready(self):
        for token in (
            "pub fn aml_namespace_is_ready",
            "pub fn aml_namespace_count",
            "pub fn aml_namespace_node",
            "pub fn aml_namespace_find_child",
            "pub fn aml_namespace_lookup",
        ):
            self.assertIn(token, self.source)
        self.assertIn("fn aml_namespace_define_path", self.source)
        self.assertNotIn("pub fn aml_namespace_define_path", self.source)
        self.assertIn("if !AML_NAMESPACE_READY", self.source)

    def test_name_resolution_honors_root_and_parent_prefixes(self):
        start = self.source.split("fn aml_namespace_start_scope", 1)[1].split(
            "fn aml_namespace_lookup_internal", 1
        )[0]
        self.assertIn("if (*name).rooted", start)
        self.assertIn("scope = 0", start)
        self.assertIn("(*name).parent_prefixes", start)
        self.assertIn("if scope == 0", start)
        lookup = self.source.split("fn aml_namespace_lookup_internal", 1)[1].split(
            "fn aml_namespace_define_path", 1
        )[0]
        self.assertIn("aml_namespace_find_child_internal", lookup)
        self.assertIn("(*name).segments[index]", lookup)

    def test_duplicates_and_capacity_fail_closed(self):
        allocator = self.source.split("fn aml_namespace_allocate_child", 1)[1].split(
            "fn aml_namespace_start_scope", 1
        )[0]
        self.assertIn("AML_NAMESPACE_COUNT >= AML_NAMESPACE_MAX_NODES", allocator)
        self.assertIn("aml_namespace_find_child_internal(parent, segment)", allocator)
        self.assertIn("return AML_NAMESPACE_INVALID_INDEX", allocator)
        init = self.source.split("pub fn aml_namespace_foundation_init", 1)[1].split(
            "pub fn aml_namespace_emit_ready_marker", 1
        )[0]
        self.assertIn("before_duplicate", init)
        self.assertIn("AML_NAMESPACE_COUNT != before_duplicate", init)

    def test_self_test_covers_absolute_relative_and_parent_paths(self):
        init = self.source.split("pub fn aml_namespace_foundation_init", 1)[1].split(
            "pub fn aml_namespace_emit_ready_marker", 1
        )[0]
        for token in (
            "let sb_bytes: [u8; 5] = [0x5C,95,83,66,95]",
            "let pci_bytes: [u8; 4] = [80,67,73,48]",
            "let hid_bytes: [u8; 4] = [95,72,73,68]",
            "let absolute_pci_bytes: [u8; 10]",
            "let parent_sta_bytes: [u8; 5] = [0x5E,95,83,84,65]",
            "hid_node.integer_value != 0x1234",
            "aml_namespace_reset();",
            "AML_NAMESPACE_READY = true",
        ):
            self.assertIn(token, init)
        marker = self.source.split("pub fn aml_namespace_emit_ready_marker", 1)[1]
        self.assertIn("aml_namespace_count() != 1", marker)

    def test_namespace_foundation_does_not_execute_aml_or_touch_hardware(self):
        lower = self.source.lower()
        for forbidden in (
            "evaluate_method", "execute_opcode", "operation_region",
            "mmio_write", "pci_write", "__out", "io_write",
        ):
            self.assertNotIn(forbidden, lower)

    def test_all_runtime_gates_require_namespace_marker(self):
        runtime = RUNTIME.read_text(encoding="utf-8")
        run = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertLess(run.index("aml_decoder_self_test()"),
                        run.index("aml_namespace_foundation_init()"))
        self.assertLess(run.index("aml_namespace_foundation_init()"),
                        run.index("platform_inventory_init()"))
        self.assertIn("aml_namespace_emit_ready_marker()", run)

        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("ACPI_AML_NAMESPACE_READY", REQUIRED)
        from tools.scripts.run_smp_qemu import REQUIRED_MARKERS
        self.assertIn("BAKEN:ACPI_AML_NAMESPACE_READY", REQUIRED_MARKERS)

        nvme = (ROOT / ".github/workflows/baken_nvme_only.yml").read_text(encoding="utf-8")
        smp = (ROOT / ".github/workflows/baken_smp.yml").read_text(encoding="utf-8")
        self.assertIn("'BAKEN:ACPI_AML_NAMESPACE_READY'", nvme)
        self.assertIn("python3 tests/test_acpi_aml_namespace.py", smp)
        self.assertIn("require_marker 'BAKEN:ACPI_AML_NAMESPACE_READY'", smp)


if __name__ == "__main__":
    unittest.main()
