# Baken OS — I2C Roadmap Appendix XIII

## I2C-HID hardening after real-hardware audit

This appendix is append-only. Earlier I2C roadmap appendices remain historical and are not rewritten.

### Stage I2C-HID-6 — protocol/lifecycle hardening

Implementation status: **code complete; CI certification pending at commit publication**.

Completed in this stage:

- GET_REPORT now emits one combined I2C write phase containing Command Register, encoded HID command, optional extended Report ID and Data Register, followed by the repeated-start read.
- SET_REPORT now emits one write transaction containing Command Register, command, optional extended Report ID, Data Register, LE16 report length, numbered-report ID when required, and payload.
- Extended Report IDs use the HID-over-I2C order `type|0x0F`, opcode, Report ID.
- Input runtime slots are no longer confused with ACPI discovery slots. `input_device_index` is stored explicitly by the manager.
- I2C-HID input registration is removable and bounded; failed initialization can return the slot to the fixed-capacity table.
- `wMaxInputLength` values larger than the certified fixed input buffer fail closed instead of being silently truncated.
- GPIO pin zero is treated as an ordinary pin value, not as a wildcard broadcast to all HID devices.
- RESET completion requires a pending GPIO interrupt before reading the 2-byte reset acknowledgement; the acknowledged `wLength` must be zero.
- Every post-attach failure rolls back the HID input slot, HID event binding, HID device map, generic input device, GPIO connection and I2C device generation-safely.
- A logical ACPI `GpioInt` connection is no longer enough to claim a working interrupt. `gpio_core` now requires an explicitly registered physical backend owning the resolved GPIO controller namespace.
- Physical GPIO backend unregister refuses removal while live logical connections still reference that controller namespace.

### Certification invariants

The following regressions are now explicitly blocked by tests:

1. GET_REPORT must not split command and Data Register into independent transfers.
2. SET_REPORT must not split command framing from report data.
3. Extended Report ID must follow the opcode.
4. ACPI `device_slot` must not be used as the runtime I2C-HID input index.
5. Input lengths above the fixed certified buffer must not be clamped/truncated.
6. GPIO pin zero must not broadcast IRQ notification.
7. RESET polling must not read until the registered GPIO connection reports a pending interrupt.
8. ACPI-only GPIO ownership must fail closed when no physical backend has registered that controller.
9. Initialization failure must not leak I2C, GPIO, HID-map, HID-event or generic-input lifecycle state.

### Foundation boundary after this stage

I2C controller transport and HID-over-I2C protocol/lifecycle code are now separated from the remaining hardware gap.

The next required foundation stage is **GPIO-PHYS-0**: implement a real x86-64 platform GPIO interrupt backend, map supported GPIO controller hardware, bind ACPI GPIO controller namespaces to physical backend instances, configure GpioInt polarity/trigger/masking in hardware, and route real IRQ delivery into `gpio_connection_signal()`.

Until GPIO-PHYS-0 exists for the detected machine, I2C-HID devices requiring `GpioInt` intentionally remain non-operational. There is no polling or synthetic IRQ fallback.

### Next sequence

1. Publish I2C-HID-6 as one atomic commit.
2. Require CI/QEMU, SMP, NVMe and HID regression workflows to remain green.
3. Certify this appendix only after those gates pass.
4. Begin GPIO-PHYS-0 with fail-closed PCI/ACPI identification and no generic MMIO guesses.
5. After physical GPIO is available, run the first real I2C-HID interrupt/RESET/input report certification on hardware.
