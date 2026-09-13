#!/usr/bin/env python3
"""Resolve um RIP PE/COFF para o símbolo anterior mais próximo em saída nm -n."""
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: symbolize_pe_rip.py <rip-hex> <nm-symbol-file>", file=sys.stderr)
        return 2
    try:
        rip = int(sys.argv[1], 16)
    except ValueError:
        print(f"invalid RIP: {sys.argv[1]}", file=sys.stderr)
        return 2

    symbol_file = Path(sys.argv[2])
    if not symbol_file.is_file():
        print(f"symbol file not found: {symbol_file}", file=sys.stderr)
        return 2

    best = None
    for raw in symbol_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = raw.split()
        if len(parts) < 3:
            continue
        try:
            address = int(parts[0], 16)
        except ValueError:
            continue
        if address <= rip and (best is None or address > best[0]):
            best = (address, parts[-1])

    if best is None:
        print(f"NEAREST_SYMBOL=none RIP=0x{rip:016X}")
        return 1

    address, name = best
    print(
        f"NEAREST_SYMBOL={name} BASE=0x{address:016X} "
        f"OFFSET=0x{rip - address:X} RIP=0x{rip:016X}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
