#!/usr/bin/env python3
"""Inicializador gráfico interativo do Baken OS no QEMU com compilação automática e suporte a disco alvo."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
QEMU = Path(r"C:\Program Files\qemu\qemu-system-x86_64.exe")
OVMF = BUILD / "ovmf.fd"
ISO = BUILD / "baken_os.iso"
TARGET_DISK = BUILD / "baken_install_target.img"


def build_artifacts():
    print("[1/3] Compilando kernel Sotlas e gerando BOOTX64.EFI...")
    comp_script = ROOT / "tools" / "sotlas_compile" / "compiler.py"
    entry = ROOT / "kernel" / "src" / "main.sotlas"
    out_efi = BUILD / "iso_root" / "EFI" / "BOOT" / "BOOTX64.EFI"
    manifest = BUILD / "sotlas-main.manifest.json"
    
    res = subprocess.run([sys.executable, str(comp_script), "build", str(entry), "-o", str(out_efi), "-m", str(manifest)], cwd=ROOT)
    if res.returncode != 0:
        print("[ERRO] Falha ao compilar BOOTX64.EFI", file=sys.stderr)
        return False
        
    print("[2/3] Gerando imagem ISO óptica UEFI...")
    iso_script = ROOT / "tools" / "scripts" / "create_uefi_iso.py"
    res = subprocess.run([sys.executable, str(iso_script)], cwd=ROOT)
    if res.returncode != 0:
        print("[ERRO] Falha ao gerar baken_os.iso", file=sys.stderr)
        return False

    print("[3/3] Garantindo disco de teste alvo para instalacao...")
    disk_script = ROOT / "tools" / "scripts" / "create_fat32_img.py"
    res = subprocess.run([sys.executable, str(disk_script)], cwd=ROOT)
    if res.returncode != 0:
        print("[ERRO] Falha ao gerar baken_install_target.img", file=sys.stderr)
        return False

    return True


def main():
    if not QEMU.exists():
        print(f"[ERRO] QEMU nao encontrado em: {QEMU}", file=sys.stderr)
        return 1

    if not OVMF.exists():
        print(f"[ERRO] Firmware OVMF nao encontrado em: {OVMF}", file=sys.stderr)
        return 1

    if not build_artifacts():
        return 1

    print(f"\n=== Baken OS - Inicializando QEMU GUI ===")
    print(f"  Midia Live: {ISO.name} (CD-ROM)")
    print(f"  Disco Alvo: {TARGET_DISK.name} (Unidade Gravavel 64MB)")
    print(f"  Mouse: USB Tablet com coordenadas absolutas nativo")
    print(f"  Teclado: USB Keyboard nativo")
    print(f"===================================================\n")

    cmd = [
        str(QEMU),
        "-m", "1024M",
        "-smp", "2",
        "-vga", "std",
        "-device", "qemu-xhci",
        "-device", "usb-kbd",
        "-device", "usb-tablet",
        "-device", "usb-mouse",
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={OVMF}",
        "-drive", f"media=cdrom,readonly=on,file={ISO}",
    ]
    
    if TARGET_DISK.exists():
        cmd.extend(["-drive", f"format=raw,file={TARGET_DISK}"])

    try:
        proc = subprocess.run(cmd, cwd=ROOT)
        return proc.returncode
    except KeyboardInterrupt:
        print("\n[OK] Sessao QEMU finalizada pelo usuario.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
