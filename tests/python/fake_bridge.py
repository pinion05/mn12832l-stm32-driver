#!/usr/bin/env python3
from __future__ import annotations

import sys

from mn12832l.protocol import (
    FRAME_PACKET_BYTES,
    AckStatus,
    encode_ack,
)


def read_exact(size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = sys.stdin.buffer.read(size - len(data))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def main() -> int:
    while True:
        packet = read_exact(FRAME_PACKET_BYTES)
        if not packet:
            return 0
        if len(packet) != FRAME_PACKET_BYTES:
            return 2
        sequence = int.from_bytes(packet[4:6], "little")
        sys.stdout.buffer.write(encode_ack(sequence, AckStatus.OK))
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    raise SystemExit(main())
