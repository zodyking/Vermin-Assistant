"""Draw the add-on icon: a blue disc with a sound mark."""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path: Path, size: int) -> None:
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            raw.extend(_pixel(x + 0.5, y + 0.5, size))
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b"")
    path.write_bytes(png)


def _pixel(x: float, y: float, size: int) -> tuple[int, int, int, int]:
    center = size / 2
    dx = x - center
    dy = y - center
    radius = math.hypot(dx, dy)
    limit = size * 0.46
    if radius > limit:
        return (0, 0, 0, 0)
    angle = math.degrees(math.atan2(dy, dx))
    edge = abs(radius - limit) < max(1.5, size * 0.012)
    if edge:
        return (2, 119, 189, 255)
    for band in (0.18, 0.28, 0.38):
        if abs(angle) <= 38 and abs(radius - size * band) <= size * 0.018:
            return (255, 255, 255, 255)
    body = math.hypot(x - (center - size * 0.08), y - center)
    if body <= size * 0.055:
        return (16, 32, 39, 255)
    return (3, 169, 244, 255)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    write_png(root / "icon.png", 128)
    write_png(root / "logo.png", 256)


if __name__ == "__main__":
    main()
