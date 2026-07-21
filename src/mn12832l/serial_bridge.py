"""Persistent stdin/stdout proxy for one pyserial connection."""

from __future__ import annotations

import argparse
import sys
from typing import Any, BinaryIO, Optional, Sequence

from .protocol import (
    ACK_PACKET_BYTES,
    FRAME_PACKET_BYTES,
    ProtocolError,
    decode_ack,
)


class BridgeError(RuntimeError):
    """Raised when either side of the byte proxy ends mid-packet."""


def _read_exact(
    stream: Any, size: int, *, clean_eof: bool = False
) -> Optional[bytes]:
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            if clean_eof and not data:
                return None
            raise BridgeError(f"stream ended after {len(data)} of {size} bytes")
        data.extend(chunk)
    return bytes(data)


def run_bridge(device: Any, input_stream: BinaryIO, output_stream: BinaryIO) -> int:
    """Proxy complete frame packets through an already-open serial device."""

    count = 0
    while True:
        packet = _read_exact(
            input_stream, FRAME_PACKET_BYTES, clean_eof=True
        )
        if packet is None:
            return count

        written = device.write(packet)
        if written is not None and written != len(packet):
            raise BridgeError(
                f"serial write accepted {written} of {len(packet)} bytes"
            )
        device.flush()
        ack = _read_exact(device, ACK_PACKET_BYTES)
        if ack is None:  # pragma: no cover - non-clean EOF cannot return None
            raise BridgeError("serial device returned no ACK")
        sequence = int.from_bytes(packet[4:6], "little")
        try:
            decode_ack(ack, expected_sequence=sequence)
        except ProtocolError as error:
            raise BridgeError("serial device returned an invalid ACK") from error
        output_stream.write(ack)
        output_stream.flush()
        count += 1


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Persistent MN12832L frame proxy over a serial device"
    )
    parser.add_argument("--port", required=True, help="serial device path")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=1.0)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _argument_parser().parse_args(argv)
    if args.baud <= 0 or args.timeout <= 0:
        print("baud and timeout must be greater than zero", file=sys.stderr)
        return 2

    try:
        import serial
    except ImportError:
        print(
            "pyserial is required: pip install 'mn12832l-vfd[serial]'",
            file=sys.stderr,
        )
        return 2

    try:
        with serial.Serial(
            port=args.port,
            baudrate=args.baud,
            timeout=args.timeout,
            write_timeout=args.timeout,
        ) as device:
            run_bridge(device, sys.stdin.buffer, sys.stdout.buffer)
    except (BridgeError, OSError, serial.SerialException) as error:
        print(f"mn12832l serial bridge: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
