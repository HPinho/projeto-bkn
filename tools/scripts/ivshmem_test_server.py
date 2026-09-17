#!/usr/bin/env python3
"""Minimal single-peer ivshmem server for the DF-7e2 MSI-X runtime proof.

This is deliberately test-only. It implements the documented QEMU protocol:
version 0, peer id 0, shared-memory fd, then one eventfd for vector 0.
"""

from __future__ import annotations

import argparse
import array
import os
import pathlib
import signal
import socket
import struct
import sys
import time


def send_message(conn: socket.socket, value: int, fd: int | None = None) -> None:
    ancillary = []
    if fd is not None:
        rights = array.array("i", [fd])
        ancillary = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, rights)]
    sent = conn.sendmsg([struct.pack("<q", value)], ancillary)
    if sent != 8:
        raise RuntimeError(f"short ivshmem protocol write: {sent}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--ready", required=True)
    parser.add_argument("--size", type=int, default=1 << 20)
    args = parser.parse_args()

    sock_path = pathlib.Path(args.socket)
    ready_path = pathlib.Path(args.ready)
    sock_path.parent.mkdir(parents=True, exist_ok=True)
    sock_path.unlink(missing_ok=True)
    ready_path.unlink(missing_ok=True)

    shm_fd = os.memfd_create("baken-df7e2-ivshmem", os.MFD_CLOEXEC)
    os.ftruncate(shm_fd, args.size)
    event_fd = os.eventfd(0, os.EFD_CLOEXEC | os.EFD_NONBLOCK)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(1)
    ready_path.write_text("ready\n", encoding="utf-8")

    stop = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    conn: socket.socket | None = None
    try:
        server.settimeout(30.0)
        conn, _ = server.accept()
        conn.settimeout(None)

        # QEMU ivshmem client-server protocol, in the required order.
        send_message(conn, 0)                 # protocol version
        send_message(conn, 0)                 # this client's peer ID
        send_message(conn, -1, shm_fd)         # shared memory
        send_message(conn, 0, event_fd)        # own vector 0 receive eventfd

        # Keep descriptors and the control connection alive for QEMU.
        while not stop:
            time.sleep(0.1)
    finally:
        if conn is not None:
            conn.close()
        server.close()
        os.close(event_fd)
        os.close(shm_fd)
        ready_path.unlink(missing_ok=True)
        sock_path.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - surfaced verbatim in CI
        print(f"ivshmem test server failed: {exc}", file=sys.stderr, flush=True)
        raise
