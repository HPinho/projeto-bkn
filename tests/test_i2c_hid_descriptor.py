from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_hid_descriptor.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def build_canonical_hid_desc(
    hid_desc_len=30,
    bcd_version=0x0100,
    report_desc_len=52,
    report_desc_reg=0x0020,
    input_reg=0x0021,
    max_input_len=64,
    output_reg=0x0022,
    max_output_len=64,
    command_reg=0x0023,
    data_reg=0x0024,
    vendor_id=0x04F3,
    product_id=0x3048,
    version_id=0x0001,
    reserved=0x00000000
) -> bytes:
    return struct.pack(
        "<13H I",
        hid_desc_len,
        bcd_version,
        report_desc_len,
        report_desc_reg,
        input_reg,
        max_input_len,
        output_reg,
        max_output_len,
        command_reg,
        data_reg,
        vendor_id,
        product_id,
        version_id,
        reserved
    )


def decode_hid_descriptor(buf: bytes) -> dict | None:
    if len(buf) < 30:
        return None
    (
        hid_len,
        bcd_ver,
        rep_len,
        rep_reg,
        in_reg,
        max_in_len,
        out_reg,
        max_out_len,
        cmd_reg,
        data_reg,
        vid,
        pid,
        ver_id,
        reserved
    ) = struct.unpack_from("<13H I", buf, 0)

    if hid_len != 30:
        return None
    if bcd_ver != 0x0100:
        return None
    if rep_len == 0 or rep_len > 4096:
        return None
    if max_in_len < 2:
        return None
    if cmd_reg == 0:
        return None

    return {
        "w_hid_desc_length": hid_len,
        "bcd_version": bcd_ver,
        "w_report_desc_length": rep_len,
        "w_report_desc_register": rep_reg,
        "w_input_register": in_reg,
        "w_max_input_length": max_in_len,
        "w_output_register": out_reg,
        "w_max_output_length": max_out_len,
        "w_command_register": cmd_reg,
        "w_data_register": data_reg,
        "w_vendor_id": vid,
        "w_product_id": pid,
        "w_version_id": ver_id,
        "reserved": reserved,
        "valid": True
    }


class I2cHidDescriptorTests(unittest.TestCase):
    """Testes semânticos e contratuais do descritor de dispositivo I2C-HID."""

    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_zero_dynamic_heap_allocation(self):
        self.assertNotIn("kernel_heap", self.text)
        self.assertNotIn("alloc(", self.text)
        self.assertNotIn("malloc(", self.text)

    def test_module_registered_in_kernel_main(self):
        self.assertIn("import kernel::drivers::i2c_hid_descriptor::*;", self.main)

    def test_spec_constants_defined(self):
        self.assertIn("pub const I2C_HID_DESC_LENGTH: usize = 30;", self.text)
        self.assertIn("pub const I2C_HID_BCD_VERSION_1_00: u16 = 0x0100;", self.text)
        self.assertIn("pub const I2C_HID_MAX_REPORT_DESC_LENGTH: usize = 4096;", self.text)

    def test_canonical_30_byte_struct_definition(self):
        self.assertIn("pub struct I2cHidDescriptor", self.text)
        for field in (
            "w_hid_desc_length: u16",
            "bcd_version: u16",
            "w_report_desc_length: u16",
            "w_report_desc_register: u16",
            "w_input_register: u16",
            "w_max_input_length: u16",
            "w_output_register: u16",
            "w_max_output_length: u16",
            "w_command_register: u16",
            "w_data_register: u16",
            "w_vendor_id: u16",
            "w_product_id: u16",
            "w_version_id: u16",
            "reserved: u32",
            "valid: bool",
        ):
            self.assertIn(field, self.text)

    def test_decode_valid_descriptor(self):
        raw = build_canonical_hid_desc()
        self.assertEqual(len(raw), 30)
        desc = decode_hid_descriptor(raw)
        self.assertIsNotNone(desc)
        self.assertEqual(desc["w_hid_desc_length"], 30)
        self.assertEqual(desc["bcd_version"], 0x0100)
        self.assertEqual(desc["w_report_desc_length"], 52)
        self.assertEqual(desc["w_report_desc_register"], 0x0020)
        self.assertEqual(desc["w_input_register"], 0x0021)
        self.assertEqual(desc["w_max_input_length"], 64)
        self.assertEqual(desc["w_command_register"], 0x0023)
        self.assertEqual(desc["w_vendor_id"], 0x04F3)
        self.assertEqual(desc["w_product_id"], 0x3048)
        self.assertTrue(desc["valid"])

    def test_reject_short_buffer(self):
        raw = build_canonical_hid_desc()[:29]
        self.assertIsNone(decode_hid_descriptor(raw))

    def test_reject_invalid_length_field(self):
        raw = build_canonical_hid_desc(hid_desc_len=28)
        self.assertIsNone(decode_hid_descriptor(raw))
        raw2 = build_canonical_hid_desc(hid_desc_len=32)
        self.assertIsNone(decode_hid_descriptor(raw2))

    def test_reject_unsupported_bcd_version(self):
        raw = build_canonical_hid_desc(bcd_version=0x0200)
        self.assertIsNone(decode_hid_descriptor(raw))
        raw2 = build_canonical_hid_desc(bcd_version=0x0090)
        self.assertIsNone(decode_hid_descriptor(raw2))

    def test_reject_zero_or_excessive_report_desc_len(self):
        raw_zero = build_canonical_hid_desc(report_desc_len=0)
        self.assertIsNone(decode_hid_descriptor(raw_zero))
        raw_huge = build_canonical_hid_desc(report_desc_len=4097)
        self.assertIsNone(decode_hid_descriptor(raw_huge))

    def test_reject_invalid_max_input_length(self):
        # max_input_length deve ser no mínimo 2 (tamanho dos 2 bytes de cabeçalho de comprimento)
        raw = build_canonical_hid_desc(max_input_len=1)
        self.assertIsNone(decode_hid_descriptor(raw))
        raw_zero = build_canonical_hid_desc(max_input_len=0)
        self.assertIsNone(decode_hid_descriptor(raw_zero))

    def test_reject_zero_command_register(self):
        raw = build_canonical_hid_desc(command_reg=0)
        self.assertIsNone(decode_hid_descriptor(raw))

    def test_touchpad_and_digitizer_usage_support(self):
        # Verifica suporte a Digitizer e Touchpad no parser de descritor HID
        rep_desc_text = (ROOT / "kernel/src/drivers/hid_report_descriptor.sotlas").read_text(encoding="utf-8")
        self.assertIn("pub const HID_USAGE_PAGE_DIGITIZER: u32 = 0x0D;", rep_desc_text)
        self.assertIn("pub const HID_USAGE_DIGITIZER_TOUCH_PAD: u32 = 0x05;", rep_desc_text)
        self.assertIn("pub has_touchpad_application: bool;", rep_desc_text)


if __name__ == "__main__":
    unittest.main()

