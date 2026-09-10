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

    def test_identity_precedes_per_device_map_event_model_and_bind(self):
        text = XHCI.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_descriptor_probe_internal() -> bool", 1)[1]
        body = body.split("pub fn xhci_hid_descriptor_emit_ready_marker()", 1)[0]
        registry = body.index("input_device_registry_init()")
        attach = body.index("xhci_hid_attach_input_device(protocol, interface_number)")
        build = body.index("hid_input_device_map_build(device_id, generation")
        legacy_marker = body.index("xhci_hid_input_map_emit_ready_marker()")
        device_map_marker = body.index("xhci_hid_device_map_emit_ready_marker()")
        event_init = body.index("hid_input_events_initialize()")
        event_bind = body.index("xhci_hid_bind_input_events()")
        event_ready = body.index("xhci_hid_event_model_emit_ready_marker()")
        device_ready = body.index("xhci_hid_device_emit_ready_marker()")
        descriptor_store = body.index("XHCI_HID_DESCRIPTOR_BUFFER = buffer")
        self.assertLess(registry, attach)
        self.assertLess(attach, build)
        self.assertLess(build, legacy_marker)
        self.assertLess(legacy_marker, device_map_marker)
        self.assertLess(device_map_marker, event_init)
        self.assertLess(event_init, event_bind)
        self.assertLess(event_bind, event_ready)
        self.assertLess(event_ready, device_ready)
        self.assertLess(device_ready, descriptor_store)

    def test_hid4_binding_uses_generation_safe_registry_and_map(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::input_device::*;", text)
        self.assertIn("import kernel::drivers::hid_input_device_map::*;", text)
        self.assertIn("INPUT_TRANSPORT_USB", text)
        self.assertIn("input_device_attach(", text)
        self.assertIn("input_device_activate(handle.device_id, handle.generation)", text)
        self.assertIn("hid_input_device_map_build(device_id, generation", text)
        self.assertIn("hid_input_events_bind_device(device_id, generation)", text)
        self.assertIn("XHCI_HID_INPUT_DEVICE_ID", text)
        self.assertIn("XHCI_HID_INPUT_DEVICE_GENERATION", text)
        self.assertIn("pub fn xhci_hid_descriptor_input_map_is_ready()", text)
        self.assertIn("pub fn xhci_hid_descriptor_input_device_is_active()", text)

    def test_release_invalidates_then_purges_events_state_and_map(self):
        text = XHCI.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_descriptor_release_input_device() -> bool", 1)[1]
        body = body.split("fn xhci_hid_descriptor_reset", 1)[0]
        detach = body.index("input_device_detach(device_id, generation)")
        purge = body.index("input_event_purge_device(device_id, generation)")
        event_unbind = body.index("hid_input_events_unbind_device(device_id, generation)")
        map_unbind = body.index("hid_input_device_map_unbind(device_id, generation)")
        self.assertLess(detach, purge)
        self.assertLess(purge, event_unbind)
        self.assertLess(event_unbind, map_unbind)

    def test_device_and_per_device_map_markers_exist(self):
        text = XHCI.read_text(encoding="utf-8")
        self.assertIn("fn xhci_hid_device_map_emit_ready_marker()", text)
        self.assertIn("let marker: [u8; 31]", text)
        self.assertIn("fn xhci_hid_device_map_emit_failure_marker()", text)
        self.assertIn("let marker: [u8; 32]", text)
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

    def test_runtime_proof_keeps_hid1_hid2_and_requires_hid4b_map(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        smp = SMP.read_text(encoding="utf-8")
        yml = SMP_YML.read_text(encoding="utf-8")
        for marker in (
            '"USB_HID_DESCRIPTOR_READY"', '"USB_HID_INPUT_MAP_READY"',
            '"USB_HID_DEVICE_MAP_READY"', '"USB_HID_EVENT_MODEL_READY"',
            '"USB_HID_DEVICE_READY"',
        ):
            self.assertIn(marker, smoke)
        self.assertIn("BAKEN:USB_HID_DEVICE_MAP_FAILED", smoke)
        self.assertIn('"BAKEN:USB_HID_DEVICE_MAP_READY"', smp)
        self.assertIn("BAKEN:USB_HID_DEVICE_MAP_FAILED", smp)
        self.assertIn("require_marker 'BAKEN:USB_HID_DEVICE_MAP_READY'", yml)


if __name__ == "__main__":
    unittest.main()
