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
        self.assertIn("hid_report_descriptor_parse", text)
        self.assertNotIn("XHCI_HID_BOOT_KEYBOARD_LENGTH", text)

    def test_boot_protocol_is_only_consistency_check(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("protocol == USB_HID_PROTOCOL_KEYBOARD && !info.has_keyboard_application", text)
        self.assertIn("protocol == USB_HID_PROTOCOL_MOUSE && !info.has_mouse_application", text)
        self.assertIn("if !info.has_report_ids", text)
        self.assertIn("input_bytes > xhci_hid_endpoint_max_packet()", text)

    def test_hid2_map_precedes_event_model_and_device_binding(self):
        text = XHCI.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_descriptor_probe_internal() -> bool", 1)[1]
        body = body.split("pub fn xhci_hid_descriptor_emit_ready_marker()", 1)[0]
        build = body.index("hid_input_report_map_build(buffer.virtual_address as *const u8, length as usize)")
        map_ready = body.index("xhci_hid_input_map_emit_ready_marker()")
        registry = body.index("input_device_registry_init()")
        event_init = body.index("hid_input_events_initialize()")
        event_ready = body.index("xhci_hid_event_model_emit_ready_marker()")
        device_bind = body.index("xhci_hid_bind_input_device(protocol, interface_number)")
        device_ready = body.index("xhci_hid_device_emit_ready_marker()")
        descriptor_store = body.index("XHCI_HID_DESCRIPTOR_BUFFER = buffer")
        self.assertLess(build, map_ready)
        self.assertLess(map_ready, registry)
        self.assertLess(registry, event_init)
        self.assertLess(event_init, event_ready)
        self.assertLess(event_ready, device_bind)
        self.assertLess(device_bind, device_ready)
        self.assertLess(device_ready, descriptor_store)

    def test_hid4_binding_uses_generation_safe_generic_registry(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::input_device::*;", text)
        self.assertIn("INPUT_TRANSPORT_USB", text)
        self.assertIn("input_device_attach(", text)
        self.assertIn("input_device_activate(handle.device_id, handle.generation)", text)
        self.assertIn("hid_input_events_bind_device(handle.device_id, handle.generation)", text)
        self.assertIn("XHCI_HID_INPUT_DEVICE_ID", text)
        self.assertIn("XHCI_HID_INPUT_DEVICE_GENERATION", text)
        self.assertIn("pub fn xhci_hid_descriptor_input_device_is_active()", text)

    def test_release_invalidates_then_purges_then_unbinds(self):
        text = XHCI.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_descriptor_release_input_device() -> bool", 1)[1]
        body = body.split("fn xhci_hid_descriptor_reset", 1)[0]
        detach = body.index("input_device_detach(device_id, generation)")
        purge = body.index("input_event_purge_device(device_id, generation)")
        unbind = body.index("hid_input_events_unbind_device(device_id, generation)")
        self.assertLess(detach, purge)
        self.assertLess(purge, unbind)

    def test_device_ready_and_failure_markers_exist(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("fn xhci_hid_device_emit_ready_marker()", text)
        self.assertIn("let marker: [u8; 27]", text)
        self.assertIn("fn xhci_hid_device_emit_failure_marker()", text)
        self.assertIn("let marker: [u8; 28]", text)

    def test_set_configuration_proves_descriptor_before_ready(self):
        text = SETCFG.read_text(encoding="utf-8")
        descriptor = text.index("xhci_hid_descriptor_initialize()")
        ready = text.index("XHCI_SET_CONFIGURATION_READY = true")
        self.assertLess(descriptor, ready)
        self.assertIn("import kernel::drivers::xhci_hid_descriptor::*;", text)

    def test_graph_registers_generic_and_transport_modules(self):
        text = MAIN.read_text(encoding="utf-8")
        for token in (
            "import kernel::drivers::hid_report_descriptor::*;",
            "import kernel::drivers::hid_input_report::*;",
            "import kernel::drivers::input_device::*;",
            "import kernel::drivers::input_event::*;",
            "import kernel::drivers::hid_input_events::*;",
            "import kernel::drivers::xhci_hid_descriptor::*;",
        ):
            self.assertIn(token, text)

    def test_runtime_proof_keeps_hid1_hid2_and_adds_hid4_identity(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        smp = SMP.read_text(encoding="utf-8")
        yml = SMP_YML.read_text(encoding="utf-8")
        for marker in (
            '"USB_HID_DESCRIPTOR_READY"', '"USB_HID_INPUT_MAP_READY"',
            '"USB_HID_EVENT_MODEL_READY"', '"USB_HID_DEVICE_READY"',
        ):
            self.assertIn(marker, smoke)
        self.assertIn("BAKEN:USB_HID_DEVICE_FAILED", smoke)
        self.assertIn('"BAKEN:USB_HID_DEVICE_READY"', smp)
        self.assertIn("BAKEN:USB_HID_DEVICE_FAILED", smp)
        self.assertIn("require_marker 'BAKEN:USB_HID_DEVICE_READY'", yml)


if __name__ == "__main__":
    unittest.main()
