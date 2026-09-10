from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEVICE_MAP = ROOT / "kernel/src/drivers/hid_input_device_map.sotlas"
LEGACY_MAP = ROOT / "kernel/src/drivers/hid_input_report.sotlas"
HID_EVENTS = ROOT / "kernel/src/drivers/hid_input_events.sotlas"
XHCI_DESCRIPTOR = ROOT / "kernel/src/drivers/xhci_hid_descriptor.sotlas"
XHCI_REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"
SMP = ROOT / "tools/scripts/run_smp_qemu.py"
SMP_YML = ROOT / ".github/workflows/baken_smp.yml"


class HidInputDeviceMapTests(unittest.TestCase):
    def test_per_device_map_is_fixed_capacity_and_transport_agnostic(self):
        text = DEVICE_MAP.read_text(encoding="utf-8")
        self.assertIn("HID_DEVICE_MAP_CAPACITY: usize = INPUT_DEVICE_CAPACITY", text)
        self.assertIn("HID_DEVICE_MAP_TOTAL_FIELDS", text)
        self.assertIn("HID_DEVICE_MAP_GENERATIONS", text)
        self.assertIn("HID_DEVICE_MAP_READY_SLOTS", text)
        for forbidden in ("xhci_", "dma_", "pci_", "acpi_", "kernel_heap", "alloc("):
            self.assertNotIn(forbidden, text)

    def test_builder_uses_legacy_map_only_as_serialized_scratch(self):
        text = DEVICE_MAP.read_text(encoding="utf-8")
        self.assertIn("static mut HID_DEVICE_MAP_BUILD_LOCK: SpinLock", text)
        body = text.split("pub fn hid_input_device_map_build", 1)[1]
        body = body.split("pub fn hid_input_device_map_unbind", 1)[0]
        self.assertIn("spinlock_lock(&mut HID_DEVICE_MAP_BUILD_LOCK)", body)
        self.assertIn("hid_input_report_map_build(descriptor, length)", body)
        self.assertIn("HID_DEVICE_MAP_FIELDS", body)
        self.assertIn("hid_input_device_map_reset_scratch()", body)
        self.assertNotIn("hid_input_report_decode_field", body)
        self.assertIn("hid_input_report_map_build(null as *const u8, 0)", text)
        self.assertIn("static mut HID_INPUT_FIELDS", LEGACY_MAP.read_text(encoding="utf-8"))

    def test_runtime_api_requires_device_id_and_generation(self):
        text = DEVICE_MAP.read_text(encoding="utf-8")
        for token in (
            "pub fn hid_input_device_map_is_ready(device_id: u32, generation: u32)",
            "pub fn hid_input_device_map_field_count(device_id: u32, generation: u32)",
            "pub fn hid_input_device_map_has_report_ids(device_id: u32, generation: u32)",
            "pub fn hid_input_device_map_expected_bytes(device_id: u32",
            "pub fn hid_input_device_map_decode_field(device_id: u32",
            "pub fn hid_input_device_map_validate(device_id: u32",
            "pub fn hid_input_device_map_unbind(device_id: u32, generation: u32)",
        ):
            self.assertIn(token, text)

    def test_self_test_proves_two_simultaneous_maps_and_isolation(self):
        text = DEVICE_MAP.read_text(encoding="utf-8")
        body = text.split("pub fn hid_input_device_map_self_test()", 1)[1]
        self.assertIn("hid_input_device_map_build(1, 11", body)
        self.assertIn("hid_input_device_map_build(2, 7", body)
        self.assertIn("hid_input_device_map_field_count(1, 11) != 15", body)
        self.assertIn("hid_input_device_map_field_count(2, 7) != 7", body)
        self.assertIn("hid_input_device_map_validate(2, 7, &keyboard_report[0], 8)", body)
        self.assertIn("hid_input_device_map_validate(1, 11, &mouse_report[0], 4)", body)
        self.assertIn("hid_input_device_map_unbind(1, 11)", body)
        self.assertIn("hid_input_device_map_is_ready(2, 7)", body)

    def test_runtime_consumers_do_not_use_singleton_map(self):
        events = HID_EVENTS.read_text(encoding="utf-8")
        report = XHCI_REPORT.read_text(encoding="utf-8")
        descriptor = XHCI_DESCRIPTOR.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::hid_input_device_map::*;", events)
        self.assertIn("hid_input_device_map_validate(device_id, device_generation", events)
        self.assertIn("hid_input_device_map_field_count(device_id, device_generation)", events)
        self.assertIn("hid_input_device_map_decode_field(", events)
        self.assertNotIn("hid_input_report_validate(", events)
        self.assertNotIn("hid_input_report_field_count()", events)
        self.assertNotIn("hid_input_report_decode_field(", events)
        self.assertIn("hid_input_device_map_validate(", report)
        self.assertIn("hid_input_device_map_has_report_ids(device_id, device_generation)", report)
        self.assertNotIn("hid_input_report_validate(", report)
        self.assertIn("hid_input_device_map_build(device_id, generation", descriptor)
        self.assertNotIn("hid_input_report_map_build(buffer.virtual_address", descriptor)

    def test_xhci_identity_precedes_per_device_map_and_event_bind(self):
        text = XHCI_DESCRIPTOR.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_descriptor_probe_internal() -> bool", 1)[1]
        body = body.split("pub fn xhci_hid_descriptor_emit_ready_marker()", 1)[0]
        attach = body.index("xhci_hid_attach_input_device(protocol, interface_number)")
        build = body.index("hid_input_device_map_build(device_id, generation")
        map_marker = body.index("xhci_hid_device_map_emit_ready_marker()")
        event_init = body.index("hid_input_events_initialize()")
        event_bind = body.index("xhci_hid_bind_input_events()")
        device_ready = body.index("xhci_hid_device_emit_ready_marker()")
        self.assertLess(attach, build)
        self.assertLess(build, map_marker)
        self.assertLess(map_marker, event_init)
        self.assertLess(event_init, event_bind)
        self.assertLess(event_bind, device_ready)

    def test_runtime_gates_require_per_device_map_marker(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        smp = SMP.read_text(encoding="utf-8")
        yml = SMP_YML.read_text(encoding="utf-8")
        self.assertIn('"USB_HID_DEVICE_MAP_READY"', smoke)
        self.assertIn("BAKEN:USB_HID_DEVICE_MAP_FAILED", smoke)
        self.assertIn('"BAKEN:USB_HID_DEVICE_MAP_READY"', smp)
        self.assertIn("BAKEN:USB_HID_DEVICE_MAP_FAILED", smp)
        self.assertIn("require_marker 'BAKEN:USB_HID_DEVICE_MAP_READY'", yml)
        self.assertIn("python3 tests/test_hid_input_device_map.py", yml)


if __name__ == "__main__":
    unittest.main()
