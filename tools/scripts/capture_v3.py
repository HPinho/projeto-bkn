import subprocess
import time
import socket
import os
from PIL import Image

def main():
    qemu = r"C:\Program Files\qemu\qemu-system-x86_64.exe"
    ovmf = r"C:\Projetos\projeto-bkn\build\ovmf.fd"
    iso = r"C:\Projetos\projeto-bkn\build\baken_os.iso"
    build_dir = r"C:\Projetos\projeto-bkn\build"

    monitor_port = 55558

    args = [
        qemu,
        "-accel", "tcg,thread=multi",
        "-cpu", "max",
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={ovmf}",
        "-drive", f"media=cdrom,readonly=on,file={iso}",
        "-device", "usb-ehci,id=ehci",
        "-device", "usb-tablet,bus=ehci.0",
        "-device", "usb-mouse,bus=ehci.0",
        "-device", "usb-kbd,bus=ehci.0",
        "-m", "4G",
        "-smp", "1",
        "-device", "VGA,vgamem_mb=64,xres=1920,yres=1080",
        "-monitor", f"tcp:127.0.0.1:{monitor_port},server,nowait",
        "-display", "none"
    ]

    proc = subprocess.Popen(args)
    time.sleep(3)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for i in range(15):
        try:
            sock.connect(("127.0.0.1", monitor_port))
            break
        except Exception:
            time.sleep(1)

    time.sleep(1)
    sock.recv(4096)

    def send_cmd(cmd):
        sock.sendall((cmd + "\n").encode('utf-8'))
        time.sleep(0.8)
        try:
            return sock.recv(4096).decode('utf-8')
        except Exception:
            return ""

    time.sleep(4)

    # 1. Captura Tela de Boas-Vindas
    ppm_welcome = os.path.join(build_dir, "view-v3-welcome.ppm")
    send_cmd(f"screendump {ppm_welcome}")
    time.sleep(0.8)

    # 2. Avança para Tela de Idiomas
    send_cmd("sendkey ret")
    time.sleep(1.2)
    ppm_lang = os.path.join(build_dir, "view-v3-lang.ppm")
    send_cmd(f"screendump {ppm_lang}")
    time.sleep(0.8)

    # 3. Entra no Desktop
    send_cmd("sendkey d")
    time.sleep(2.0)
    ppm_desktop = os.path.join(build_dir, "view-v3-desktop.ppm")
    send_cmd(f"screendump {ppm_desktop}")
    time.sleep(0.8)

    # Encerra QEMU
    send_cmd("quit")
    sock.close()
    proc.wait()

    for ppm_path in [ppm_welcome, ppm_lang, ppm_desktop]:
        if os.path.exists(ppm_path):
            png_path = ppm_path.replace(".ppm", ".png")
            try:
                img = Image.open(ppm_path)
                img.save(png_path)
                os.remove(ppm_path)
                print(f"[OK] Gravado: {png_path}")
            except Exception as e:
                print(f"[ERRO] Conversao PPM para PNG: {e}")

if __name__ == "__main__":
    main()
