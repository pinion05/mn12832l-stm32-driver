"""High-level render, transfer, retry, and lifecycle orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol

from .protocol import FRAME_BYTES, AckStatus, decode_ack, encode_frame
from .renderer import MvlsbRenderer


class FrameTransport(Protocol):
    """Minimal transport contract consumed by :class:`VfdDisplay`."""

    def open(self) -> None:
        ...

    def request(self, packet: bytes) -> bytes:
        ...

    def close(self) -> None:
        ...


class DisplayError(RuntimeError):
    """Base error for high-level display operations."""


class DisplayClosedError(DisplayError):
    """Raised when presenting through a closed display."""


class FrameRejectedError(DisplayError):
    """Raised when the MCU rejects a complete frame packet."""

    def __init__(self, sequence: int, status: AckStatus) -> None:
        self.sequence = sequence
        self.status = status
        super().__init__(f"frame {sequence} rejected with {status.name}")


@dataclass(frozen=True)
class PresentResult:
    """Outcome of one logical frame presentation."""

    sent: bool
    sequence: int
    attempts: int


class VfdDisplay:
    """Join high-level model rendering to reliable native-frame transfer."""

    _RETRYABLE = frozenset((AckStatus.BUSY, AckStatus.CRC_ERROR))

    def __init__(
        self,
        transport: FrameTransport,
        renderer: Optional[MvlsbRenderer] = None,
        retry_limit: int = 2,
        retry_delay: float = 0.01,
    ) -> None:
        if retry_limit < 0:
            raise ValueError("retry_limit must not be negative")
        if retry_delay < 0:
            raise ValueError("retry_delay must not be negative")
        self._transport = transport
        self._renderer = renderer or MvlsbRenderer()
        self._retry_limit = retry_limit
        self._retry_delay = retry_delay
        self._is_open = False
        self._next_sequence = 0
        self._last_sequence = 0
        self._last_frame: Optional[bytes] = None

    @property
    def renderer(self) -> MvlsbRenderer:
        return self._renderer

    def open(self) -> None:
        """Initialize the lower transport once."""

        if self._is_open:
            return
        self._transport.open()
        # A reopened bridge may point at a reset MCU, so force state replay.
        self._last_frame = None
        self._is_open = True

    def close(self) -> None:
        """Close the lower transport once."""

        if not self._is_open:
            return
        try:
            self._transport.close()
        finally:
            self._is_open = False

    def __enter__(self) -> "VfdDisplay":
        self.open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def update(
        self, model: Any, draw: Callable[[Any, Any], None]
    ) -> PresentResult:
        """Render a model into a clean buffer and present it."""

        return self.present(self._renderer.render(model, draw))

    def present(self, frame: bytes) -> PresentResult:
        """Send a changed frame, retry transient NACKs, and cache ACKed state."""

        if not self._is_open:
            raise DisplayClosedError("display is not open")
        payload = bytes(frame)
        if len(payload) != FRAME_BYTES:
            raise ValueError(f"frame must contain exactly {FRAME_BYTES} bytes")
        if payload == self._last_frame:
            return PresentResult(
                sent=False, sequence=self._last_sequence, attempts=0
            )

        sequence = self._next_sequence
        packet = encode_frame(payload, sequence)
        attempts = 0
        while True:
            attempts += 1
            ack = decode_ack(
                self._transport.request(packet), expected_sequence=sequence
            )
            if ack.status is AckStatus.OK:
                self._last_frame = payload
                self._last_sequence = sequence
                self._next_sequence = (sequence + 1) & 0xFFFF
                return PresentResult(
                    sent=True, sequence=sequence, attempts=attempts
                )
            if ack.status in self._RETRYABLE and attempts <= self._retry_limit:
                if self._retry_delay:
                    time.sleep(self._retry_delay)
                continue
            raise FrameRejectedError(sequence, ack.status)
