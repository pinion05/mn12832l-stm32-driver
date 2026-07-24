"""Binary host-to-MCU frame protocol shared with ``vfd_host_link.c``."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Union


FRAME_WIDTH = 128
FRAME_HEIGHT = 32
FRAME_BYTES = FRAME_WIDTH * FRAME_HEIGHT // 8

MAGIC = b"VF"
PROTOCOL_VERSION = 1
FRAME_COMMAND = 0x01
ACK_COMMAND = 0x80
FRAME_HEADER_BYTES = 8
CRC_BYTES = 2
FRAME_PACKET_BYTES = FRAME_HEADER_BYTES + FRAME_BYTES + CRC_BYTES
ACK_PACKET_BYTES = 9

BytesLike = Union[bytes, bytearray, memoryview]


# --- MVLSB 픽셀 ↔ 바이트 변환 헬퍼 ---
# 코드 리뷰 CODE_REVIEW_20260724_0850 §1.5: 이 공식이 6~7곳에 중복됐던 것을
# 단일 소스로 통합. (y // 8) * FRAME_WIDTH + x 의 인덱스와 1 << (y % 8)의 비트 마스크.


def pixel_byte_index(x: int, y: int) -> int:
    """MVLSB 레이아웃에서 픽셀 (x, y)가 들어 있는 바이트 인덱스."""
    return (y // 8) * FRAME_WIDTH + x


def pixel_bit_mask(y: int) -> int:
    """MVLSB 레이아웃에서 픽셀 (x, y)에 해당하는 비트 마스크."""
    return 1 << (y % 8)


def pixel_is_on(frame: BytesLike, x: int, y: int) -> bool:
    """MVLSB 프레임에서 픽셀 (x, y)가 켜져 있는지."""
    return bool(frame[pixel_byte_index(x, y)] & pixel_bit_mask(y))


class ProtocolError(ValueError):
    """Raised when a wire packet violates the protocol contract."""


class AckStatus(IntEnum):
    """MCU acknowledgement status values."""

    OK = 0
    CRC_ERROR = 1
    VERSION_ERROR = 2
    COMMAND_ERROR = 3
    LENGTH_ERROR = 4
    BUSY = 5


@dataclass(frozen=True)
class FrameAck:
    """Decoded acknowledgement for one frame sequence."""

    sequence: int
    status: AckStatus


def crc16_ccitt(data: BytesLike) -> int:
    """Return CRC-16/CCITT-FALSE for *data*."""

    crc = 0xFFFF
    for value in memoryview(data).cast("B"):
        crc ^= value << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _validate_sequence(sequence: int) -> None:
    if not 0 <= sequence <= 0xFFFF:
        raise ValueError("sequence must be in the range 0..65535")


def encode_frame(frame: BytesLike, sequence: int) -> bytes:
    """Encode one native 512-byte MVLSB frame."""

    _validate_sequence(sequence)
    payload = bytes(frame)
    if len(payload) != FRAME_BYTES:
        raise ValueError(f"frame must contain exactly {FRAME_BYTES} bytes")

    header = b"".join(
        (
            MAGIC,
            bytes((PROTOCOL_VERSION, FRAME_COMMAND)),
            sequence.to_bytes(2, "little"),
            FRAME_BYTES.to_bytes(2, "little"),
        )
    )
    body = header + payload
    return body + crc16_ccitt(body).to_bytes(CRC_BYTES, "little")


def encode_ack(sequence: int, status: AckStatus) -> bytes:
    """Encode an ACK packet; primarily useful for bridges and test peers."""

    _validate_sequence(sequence)
    try:
        known_status = AckStatus(status)
    except ValueError as error:
        raise ValueError("unknown acknowledgement status") from error

    body = b"".join(
        (
            MAGIC,
            bytes((PROTOCOL_VERSION, ACK_COMMAND)),
            sequence.to_bytes(2, "little"),
            bytes((known_status,)),
        )
    )
    return body + crc16_ccitt(body).to_bytes(CRC_BYTES, "little")


def decode_ack(
    packet: BytesLike, expected_sequence: Optional[int] = None
) -> FrameAck:
    """Validate and decode a fixed-size MCU acknowledgement."""

    raw = bytes(packet)
    if len(raw) != ACK_PACKET_BYTES:
        raise ProtocolError(f"ACK must contain exactly {ACK_PACKET_BYTES} bytes")
    if raw[:2] != MAGIC:
        raise ProtocolError("ACK magic does not match")
    if raw[2] != PROTOCOL_VERSION:
        raise ProtocolError("ACK protocol version does not match")
    if raw[3] != ACK_COMMAND:
        raise ProtocolError("packet is not an ACK")

    encoded_crc = int.from_bytes(raw[-CRC_BYTES:], "little")
    if encoded_crc != crc16_ccitt(raw[:-CRC_BYTES]):
        raise ProtocolError("ACK CRC does not match")

    sequence = int.from_bytes(raw[4:6], "little")
    if expected_sequence is not None:
        _validate_sequence(expected_sequence)
        if sequence != expected_sequence:
            raise ProtocolError(
                f"ACK sequence {sequence} does not match {expected_sequence}"
            )
    try:
        status = AckStatus(raw[6])
    except ValueError as error:
        raise ProtocolError(f"unknown ACK status {raw[6]}") from error
    return FrameAck(sequence=sequence, status=status)
