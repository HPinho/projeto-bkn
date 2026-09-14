# Kernel I2C Handoff — Appendix XIII

## I2C-HID protocol/lifecycle hardening and physical GPIO boundary

Append-only handoff. Do not rewrite Appendices I–XII.

### Base before this stage

- Branch: `main`
- Parent commit: `a0acb0fd61db4f0fe18d5fcbf7abcd804e8a7446`
- Parent tree: `09345402b637c20936ac5a143a39f8f7e1775a96`

### Files hardened

- `kernel/src/drivers/i2c_hid_command.sotlas`
- `kernel/src/drivers/i2c_hid_input.sotlas`
- `kernel/src/drivers/i2c_hid_manager.sotlas`
- `kernel/src/drivers/gpio_core.sotlas`
- `tests/test_i2c_hid_manager.py`
- `tests/test_i2c_hid_hardening_contract.py`

### Protocol invariants

`i2c_hid_command_get_report` must use one `i2c_device_write_read` transaction. The write phase is:

`wCommandRegister LE16 | type/report-id nibble | GET_REPORT | [extended report-id] | wDataRegister LE16`

`i2c_hid_command_set_report` must use one `i2c_device_write` transaction. The frame is:

`wCommandRegister LE16 | type/report-id nibble | SET_REPORT | [extended report-id] | wDataRegister LE16 | total-report-length LE16 | [numbered report-id] | payload`

Do not restore the former two-transfer command/data behavior.

### Runtime identity invariants

ACPI discovery slot and I2C-HID input runtime slot are distinct identities.

- `device_slot`: ACPI/I2C-HID discovery identity only.
- `input_device_index`: slot returned by `i2c_hid_input_register_device_index` and used by IRQ/report service.
- generic input identity remains `input_device_id + input_device_generation`.
- I2C identity remains `i2c_device_id + i2c_generation`.
- GPIO identity remains `connection_id + generation`.

Never route runtime reports using `device_slot`.

### Input buffer invariant

The current certified fixed input buffer is `I2C_HID_MAX_INPUT_BUFFER_BYTES = 256`.

If `wMaxInputLength` exceeds this value, initialization fails. Do not silently clamp a physical read because truncating an HID-over-I2C frame destroys the `wLength` contract and can turn one report into a malformed partial report.

### RESET invariant

RESET is asynchronous. After SET_POWER(ON) and RESET succeed:

1. wait boundedly for the device's registered GPIO connection to become pending;
2. consume that pending state;
3. perform a 2-byte I2C read;
4. accept the reset acknowledgement only when LE16 `wLength == 0`.

Do not return to blind I2C polling before an IRQ.

### Rollback invariant

If initialization fails after an I2C device is attached, tear down all objects that were created, in dependency order:

1. `i2c_hid_input_unregister_device`
2. `hid_input_events_unbind_device`
3. `hid_input_device_map_unbind`
4. `input_device_detach`
5. `gpio_connection_unregister`
6. `i2c_device_detach`

All teardown uses the original generation. Stale generations must fail.

### GPIO physical ownership invariant

`gpio_connection_register_from_acpi` is only allowed to publish an ACTIVE logical GpioInt connection if the resource source resolves to an ACPI namespace currently owned by a registered `GpioPhysicalBackend`.

`gpio_physical_backend_register(namespace, backend_instance)` is the explicit bridge from future silicon-specific GPIO code into the generic GPIO core.

`gpio_physical_backend_unregister` fails while any logical connection still references that namespace.

There is intentionally no synthetic fallback and no assumption that an ACPI GpioInt descriptor proves the hardware was configured.

### Remaining foundation work: GPIO-PHYS-0

This is now the next blocking hardware stage for real I2C-HID input.

Requirements:

- identify supported physical GPIO controller(s) from actual platform enumeration rather than generic addresses;
- map MMIO through the kernel VMM, never firmware pointers after cutover;
- bind each physical controller instance to its resolved ACPI namespace using `gpio_physical_backend_register`;
- translate GpioInt pin number, polarity and level/edge trigger into verified silicon registers;
- implement mask/unmask and interrupt status acknowledge at hardware level;
- connect the hardware IRQ handler to `gpio_connection_signal(connection_id)` for the matching logical connection;
- keep fixed-capacity state and generation-safe teardown;
- fail closed on unsupported vendor/device/community/pad mappings;
- no polling-as-IRQ and no fake QEMU success path.

### Certification plan

Before marking I2C-HID-6 certified, require the repository workflows for its commit to pass. GPIO-PHYS-0 remains a separate stage and should not be declared certified until a supported controller can demonstrate a real interrupt from hardware into an HID-over-I2C RESET acknowledgement and normal input report.
