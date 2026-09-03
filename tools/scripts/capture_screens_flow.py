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

    monitor_port = 55562

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

    # 1. Tela 0: Welcome Carousel
    time.sleep(3.5)
    ppm0 = os.path.join(build_dir, "screen0_welcome.ppm")
    send_cmd(f"screendump {ppm0}")

    # 2. Envia clique ou Enter para avançar para a Tela 1 (Idiomas)
    send_cmd("sendkey ret")
    time.sleep(1.5)
    ppm1 = os.path.join(build_dir, "screen1_languages.ppm")
    send_cmd(f"screendump {ppm1}")

    # 3. Avança para a próxima tela
    send_cmd("sendkey ret")
    time.sleep(1.5)
    ppm2 = os.path.join(build_dir, "screen2_type.ppm")
    send_cmd(f"screendump {ppm2}")

    send_cmd("quit")
    sock.close()
    proc.wait()

    for ppm, png_name in [(ppm0, "screen0_welcome.png"), (ppm1, "screen1_languages.png"), (ppm2, "screen2_type.png")]:
        png = os.path.join(build_dir, png_name)
        if os.path.exists(ppm):
            Image.open(ppm).save(png)
            os.remove(ppm)
            print(f"[OK] Gravado: {png}")

if __name__ == "__main__":
    main()
