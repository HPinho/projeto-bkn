from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / "kernel/src/drivers/input_device.sotlas"
EVENT = ROOT / "kernel/src/drivers/input_event.sotlas"
HID_EVENTS = ROOT / "kernel/src/drivers/hid_input_events.sotlas"
XHCI_DESCRIPTOR = ROOT / "kernel/src/drivers/xhci_hid_descriptor.sotlas"
XHCI_REPORT = ROOT / "kernel/src/drivers/xhci_hid_report.sotlas"
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"
SMP = ROOT / "tools/scripts/run_smp_qemu.py"
SMP_YML = ROOT / ".github/workflows/baken_smp.yml"


class Hid4RuntimeContractTests(unittest.TestCase):
    def test_lifecycle_layers_are_bounded_and_no_heap(self):
        for path in (DEVICE, EVENT, HID_EVENTS):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("kernel_heap", text)
            self.assertNotIn("alloc(", text)
        self.assertIn("INPUT_DEVICE_CAPACITY: usize = 16", DEVICE.read_text(encoding="utf-8"))
        self.assertIn("INPUT_EVENT_QUEUE_CAPACITY: usize = 512", EVENT.read_text(encoding="utf-8"))

    def test_xhci_current_transport_is_explicitly_identity_bound(self):
        descriptor = XHCI_DESCRIPTOR.read_text(encoding="utf-8")
        report = XHCI_REPORT.read_text(encoding="utf-8")
        self.assertIn("input_device_attach(", descriptor)
        self.assertIn("INPUT_TRANSPORT_USB", descriptor)
        self.assertIn("xhci_hid_descriptor_input_device_is_active()", report)
        self.assertIn("hid_input_events_process_report_for_device(", report)

    def test_detach_order_blocks_publish_then_purges_then_clears_hid_state(self):
        text = XHCI_DESCRIPTOR.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_hid_descriptor_release_input_device() -> bool", 1)[1]
        body = body.split("fn xhci_hid_descriptor_reset", 1)[0]
        detach = body.index("input_device_detach")
        purge = body.index("input_event_purge_device")
        unbind = body.index("hid_input_events_unbind_device")
        self.assertLess(detach, purge)
        self.assertLess(purge, unbind)

    def test_hid4_does_not_claim_multidevice_xhci_before_singletons_are_migrated(self):
        descriptor = XHCI_DESCRIPTOR.read_text(encoding="utf-8")
        self.assertIn("transport_instance=0 significa o primeiro xHC ainda singleton", descriptor)
        self.assertNotIn("MULTI_DEVICE_READY", descriptor)

    def test_all_runtime_gates_require_device_identity_marker(self):
        smoke = SMOKE.read_text(encoding="utf-8")
        smp = SMP.read_text(encoding="utf-8")
        yml = SMP_YML.read_text(encoding="utf-8")
        self.assertIn('"USB_HID_DEVICE_READY"', smoke)
        self.assertIn("BAKEN:USB_HID_DEVICE_FAILED", smoke)
        self.assertIn('"BAKEN:USB_HID_DEVICE_READY"', smp)
        self.assertIn("BAKEN:USB_HID_DEVICE_FAILED", smp)
        self.assertIn("require_marker 'BAKEN:USB_HID_DEVICE_READY'", yml)
        self.assertIn("python3 tests/test_hid4_runtime_contract.py", yml)


if __name__ == "__main__":
    unittest.main()
