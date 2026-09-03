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

    monitor_port = 55560

    args = [
        qemu,
        "-accel", "tcg,thread=multi",
        "-cpu", "max",
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={ovmf}",
        "-drive", f"media=cdrom,readonly=on,file={iso}",
        "-device", "qemu-xhci,id=xhci",
        "-device", "usb-tablet,bus=xhci.0",
        "-device", "usb-mouse,bus=xhci.0",
        "-device", "usb-kbd,bus=xhci.0",
        "-m", "4G",
        "-smp", "1",
        "-device", "VGA,vgamem_mb=64,xres=1920,yres=1080",
        "-serial", f"file:{os.path.join(build_dir, 'qemu_debug.log')}",
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
    try:
        sock.recv(4096)
    except Exception:
        pass

    def send_cmd(cmd):
        sock.sendall((cmd + "\n").encode('utf-8'))
        time.sleep(0.8)
        try:
            return sock.recv(4096).decode('utf-8')
        except Exception:
            return ""

    # Aguarda o carrossel rotacionar (~6 a 7 segundos de simulação)
    time.sleep(6.5)

    ppm_carousel = os.path.join(build_dir, "view-v3-carousel.ppm")
    send_cmd(f"screendump {ppm_carousel}")
    time.sleep(0.8)

    send_cmd("quit")
    sock.close()
    proc.wait()

    png_carousel = os.path.join(build_dir, "view-v3-carousel.png")
    if os.path.exists(ppm_carousel):
        Image.open(ppm_carousel).save(png_carousel)
        os.remove(ppm_carousel)
        print(f"[OK] Gravado: {png_carousel}")

if __name__ == "__main__":
    main()
