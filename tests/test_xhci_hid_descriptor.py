from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
XHCI = ROOT / "kernel/src/drivers/xhci_hid_descriptor.sotlas"
SETCFG = ROOT / "kernel/src/drivers/xhci_set_configuration.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"
SMP = ROOT / "tools/scripts/run_smp_qemu.py"
SMP_YML = ROOT / ".github/workflows/baken_smp.yml"


class XhciHidDescriptorTests(unittest.TestCase):
    def test_report_descriptor_uses_standard_interface_request(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("USB_REQUEST_TYPE_DEVICE_TO_HOST_STANDARD_INTERFACE: u8 = 0x81", text)
        self.assertIn("USB_HID_REPORT_DESCRIPTOR_VALUE: u16 = 0x2200", text)
        self.assertIn("USB_REQUEST_GET_DESCRIPTOR", text)
        self.assertIn("interface_number as u16", text)
        self.assertIn("XHCI_SETUP_TRT_IN_DATA", text)
        self.assertIn("xhci_transfer_wait_ep0_completion", text)

    def test_descriptor_length_comes_from_hid_descriptor(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("let length = xhci_hid_report_descriptor_length()", text)
        self.assertIn("length == 0", text)
        self.assertIn("length as usize", text)
        self.assertIn("hid_report_descriptor_parse", text)
        self.assertNotIn("XHCI_HID_BOOT_KEYBOARD_LENGTH", text)

    def test_boot_protocol_is_only_consistency_check(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("protocol == USB_HID_PROTOCOL_KEYBOARD && !info.has_keyboard_application", text)
        self.assertIn("protocol == USB_HID_PROTOCOL_MOUSE && !info.has_mouse_application", text)
        self.assertIn("if !info.has_report_ids", text)
        self.assertIn("input_bytes > xhci_hid_endpoint_max_packet()", text)

    def test_set_configuration_proves_descriptor_before_ready(self):
        text = SETCFG.read_text(encoding="utf-8")
        descriptor = text.index("xhci_hid_descriptor_initialize()")
        ready = text.index("XHCI_SET_CONFIGURATION_READY = true")
        self.assertLess(descriptor, ready)
        self.assertIn("import kernel::drivers::xhci_hid_descriptor::*;", text)

    def test_graph_registers_generic_and_transport_modules(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::hid_report_descriptor::*;", text)
        self.assertIn("import kernel::drivers::xhci_hid_descriptor::*;", text)

    def test_runtime_proof_is_required_by_all_smoke_contracts(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        smp = SMP.read_text(encoding="utf-8")
        yml = SMP_YML.read_text(encoding="utf-8")
        self.assertIn('"USB_HID_DESCRIPTOR_READY"', smoke)
        self.assertIn("BAKEN:USB_HID_DESCRIPTOR_FAILED", smoke)
        self.assertIn('"BAKEN:USB_HID_DESCRIPTOR_READY"', smp)
        self.assertIn("BAKEN:USB_HID_DESCRIPTOR_FAILED", smp)
        self.assertIn("require_marker 'BAKEN:USB_HID_DESCRIPTOR_READY'", yml)


if __name__ == "__main__":
    unittest.main()
