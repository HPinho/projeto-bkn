#!/usr/bin/env python3
"""Guardrails HID-4d.6: hotplug/reconnect de runtime sem novo Event Ring consumer."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOTPLUG = ROOT / "kernel/src/platform/hid_hotplug.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_hid_dual.yml"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", match.end())
    if brace < 0:
        raise AssertionError(f"missing body {name}")
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
    raise AssertionError(f"unterminated body {name}")


class XhciHidHotplugRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hotplug = HOTPLUG.read_text(encoding="utf-8")
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.progress = function_body(
            cls.hotplug, "platform_hid_hotplug_progress_detach_for"
        )
        cls.reconnect = function_body(
            cls.hotplug, "platform_hid_hotplug_record_reconnect"
        )
        cls.service = function_body(
            cls.hotplug, "platform_hid_hotplug_service_once"
        )
        cls.runtime_run = function_body(cls.runtime, "baken_native_runtime_run")

    def test_hotplug_uses_only_certified_owner_apis(self):
        required = (
            "xhci_hid_lifecycle_stop_endpoint_for",
            "xhci_hid_lifecycle_begin_logical_teardown_for",
            "xhci_hid_lifecycle_complete_logical_teardown_for",
            "xhci_hid_teardown_endpoint_for",
            "xhci_slot_teardown_release_enumeration_dma_for",
            "xhci_slot_teardown_quiesce_logical_state_for",
            "xhci_slot_teardown_disable_and_release_context_for",
            "xhci_slot_reuse_finalize_for",
            "xhci_hid_enumerate_next_connected",
        )
        for token in required:
            self.assertIn(token, self.hotplug)

    def test_progress_is_stage_aware_from_latest_proof_backwards(self):
        physical = self.progress.index("xhci_slot_teardown_physical_complete_for")
        reuse = self.progress.index("xhci_slot_reuse_finalize_for", physical)
        logical_state = self.progress.index(
            "xhci_slot_teardown_logical_state_complete_for", reuse
        )
        physical_teardown = self.progress.index(
            "xhci_slot_teardown_disable_and_release_context_for", logical_state
        )
        enum_dma = self.progress.index(
            "xhci_slot_teardown_enumeration_dma_complete_for", physical_teardown
        )
        logical_quiesce = self.progress.index(
            "xhci_slot_teardown_quiesce_logical_state_for", enum_dma
        )
        endpoint = self.progress.index(
            "xhci_hid_teardown_endpoint_complete_for", logical_quiesce
        )
        enum_release = self.progress.index(
            "xhci_slot_teardown_release_enumeration_dma_for", endpoint
        )
        logical_complete = self.progress.index(
            "xhci_hid_lifecycle_logical_teardown_complete_for", enum_release
        )
        endpoint_teardown = self.progress.index(
            "xhci_hid_teardown_endpoint_for", logical_complete
        )
        logical_started = self.progress.index(
            "xhci_hid_lifecycle_logical_teardown_started_for", endpoint_teardown
        )
        logical_finish = self.progress.index(
            "xhci_hid_lifecycle_complete_logical_teardown_for", logical_started
        )
        endpoint_stopped = self.progress.index(
            "xhci_hid_lifecycle_endpoint_stopped_for", logical_finish
        )
        logical_begin = self.progress.index(
            "xhci_hid_lifecycle_begin_logical_teardown_for", endpoint_stopped
        )
        stop = self.progress.index("xhci_hid_lifecycle_stop_endpoint_for", logical_begin)
        self.assertLess(physical, reuse)
        self.assertLess(reuse, logical_state)
        self.assertLess(logical_state, physical_teardown)
        self.assertLess(physical_teardown, enum_dma)
        self.assertLess(enum_dma, logical_quiesce)
        self.assertLess(logical_quiesce, endpoint)
        self.assertLess(endpoint, enum_release)
        self.assertLess(enum_release, logical_complete)
        self.assertLess(logical_complete, endpoint_teardown)
        self.assertLess(endpoint_teardown, logical_started)
        self.assertLess(logical_started, logical_finish)
        self.assertLess(logical_finish, endpoint_stopped)
        self.assertLess(endpoint_stopped, logical_begin)
        self.assertLess(logical_begin, stop)

    def test_reuse_is_final_barrier_before_registry_disappears(self):
        self.assertIn("xhci_slot_teardown_physical_complete_for(slot_id, epoch)", self.progress)
        self.assertIn("xhci_slot_reuse_finalize_for(slot_id, epoch)", self.progress)
        self.assertIn("xhci_slot_reuse_complete_for(slot_id, epoch)", self.progress)
        self.assertIn("xhci_device_table_slot_is_valid(slot_id)", self.progress)
        self.assertIn("PLATFORM_HID_HOTPLUG_LAST_DETACHED_EPOCH = epoch", self.progress)

    def test_service_finishes_pending_epoch_before_new_enumeration(self):
        scan = self.service.index("xhci_hid_lifecycle_scan_detached()")
        pending = self.service.index("XHCI_DEVICE_STATE_DETACH_PENDING", scan)
        progress = self.service.index("platform_hid_hotplug_progress_detach_for", pending)
        enumerate_new = self.service.index("xhci_hid_enumerate_next_connected(0)", progress)
        self.assertLess(scan, pending)
        self.assertLess(pending, progress)
        self.assertLess(progress, enumerate_new)
        self.assertIn("return platform_hid_hotplug_progress_detach_for", self.service)

    def test_same_slot_reconnect_requires_new_epoch(self):
        self.assertIn("PLATFORM_HID_HOTPLUG_LAST_DETACHED_SLOT == slot_id", self.reconnect)
        self.assertIn("epoch <= PLATFORM_HID_HOTPLUG_LAST_DETACHED_EPOCH", self.reconnect)
        self.assertIn("XHCI_DEVICE_STATE_HID_READY", self.reconnect)
        self.assertIn("xhci_hid_enumeration_is_ready_for(slot_id)", self.reconnect)

    def test_runtime_loop_services_hotplug_opportunistically(self):
        self.assertIn("import kernel::platform::hid_hotplug::*;", self.runtime)
        self.assertIn("platform_hid_hotplug_service_once();", self.runtime_run)
        self.assertNotIn("if !platform_hid_hotplug_service_once()", self.runtime_run)

    def test_hotplug_adds_no_second_event_consumer_command_or_dma_owner(self):
        forbidden = (
            "xhci_event_consumer",
            "xhci_transfer_route_next_event",
            "ERDP",
            "erdp",
            "xhci_command_",
            "xhci_trb_",
            "dma_release",
            "dma_unshare_from_device",
            "import kernel::memory::dma::*;",
        )
        for token in forbidden:
            self.assertNotIn(token, self.hotplug)

    def test_runtime_markers_cover_service_detach_and_reconnect(self):
        for marker in (
            "BAKEN:USB_HID_HOTPLUG_RUNTIME_READY",
            "BAKEN:USB_HID_HOTPLUG_DETACH_READY",
            "BAKEN:USB_HID_HOTPLUG_RECONNECT_READY",
        ):
            self.assertIn(marker, self.hotplug)

    def test_hid_workflow_performs_real_qemu_device_del_add_stress(self):
        self.assertIn("id=mouse0", self.workflow)
        self.assertIn("device_del mouse0", self.workflow)
        self.assertIn("device_add usb-mouse,bus=xhci.0,id=mouse1", self.workflow)
        self.assertIn("device_del mouse1", self.workflow)
        self.assertIn("device_add usb-mouse,bus=xhci.0,id=mouse2", self.workflow)
        self.assertIn("BAKEN:USB_HID_HOTPLUG_RUNTIME_READY", self.workflow)
        self.assertIn("BAKEN:USB_HID_HOTPLUG_DETACH_READY", self.workflow)
        self.assertIn("BAKEN:USB_HID_HOTPLUG_RECONNECT_READY", self.workflow)


if __name__ == "__main__":
    unittest.main()
