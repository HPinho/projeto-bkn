#!/usr/bin/env python3
"""Inicializador gráfico interativo do Baken OS no QEMU com suporte a Mouse USB Tablet."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
QEMU = Path(r"C:\Program Files\qemu\qemu-system-x86_64.exe")
OVMF = BUILD / "ovmf.fd"
ISO = BUILD / "baken_os.iso"
DISK = BUILD / "baken_disk.img"


def main():
    if not QEMU.exists():
        print(f"[ERRO] QEMU nao encontrado em: {QEMU}", file=sys.stderr)
        return 1

    if not OVMF.exists():
        print(f"[ERRO] Firmware OVMF nao encontrado em: {OVMF}", file=sys.stderr)
        return 1

    media = ISO if ISO.exists() else DISK
    if not media.exists():
        print(f"[ERRO] Imagem de boot nao encontrada (baken_os.iso ou baken_disk.img)", file=sys.stderr)
        return 1

    print(f"=== Baken OS Sovereign - Inicializando QEMU GUI ===")
    print(f"  Midia: {media.name}")
    print(f"  Mouse: USB Tablet com coordenadas absolutas ativado")
    print(f"  Teclado: USB Keyboard nativo")
    print(f"===================================================")

    media_arg = ["-drive", f"media=cdrom,readonly=on,file={media}"] if media.suffix == ".iso" else ["-drive", f"format=raw,file={media}"]

    cmd = [
        str(QEMU),
        "-m", "1024M",
        "-smp", "2",
        "-vga", "std",
        "-device", "qemu-xhci",
        "-device", "usb-kbd",
        "-device", "usb-tablet",
        "-show-cursor",
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={OVMF}",
    ] + media_arg

    try:
        proc = subprocess.run(cmd, cwd=ROOT)
        return proc.returncode
    except KeyboardInterrupt:
        print("\n[OK] Sessao QEMU finalizada pelo usuario.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
