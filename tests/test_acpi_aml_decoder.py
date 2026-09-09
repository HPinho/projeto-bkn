"""Contratos do decoder estrutural AML fail-closed."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DECODER = ROOT / "kernel/src/acpi/aml_decoder.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class AcpiAmlDecoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DECODER.read_text(encoding="utf-8")

    def test_cursor_checks_remaining_without_overflowing_offset_plus_count(self):
        body = self.source.split("fn aml_cursor_can_read", 1)[1].split(
            "pub fn aml_cursor_peek_u8", 1
        )[0]
        self.assertIn("(*cursor).offset <= (*cursor).length", body)
        self.assertIn("count <= (*cursor).length - (*cursor).offset", body)
        self.assertNotIn("offset + count", body)
        self.assertIn("aml_cursor_fail(cursor)", self.source)
        take = self.source.split("pub fn aml_cursor_take", 1)[1].split(
            "fn aml_cursor_read_integer_bytes", 1
        )[0]
        self.assertIn("offset > 0xFFFFFFFFFFFFFFFF - base_address", take)
        self.assertIn("(*cursor).offset += count", take)
        self.assertIn("length: count", take)

    def test_pkg_length_decodes_one_to_four_bytes_and_enforces_boundary(self):
        body = self.source.split("pub fn aml_decode_pkg_length", 1)[1].split(
            "fn aml_name_string_invalid", 1
        )[0]
        for token in (
            "let follow = ((lead >> 6) & 3) as usize",
            "(lead & 0x3F) as usize",
            "if (lead & 0x30) != 0",
            "part << (4 + index * 8)",
            "if package_bytes < encoded",
            "let body = package_bytes - encoded",
            "aml_cursor_can_read(cursor as *const AmlCursor, body)",
        ):
            self.assertIn(token, body)

    def test_name_string_supports_root_parent_dual_multi_and_valid_namesegs(self):
        body = self.source.split("pub fn aml_decode_name_string", 1)[1].split(
            "fn aml_integer_invalid", 1
        )[0]
        for token in (
            "AML_ROOT_CHAR", "AML_PARENT_PREFIX_CHAR", "AML_NULL_NAME",
            "AML_DUAL_NAME_PREFIX", "AML_MULTI_NAME_PREFIX",
            "segment_count > AML_NAME_MAX_SEGMENTS", "aml_decode_name_seg(cursor)",
        ):
            self.assertIn(token, body)
        chars = self.source.split("fn aml_name_lead_valid", 1)[1].split(
            "fn aml_decode_name_seg", 1
        )[0]
        self.assertIn("value == '_' as u8", chars)
        self.assertIn("value >= 'A' as u8 && value <= 'Z' as u8", chars)
        self.assertIn("value >= '0' as u8 && value <= '9' as u8", chars)

    def test_integer_constants_are_little_endian_and_explicitly_typed(self):
        body = self.source.split("pub fn aml_decode_integer", 1)[1].split(
            "pub fn aml_decoder_self_test", 1
        )[0]
        for token in (
            "AML_ZERO_OP", "AML_ONE_OP", "AML_ONES_OP", "AML_BYTE_PREFIX",
            "AML_WORD_PREFIX", "AML_DWORD_PREFIX", "AML_QWORD_PREFIX",
            "aml_cursor_read_integer_bytes(cursor, byte_count)",
        ):
            self.assertIn(token, body)
        self.assertIn("<< (index * 8)", self.source)

    def test_runtime_self_test_covers_valid_and_reserved_encodings(self):
        body = self.source.split("pub fn aml_decoder_self_test", 1)[1].split(
            "pub fn aml_decoder_emit_ready_marker", 1
        )[0]
        self.assertIn("package.package_bytes != 65", body)
        self.assertIn("aml_cursor_take(&mut package_cursor, package.body_bytes)", body)
        self.assertIn("package_cursor.offset != 65", body)
        self.assertIn("name.segment_count != 2", body)
        self.assertIn("integer.value != 0x0102030405060708", body)
        self.assertIn("let invalid_package: [u8; 2] = [0x70,0]", body)
        self.assertIn("AML_DECODER_READY = true", body)
        marker = self.source.split("pub fn aml_decoder_emit_ready_marker", 1)[1]
        self.assertIn("if !AML_DECODER_READY", marker)

    def test_all_qemu_gates_require_decoder_marker(self):
        runtime = RUNTIME.read_text(encoding="utf-8")
        run = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertLess(run.index("aml_tables_init()"), run.index("aml_decoder_self_test()"))
        self.assertLess(run.index("aml_decoder_self_test()"), run.index("platform_inventory_init()"))
        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("ACPI_AML_DECODER_READY", REQUIRED)
        nvme = (ROOT / ".github/workflows/baken_nvme_only.yml").read_text(encoding="utf-8")
        smp = (ROOT / ".github/workflows/baken_smp.yml").read_text(encoding="utf-8")
        self.assertIn("'BAKEN:ACPI_AML_DECODER_READY'", nvme)
        self.assertIn("require_marker 'BAKEN:ACPI_AML_DECODER_READY'", smp)

    def test_decoder_does_not_execute_aml_or_touch_hardware(self):
        lower = self.source.lower()
        for forbidden in ("__out", "mmio_write", "pci_write", "evaluate_method", "execute_opcode"):
            self.assertNotIn(forbidden, lower)


if __name__ == "__main__":
    unittest.main()
