#!/usr/bin/env python3
import os
import subprocess
import shutil

QEMU_EXE = r"C:\Program Files\qemu\qemu-system-x86_64.exe"
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OVMF_LOCAL = os.path.join(ROOT_DIR, "build", "ovmf.fd")
OVMF_ORIG = r"C:\Program Files\qemu\share\edk2-x86_64-code.fd"
ISO_ROOT = os.path.join(ROOT_DIR, "build", "iso_root")

def main():
    if not os.path.exists(OVMF_LOCAL) and os.path.exists(OVMF_ORIG):
        shutil.copyfile(OVMF_ORIG, OVMF_LOCAL)

    print("=================================================================")
    print("      INICIANDO BAKEN OS EM MODO UEFI BARE-METAL NO QEMU         ")
    print("=================================================================")

    cmd = [
        QEMU_EXE,
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={OVMF_LOCAL}",
        "-drive", f"file=fat:rw:{ISO_ROOT},format=raw",
        "-m", "4G",
        "-smp", "4",
        "-vga", "std",
        "-name", "Baken OS - Quantum Edition",
        "-net", "none"
    ]

    subprocess.run(cmd)

if __name__ == "__main__":
    main()
