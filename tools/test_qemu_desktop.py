#!/usr/bin/env python3
"""Teste visual reproduzível do desktop UEFI no QEMU.

O kernel atual não possui console serial; por isso o teste usa o monitor QEMU
para fazer um screendump do framebuffer após o boot. A imagem é evidência de
que GOP, EFI e renderização chegaram ao desktop em uma VM de verdade.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
QEMU = Path(r"C:\Program Files\qemu\qemu-system-x86_64.exe")
OVMF = BUILD / "ovmf.fd"
DISK = BUILD / "baken_disk.img"
ISO = BUILD / "baken_os.iso"
INSTALLED_DISK = BUILD / "baken_installed.img"
INSTALL_TARGET = BUILD / "baken_install_target.img"
SHOT = BUILD / "qemu-desktop.ppm"
PORT = 45873


def framebuffer_has_color(path: Path) -> bool:
    """Evita aprovar uma captura PPM criada antes do primeiro frame EFI."""
    if not path.exists() or path.stat().st_size < 100:
        return False
    data = path.read_bytes()
    parts = data.split(b"\n", 3)
    return len(parts) == 4 and any(parts[3])


def monitor_connect() -> socket.socket:
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            conn = socket.create_connection(("127.0.0.1", PORT), timeout=1)
            conn.recv(4096)
            return conn
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("monitor QEMU não ficou disponível")


def monitor_command(conn: socket.socket, command: str) -> str:
    conn.sendall((command + "\n").encode("ascii"))
    time.sleep(0.6)
    return conn.recv(4096).decode("ascii", errors="replace")


def main(install: bool, installer: bool, optical_iso: bool, app: int | None = None,
         installed_disk: bool = False, attach_target: bool = False,
         save_note: str | None = None, save_theme: bool = False,
         create_files: bool = False, toggle_media: bool = False,
         menu: str | None = None, control_center: bool = False,
         spotlight: bool = False, context_menu: bool = False,
         terminal: bool = False, files: bool = False) -> int:
    media = INSTALLED_DISK if installed_disk else (ISO if optical_iso else DISK)
    for required in (QEMU, OVMF, media):
        if not required.exists():
            raise FileNotFoundError(f"arquivo necessário ausente: {required}")
    if attach_target and not INSTALL_TARGET.exists():
        with open(INSTALL_TARGET, "wb") as f:
            f.truncate(64 * 1024 * 1024)
        print(f"[OK] Disco alvo criado: {INSTALL_TARGET}")
    if install and (optical_iso or installed_disk):
        raise ValueError("--install exige o disco UEFI gravável, não a ISO óptica")
    if SHOT.exists():
        SHOT.unlink()

    media_drive = (
        f"media=cdrom,readonly=on,file={media}"
        if optical_iso else f"format=raw,file={media}"
    )
    command = [
        str(QEMU), "-accel", "tcg", "-m", "512M", "-smp", "1", "-vga", "std",
        "-device", "qemu-xhci", "-device", "usb-kbd", "-device", "usb-tablet",
        "-display", "none", "-monitor", f"tcp:127.0.0.1:{PORT},server,nowait",
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={OVMF}",
        "-drive", media_drive, "-no-reboot",
    ]
    if attach_target:
        command.extend(["-drive", f"format=raw,file={INSTALL_TARGET}"])
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        time.sleep(13)
        monitor = monitor_connect()
        if install:
            time.sleep(2)
            monitor_command(monitor, "sendkey 1")
            time.sleep(1)
            for _ in range(7):
                monitor_command(monitor, "sendkey ret")
                time.sleep(1.5)
            time.sleep(12)
        elif installer:
            monitor_command(monitor, "sendkey i")
            time.sleep(2)
        elif create_files:
            monitor_command(monitor, "sendkey 1")
            time.sleep(1)
            monitor_command(monitor, "sendkey d")
            monitor_command(monitor, "sendkey n")
            time.sleep(1)
        elif toggle_media:
            monitor_command(monitor, "sendkey m")
            time.sleep(1)
        elif menu is not None:
            monitor_command(monitor, f"sendkey {menu}")
            time.sleep(4)
        elif control_center:
            monitor_command(monitor, "sendkey c")
            time.sleep(4)
        elif spotlight:
            monitor_command(monitor, "sendkey s")
            time.sleep(4)
        elif terminal:
            monitor_command(monitor, "sendkey 4")
            time.sleep(4)
        elif context_menu:
            monitor_command(monitor, "sendkey x")
            time.sleep(4)
        elif save_theme:
            monitor_command(monitor, "sendkey t")
            time.sleep(4)
        elif save_note is not None:
            if not save_note.isascii() or not save_note.isalnum():
                raise ValueError("--save-note aceita somente marcador ASCII alfanumerico")
            monitor_command(monitor, "sendkey 2")
            for key in save_note.lower():
                monitor_command(monitor, f"sendkey {key}")
            monitor_command(monitor, "sendkey ret")
            time.sleep(4)
        elif files:
            monitor_command(monitor, "sendkey 1")
            time.sleep(4)
        elif app is not None:
            monitor_command(monitor, f"sendkey {app}")
            time.sleep(4)
        for attempt in range(5):
            monitor_command(monitor, f"screendump {SHOT}")
            if framebuffer_has_color(SHOT):
                break
            if attempt < 4:
                time.sleep(5)
        monitor.close()
        if not framebuffer_has_color(SHOT):
            raise RuntimeError("QEMU não produziu um framebuffer visível; captura permaneceu preta")
        print(f"[OK] framebuffer capturado: {SHOT} ({SHOT.stat().st_size} bytes)")
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--install", action="store_true", help="salva o registro persistente de teste no guest")
        mode.add_argument("--installer", action="store_true", help="abre o assistente sem gravar no disco")
        media = parser.add_mutually_exclusive_group()
        media.add_argument("--iso", action="store_true", help="inicializa a ISO óptica em vez do disco UEFI gravável")
        media.add_argument("--installed", action="store_true", help="inicializa o disco virtual GPT/FAT32 instalado")
        parser.add_argument("--target", action="store_true", help="anexa o segundo disco virtual-alvo de instalação")
        mode.add_argument("--app", type=int, choices=range(1, 7), help="abre o aplicativo correspondente (1 a 6)")
        mode.add_argument("--menu", choices=["a", "b"], help="abre o menu suspenso ('a' = Arquivo, 'b' = Baken OS)")
        mode.add_argument("--control-center", action="store_true", help="abre a Central de Controle Q-HAL")
        mode.add_argument("--spotlight", action="store_true", help="abre a Busca Global Spotlight")
        mode.add_argument("--terminal", action="store_true", help="abre a janela do Terminal Sotlas")
        mode.add_argument("--files", action="store_true", help="abre o Explorador de Arquivos BakenFS")
        mode.add_argument("--context-menu", action="store_true", help="abre o menu de contexto do desktop")
        mode.add_argument("--save-note", metavar="MARCADOR", help="anexa e salva um marcador no editor de notas")
        mode.add_argument("--save-theme", action="store_true", help="alterna para Modo Escuro/Claro")
        mode.add_argument("--create-files", action="store_true", help="cria pasta e arquivo pelo gerenciador BakenFS")
        mode.add_argument("--media", action="store_true", help="alterna o estado do player local")
        args = parser.parse_args()
        raise SystemExit(main(args.install, args.installer, args.iso, args.app, args.installed, args.target,
                              args.save_note, args.save_theme, args.create_files, args.media, args.menu,
                              args.control_center, args.spotlight, args.context_menu, args.terminal, args.files))
    except Exception as error:
        print(f"[ERRO] teste QEMU: {error}", file=sys.stderr)
        raise SystemExit(1)
