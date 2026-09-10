from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID = ROOT / "kernel/src/drivers/hid_report_descriptor.sotlas"


class HidReportDescriptorTests(unittest.TestCase):
    def test_parser_is_transport_independent_and_bounded(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("module kernel::drivers::hid_report_descriptor", text)
        self.assertIn("HID_REPORT_DESCRIPTOR_MAX_BYTES: usize = 4096", text)
        self.assertIn("HID_REPORT_DESCRIPTOR_MAX_ITEMS: u32 = 512", text)
        self.assertIn("HID_REPORT_MAX_COLLECTION_DEPTH: u16 = 16", text)
        self.assertNotIn("xhci_", text)
        self.assertNotIn("dma_", text)

    def test_parser_decodes_short_item_header_without_blind_scan(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("let item_type = (prefix >> 2) & 0x03", text)
        self.assertIn("let tag = (prefix >> 4) & 0x0F", text)
        self.assertIn("hid_report_item_size(prefix)", text)
        self.assertIn("if prefix == HID_ITEM_LONG_PREFIX { return result; }", text)
        self.assertIn("if size > length - offset { return result; }", text)

    def test_report_geometry_is_overflow_bounded(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("HID_REPORT_MAX_REPORT_SIZE_BITS: u32 = 64", text)
        self.assertIn("HID_REPORT_MAX_REPORT_COUNT: u32 = 256", text)
        self.assertIn("HID_REPORT_MAX_AGGREGATE_BITS: u32 = 32768", text)
        self.assertIn("count > (HID_REPORT_MAX_AGGREGATE_BITS / size)", text)
        self.assertIn("current > HID_REPORT_MAX_AGGREGATE_BITS - bits", text)

    def test_application_usage_and_report_ids_are_explicit(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("HID_USAGE_PAGE_GENERIC_DESKTOP", text)
        self.assertIn("HID_USAGE_KEYBOARD", text)
        self.assertIn("HID_USAGE_MOUSE", text)
        self.assertIn("has_report_ids = true", text)
        self.assertIn("has_keyboard_application", text)
        self.assertIn("has_mouse_application", text)

    def test_unsupported_global_stack_fails_closed(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("tag == HID_GLOBAL_PUSH || tag == HID_GLOBAL_POP", text)
        self.assertIn("return result;", text)

    def test_self_test_uses_realistic_boot_keyboard_descriptor(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("let keyboard: [u8; 63]", text)
        self.assertIn("parsed.input_bits != 64", text)
        self.assertIn("parsed.output_bits != 8", text)
        self.assertIn("hid_report_descriptor_input_bytes(parsed) != 8", text)
        self.assertIn("let truncated: [u8; 2]", text)
        self.assertIn("let long_item: [u8; 3]", text)


if __name__ == "__main__":
    unittest.main()
