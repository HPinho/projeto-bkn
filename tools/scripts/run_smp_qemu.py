"""Run locally the same SMP proof required by GitHub Actions."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
FINAL_MARKER = "BAKEN:SMP_FPU_MIGRATION_READY"
REQUIRED_MARKERS = (
    "BAKEN:SMP_BASE_READY", "BAKEN:ACPI_AML_TABLES_READY",
    "BAKEN:ACPI_AML_DECODER_READY", "BAKEN:ACPI_AML_NAMESPACE_READY",
    "BAKEN:SMP_AP_ONLINE", "BAKEN:SMP_AP_RUNTIME_READY", "BAKEN:SMP_THREAD_ON_AP",
    "BAKEN:SMP_TIMER_ON_AP", "BAKEN:SMP_ANY_THREAD_ON_AP",
    "BAKEN:SMP_HEAP_READY", "BAKEN:SMP_TLB_SHOOTDOWN_READY",
    "BAKEN:SMP_RING3_ON_AP", "BAKEN:SMP_RING3_RESUMED_ON_AP",
    "BAKEN:SMP_PROCESS_TLB_READY", "BAKEN:SMP_RING3_ON_AP_READY",
    "BAKEN:SMP_PROCESS_MIGRATED", FINAL_MARKER,
    "BAKEN:USER_FAULT_ISOLATED_READY", "BAKEN:SMP_USER_FAULT_ISOLATED_READY",
)


def build_iso(iso: Path) -> None:
    if os.name == "nt":
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            raise RuntimeError("PowerShell not found")
        subprocess.run([shell, "-NoProfile", "-File",
                        str(ROOT / "tools/build_uefi_desktop.ps1")], cwd=ROOT, check=True)
    else:
        output = ROOT / "build/iso_root/EFI/BOOT/BOOTX64.EFI"
        output.parent.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment.setdefault("SOTLAS_CC", "x86_64-w64-mingw32-gcc")
        subprocess.run([sys.executable, "tools/sotlas_compile/compiler.py", "build",
                        "kernel/src/main.sotlas", "--manifest", "build/sotlas-main.manifest.json",
                        "--output", str(output)], cwd=ROOT, env=environment, check=True)
    subprocess.run([sys.executable, "tools/scripts/create_uefi_iso.py"], cwd=ROOT, check=True)
    if not iso.is_file() or iso.stat().st_size == 0:
        raise RuntimeError(f"ISO was not generated: {iso}")


def marker_lines(serial: str) -> set[str]:
    return {line.strip() for line in serial.splitlines() if line.startswith("BAKEN:")}


def validate(serial: str) -> list[str]:
    errors: list[str] = []
    if "BAKEN:HEX=E:" in serial:
        errors.append("CPU exception reported (BAKEN:HEX=E:)")
    lines = marker_lines(serial)
    failures = re.findall(r"^BAKEN:HEX=Q:8[0-9A-Fa-f]{7}$", serial, re.M)
    errors.extend(f"Ring3/TLB probe failed: {marker}" for marker in failures)
    errors.extend(f"missing {marker}" for marker in REQUIRED_MARKERS if marker not in lines)
    return errors


def run_once(args: argparse.Namespace, proof: int, diagnostics: Path) -> None:
    serial_path = diagnostics / f"qemu-smp-serial-{proof}.log"
    vars_path = diagnostics / f"OVMF_VARS_SMP_{proof}.fd"
    qemu_log = diagnostics / f"qemu-smp-{proof}.log"
    shutil.copyfile(args.ovmf_vars, vars_path)
    command = [
        args.qemu, "-machine", "q35", "-smp", "2", "-m", "512M", "-no-reboot",
        "-drive", f"if=pflash,format=raw,readonly=on,file={args.ovmf_code}",
        "-drive", f"if=pflash,format=raw,file={vars_path}", "-cdrom", str(args.iso),
        "-device", "qemu-xhci,id=xhci", "-device", "usb-kbd,bus=xhci.0",
        "-display", "none", "-monitor", "none", "-serial", f"file:{serial_path}",
    ]
    started = time.monotonic()
    stop_reason = "timeout"
    with qemu_log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=output)
        try:
            deadline = started + args.timeout
            while time.monotonic() < deadline:
                serial = serial_path.read_text(errors="replace") if serial_path.exists() else ""
                if "BAKEN:HEX=E:" in serial or re.search(r"^BAKEN:HEX=Q:8[0-9A-Fa-f]{7}$", serial, re.M):
                    stop_reason = "kernel failure"
                    break
                if FINAL_MARKER in marker_lines(serial):
                    stop_reason = "final marker"
                    break
                if process.poll() is not None:
                    stop_reason = f"QEMU exited with status {process.returncode}"
                    break
                time.sleep(args.poll_interval)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    serial = serial_path.read_text(errors="replace") if serial_path.exists() else ""
    errors = validate(serial)
    if stop_reason != "final marker":
        errors.insert(0, stop_reason)
    elapsed = time.monotonic() - started
    if errors:
        checkpoints = "\n".join(line for line in serial.splitlines() if "BAKEN:" in line)[-8192:]
        raise RuntimeError(f"proof {proof} failed in {elapsed:.2f}s: {'; '.join(errors)}\n"
                           f"Last checkpoints:\n{checkpoints}\nDiagnostics: {diagnostics}")
    print(f"PASS: SMP proof {proof}/{args.runs} in {elapsed:.2f}s ({serial_path})", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-log", type=Path, help="Validate a saved serial log without launching QEMU")
    parser.add_argument("--qemu", default=shutil.which("qemu-system-x86_64") or
                        "C:/Program Files/qemu/qemu-system-x86_64.exe")
    parser.add_argument("--ovmf-code", type=Path,
                        default=Path("C:/Program Files/qemu/share/edk2-x86_64-code.fd"))
    parser.add_argument("--ovmf-vars", type=Path,
                        default=Path("C:/Program Files/qemu/share/edk2-i386-vars.fd"))
    parser.add_argument("--iso", type=Path, default=ROOT / "build/baken_os.iso")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--poll-interval", type=float, default=0.05)
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    if args.validate_log:
        errors = validate(args.validate_log.read_text(errors="replace"))
        for error in errors:
            print(f"::error::{error}")
        return 1 if errors else 0
    if args.runs < 1 or args.runs > 20:
        parser.error("--runs must be between 1 and 20")
    if args.build:
        build_iso(args.iso)
    for path, label in ((Path(args.qemu), "QEMU"), (args.ovmf_code, "OVMF_CODE"),
                        (args.ovmf_vars, "OVMF_VARS"), (args.iso, "ISO")):
        if not path.is_file():
            parser.error(f"{label} not found: {path}")
    diagnostics = Path(tempfile.mkdtemp(prefix="smp-local-", dir=ROOT / "build"))
    print(f"SMP diagnostics: {diagnostics}", flush=True)
    try:
        for proof in range(1, args.runs + 1):
            run_once(args, proof, diagnostics)
    except RuntimeError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {args.runs} independent SMP boot(s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
