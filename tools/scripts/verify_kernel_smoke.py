"""Fail closed on incomplete kernel execution or any reported CPU/AML failure."""
import argparse
from pathlib import Path

REQUIRED = (
    "PROCESS_SCHEDULER_READY", "ACPI_AML_TABLES_READY", "ACPI_AML_DECODER_READY",
    "ACPI_AML_DATA_READY", "ACPI_AML_NAMESPACE_READY", "ACPI_AML_NAMESPACE_LOADED",
    "HEAP_READY", "PLATFORM_READY", "DEVICE_CATALOG_READY", "STORAGE_DRIVER_BOUND", "PROCESS_ISOLATION_READY", "PROCESS_REGISTRY_READY", "BARE_METAL_READY",
    "SMP_BASE_READY",
    "SCHEDULER_SWITCH", "SCHEDULER_ROUND_TRIP", "RUN_QUEUE_CREATED",
    "RUN_QUEUE_SWITCH", "YIELD_ROUND_TRIP", "WAIT_BLOCKED", "WAIT_WAKE",
    "WAIT_RESUME", "SLEEP_BLOCKED", "SLEEP_WAKE", "SLEEP_RESUME",
    "THREAD_EXIT", "THREAD_REAP", "STACK_RELEASE",
    "FPU_CONTEXT_READY", "RING3_ENTERED", "RING3_READY", "SYSCALL_READY",
    "USER_COPY_READY", "USERSPACE_LOADER_READY",
    "USER_FAULT_ISOLATED_READY",
)


def validate(serial: str) -> list[str]:
    lines = {line.strip() for line in serial.splitlines()}
    errors = []
    if "BAKEN:HEX=E:" in serial:
        errors.append("CPU exception reported (BAKEN:HEX=E:)")
    if "BAKEN:HEX=A:" in serial:
        errors.append("AML namespace loader failed (BAKEN:HEX=A:, offset in BAKEN:HEX=B:)")
    errors.extend(f"Missing BAKEN:{marker}" for marker in REQUIRED
                  if f"BAKEN:{marker}" not in lines)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("serial", type=Path)
    args = parser.parse_args()
    try:
        serial = args.serial.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"::error::Cannot read kernel serial log: {exc}")
        return 1
    errors = validate(serial)
    for error in errors:
        print(f"::error::{error}")
    if errors:
        print("Last kernel checkpoints:")
        print("\n".join(line for line in serial.splitlines()
                        if "BAKEN:" in line)[-4096:])
        return 1
    print("Kernel smoke passed: all milestones present, no CPU/AML failure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())