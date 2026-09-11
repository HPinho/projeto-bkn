from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "kernel/src/drivers/input_device.sotlas"
DEVICE_MAP = ROOT / "kernel/src/drivers/hid_input_device_map.sotlas"
EVENT = ROOT / "kernel/src/drivers/input_event.sotlas"
HID_EVENTS = ROOT / "kernel/src/drivers/hid_input_events.sotlas"
XHCI_DEVICE_TABLE = ROOT / "kernel/src/drivers/xhci_device_table.sotlas"
XHCI_HID_CONTEXT = ROOT / "kernel/src/drivers/xhci_hid_context.sotlas"
XHCI_CONFIGURE = ROOT / "kernel/src/drivers/xhci_configure_endpoint.sotlas"
XHCI_DESCRIPTOR = ROOT / "kernel/src/drivers/xhci_hid_descriptor.sotlas"
XHCI_REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"
SMP = ROOT / "tools/scripts/run_smp_qemu.py"
SMP_YML = ROOT / ".github/workflows/baken_smp.yml"


class Hid4RuntimeContractTests(unittest.TestCase):
    def test_lifecycle_layers_are_bounded_and_no_heap(self):
        for path in (DEVICE, DEVICE_MAP, EVENT, HID_EVENTS):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("kernel_heap", text)
            self.assertNotIn("alloc(", text)
        self.assertIn("INPUT_DEVICE_CAPACITY: usize = 16", DEVICE.read_text(encoding="utf-8"))
        self.assertIn("HID_DEVICE_MAP_CAPACITY: usize = INPUT_DEVICE_CAPACITY",
                      DEVICE_MAP.read_text(encoding="utf-8"))
        self.assertIn("INPUT_EVENT_QUEUE_CAPACITY: usize = 512", EVENT.read_text(encoding="utf-8"))

    def test_xhci_transport_is_identity_and_map_bound_per_slot(self):
        descriptor = XHCI_DESCRIPTOR.read_text(encoding="utf-8")
        report = XHCI_REPORT.read_text(encoding="utf-8")
        self.assertIn("input_device_attach(", descriptor)
        self.assertIn("INPUT_TRANSPORT_USB", descriptor)
        self.assertIn("hid_input_device_map_build(", descriptor)
        self.assertIn("xhci_hid_descriptor_input_device_is_active_for(slot_id)", report)
        self.assertIn("xhci_hid_descriptor_input_map_is_ready_for(slot_id)", report)
        self.assertIn("xhci_hid_descriptor_input_device_id_for(slot_id)", report)
        self.assertIn("xhci_hid_descriptor_input_device_generation_for(slot_id)", report)
        self.assertIn("xhci_hid_protocol_for(slot_id)", report)
        self.assertIn("hid_input_events_process_report_for_device(", report)
        self.assertIn("input_device_snapshot(device_id, generation)", report)
        self.assertIn("record.transport_address == slot_id as u32", report)

    def test_detach_order_blocks_publish_then_purges_state_and_map(self):
        text = XHCI_DESCRIPTOR.read_text(encoding="utf-8")
        body = text.split(
            "pub fn xhci_hid_descriptor_release_input_device_for_slot(slot_id: u8) -> bool", 1
        )[1]
        body = body.split("pub fn xhci_hid_descriptor_release_input_device()", 1)[0]
        detach = body.index("input_device_detach")
        purge = body.index("input_event_purge_device")
        event_unbind = body.index("hid_input_events_unbind_device")
        map_unbind = body.index("hid_input_device_map_unbind")
        self.assertLess(detach, purge)
        self.assertLess(purge, event_unbind)
        self.assertLess(event_unbind, map_unbind)

    def test_hid4c_transport_descriptor_and_report_binding_are_partitioned(self):
        table = XHCI_DEVICE_TABLE.read_text(encoding="utf-8")
        context = XHCI_HID_CONTEXT.read_text(encoding="utf-8")
        configure = XHCI_CONFIGURE.read_text(encoding="utf-8")
        descriptor = XHCI_DESCRIPTOR.read_text(encoding="utf-8")
        report = XHCI_REPORT.read_text(encoding="utf-8")

        self.assertIn("XHCI_DEVICE_SLOTS", table)
        self.assertIn("XHCI_HID_CONTEXTS", context)
        self.assertIn("XHCI_CONFIGURE_ENDPOINT_READY_SLOTS", configure)
        self.assertIn("XHCI_HID_DESCRIPTOR_STATES", descriptor)
        self.assertIn("XHCI_HID_REPORT_STATES", report)
        self.assertIn("xhci_device_table_slot_epoch(slot_id)", descriptor)
        self.assertIn("xhci_hid_context_ring_physical_for(slot_id)", report)
        self.assertNotIn("static mut XHCI_HID_CONTEXT_RING:", context)
        self.assertNotIn("static mut XHCI_HID_DESCRIPTOR_READY:", descriptor)
        self.assertNotIn("static mut XHCI_HID_INPUT_DEVICE_ID:", descriptor)
        self.assertNotIn("static mut XHCI_HID_DESCRIPTOR_BUFFER:", descriptor)
        self.assertNotIn("static mut XHCI_HID_REPORT_BUFFER:", report)

        # HID-4c.3: o report runtime deve consumir descriptor/binding e resultado
        # de transferência exclusivamente pelo mesmo slot.
        self.assertIn("xhci_hid_descriptor_input_device_id_for(slot_id)", report)
        self.assertIn("xhci_transfer_last_residual_length_for(slot_id)", report)
        self.assertNotIn("xhci_hid_descriptor_input_device_id()", report)
        self.assertNotIn("xhci_hid_descriptor_input_device_generation()", report)
        self.assertNotIn("xhci_hid_descriptor_input_device_is_active()", report)
        self.assertNotIn("xhci_hid_descriptor_input_map_is_ready()", report)
        self.assertNotIn("xhci_hid_protocol()", report)
        self.assertNotIn("MULTI_DEVICE_READY", descriptor)
        self.assertNotIn("MULTI_DEVICE_READY", report)

    def test_all_runtime_gates_require_identity_and_per_device_map_markers(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        smp = SMP.read_text(encoding="utf-8")
        yml = SMP_YML.read_text(encoding="utf-8")
        self.assertIn('"USB_HID_DEVICE_MAP_READY"', smoke)
        self.assertIn("BAKEN:USB_HID_DEVICE_MAP_FAILED", smoke)
        self.assertIn('"USB_HID_DEVICE_READY"', smoke)
        self.assertIn("BAKEN:USB_HID_DEVICE_FAILED", smoke)
        self.assertIn('"BAKEN:USB_HID_DEVICE_MAP_READY"', smp)
        self.assertIn("BAKEN:USB_HID_DEVICE_MAP_FAILED", smp)
        self.assertIn("require_marker 'BAKEN:USB_HID_DEVICE_MAP_READY'", yml)
        self.assertIn("require_marker 'BAKEN:USB_HID_DEVICE_READY'", yml)
        self.assertIn("python3 tests/test_hid_input_device_map.py", yml)
        self.assertIn("python3 tests/test_hid4_runtime_contract.py", yml)


if __name__ == "__main__":
    unittest.main()
