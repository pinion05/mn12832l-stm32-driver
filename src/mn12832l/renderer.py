"""Adafruit ``framebuf`` adapter for the VFD's native MVLSB layout."""

from __future__ import annotations

from typing import Any, Callable

import adafruit_framebuf

from .protocol import FRAME_BYTES, FRAME_HEIGHT, FRAME_WIDTH


class MvlsbRenderer:
    """Own a native 512-byte frame and expose Adafruit drawing primitives."""

    def __init__(self) -> None:
        self._buffer = bytearray(FRAME_BYTES)
        self._framebuffer = adafruit_framebuf.FrameBuffer(
            self._buffer,
            FRAME_WIDTH,
            FRAME_HEIGHT,
            buf_format=adafruit_framebuf.MVLSB,
        )

    @property
    def framebuffer(self) -> Any:
        """Return the Adafruit framebuffer drawing surface."""

        return self._framebuffer

    def clear(self) -> None:
        """Clear all pixels in the current logical frame."""

        self._framebuffer.fill(0)

    def snapshot(self) -> bytes:
        """Return an immutable native-layout copy of the current frame."""

        return bytes(self._buffer)

    def render(
        self, model: Any, draw: Callable[[Any, Any], None]
    ) -> bytes:
        """Clear, render one high-level model, and return its frame."""

        self.clear()
        draw(model, self._framebuffer)
        return self.snapshot()

    def load_image(self, image: Any) -> None:
        """Load a Pillow mode-1 128x32 image into native MVLSB storage."""

        if getattr(image, "size", None) != (FRAME_WIDTH, FRAME_HEIGHT):
            raise ValueError(
                f"image must have size {FRAME_WIDTH}x{FRAME_HEIGHT}"
            )
        if getattr(image, "mode", None) != "1":
            raise ValueError("image must use Pillow mode '1'")
        self._framebuffer.image(image)
