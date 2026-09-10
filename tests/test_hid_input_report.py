from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID = ROOT / "kernel/src/drivers/hid_input_report.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class HidInputReportTests(unittest.TestCase):
    def test_field_map_is_transport_independent_and_fixed_capacity(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("module kernel::drivers::hid_input_report", text)
        self.assertIn("HID_INPUT_MAX_FIELDS: usize = 512", text)
        self.assertIn("HID_INPUT_REPORT_ID_SLOTS: usize = 256", text)
        self.assertIn("HID_INPUT_MAX_LOCAL_USAGES: usize = 256", text)
        self.assertNotIn("xhci_", text)
        self.assertNotIn("dma_", text)
        self.assertNotIn("heap", text.lower())

    def test_map_tracks_report_id_usage_offsets_and_main_flags(self):
        text = HID.read_text(encoding="utf-8")
        for token in (
            "pub report_id: u8", "pub bit_offset: u32", "pub bit_size: u32",
            "pub usage_page: u32", "pub usage: u32", "pub flags: u32",
            "HID_INPUT_FLAG_CONSTANT", "HID_INPUT_FLAG_VARIABLE",
            "HID_INPUT_FLAG_RELATIVE", "HID_INPUT_FLAG_NULL_STATE",
        ):
            self.assertIn(token, text)
        self.assertIn("HID_LOCAL_USAGE_MINIMUM", text)
        self.assertIn("HID_LOCAL_USAGE_MAXIMUM", text)
        self.assertIn("if !report_ids_enabled && data_main_seen", text)

    def test_report_id_is_wire_prefix_not_payload_bit_offset(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("if HID_INPUT_HAS_REPORT_IDS { bytes += 1; }", text)
        self.assertIn("payload = unsafe { ((report as usize) + 1) as *const u8 }", text)
        self.assertIn("payload_length -= 1", text)
        self.assertIn("if field.report_id != report_id", text)

    def test_decoder_is_bounds_checked_and_lsb_first(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("end_bit > (length as u64) * 8", text)
        self.assertIn("let absolute = bit_offset + bit", text)
        self.assertIn("let value = (byte >> ((absolute % 8) as u8)) & 1", text)
        self.assertIn("result |= (value as u64) << bit", text)
        self.assertIn("length != expected as usize", text)

    def test_signed_values_and_null_state_are_explicit(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("fn hid_input_sign_extend", text)
        self.assertIn("field.logical_min < 0", text)
        self.assertIn("if !field.null_state { return result; }", text)
        self.assertIn("result.null_value = null_value", text)

    def test_array_usage_resolution_never_invents_noncontiguous_range(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("hid_input_local_list_contiguous", text)
        self.assertIn("field.array_usage_valid = true", text)
        self.assertIn("selector <= span", text)
        self.assertNotIn("selector %", text)

    def test_self_test_covers_keyboard_mouse_report_id_and_truncation(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("let keyboard: [u8; 63]", text)
        self.assertIn("let keyboard_report: [u8; 8]", text)
        self.assertIn("let mouse: [u8; 52]", text)
        self.assertIn("x.numeric_value != -1", text)
        self.assertIn("let report_id_ok: [u8; 21]", text)
        self.assertIn("id_value.numeric_value != -2", text)
        self.assertIn("hid_input_report_validate(&keyboard_report[0], 7)", text)

    def test_main_registers_hid_input_decoder(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::hid_input_report::*;", text)


if __name__ == "__main__":
    unittest.main()
