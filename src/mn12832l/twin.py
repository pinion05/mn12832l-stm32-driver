"""Full-stack digital twin and terminal renderer for the MN12832L driver."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, TextIO, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

from .display import DisplayError, VfdDisplay
from .protocol import (
    ACK_PACKET_BYTES,
    FRAME_BYTES,
    FRAME_HEADER_BYTES,
    FRAME_HEIGHT,
    FRAME_PACKET_BYTES,
    FRAME_WIDTH,
    AckStatus,
    ProtocolError,
    decode_ack,
)
from .renderer import MvlsbRenderer
from .transport import CommandPart, SubprocessTransport, TransportError

TRACE_HEADER = b"VFDTPIN1"
SCAN_PHASES = 43
PIXEL_BITS_PER_PHASE = 192
GRID_BITS_PER_PHASE = 48
BITS_PER_PHASE = PIXEL_BITS_PER_PHASE + GRID_BITS_PER_PHASE
BORDER_PERIMETER_PIXELS = 2 * (FRAME_WIDTH + FRAME_HEIGHT) - 4
DEFAULT_ASCII_ART_ASSET = "loading_wordmark.txt"
PIN_EVENTS_PER_FRAME = (
    7 + SCAN_PHASES * (1 + BITS_PER_PHASE * 3 + 1 + 4 + 1) + 4
)
PIN_TRACE_BYTES = len(TRACE_HEADER) + PIN_EVENTS_PER_FRAME * 2

EVENT_PHASE = 1
EVENT_SIN = 2
EVENT_CLK = 3
EVENT_GAP = 4
EVENT_BLANK = 5
EVENT_LAT = 6
EVENT_EF = 7
EVENT_HV = 8
EVENT_END = 9


class DigitalTwinError(RuntimeError):
    """Raised when the virtual pin trace violates the hardware protocol."""


class DigitalTwinTransport(SubprocessTransport):
    """FrameTransport adapter backed by the persistent C system twin."""

    def __init__(
        self, command: Sequence[CommandPart], timeout: float = 2.0
    ) -> None:
        super().__init__(command, timeout=timeout)
        self._last_result: Optional[DigitalTwinResult] = None

    @property
    def last_result(self) -> Optional[DigitalTwinResult]:
        """Return the pin reconstruction produced by the latest accepted ACK."""

        return self._last_result

    def open(self) -> None:
        self._last_result = None
        super().open()

    def _read_response(
        self, process: subprocess.Popen[bytes], packet: bytes
    ) -> bytes:
        self._last_result = None
        ack = self._read_exact(process, ACK_PACKET_BYTES)
        try:
            decoded = decode_ack(ack)
        except ProtocolError as error:
            raise TransportError("system twin returned an invalid ACK") from error

        if decoded.status is not AckStatus.OK:
            return ack
        if len(packet) != FRAME_PACKET_BYTES:
            raise TransportError("system twin accepted a malformed frame packet")

        trace = self._read_exact(process, PIN_TRACE_BYTES)
        source_frame = packet[
            FRAME_HEADER_BYTES : FRAME_HEADER_BYTES + FRAME_BYTES
        ]
        self._last_result = decode_pin_trace(trace, source_frame=source_frame)
        return ack


@dataclass(frozen=True)
class DigitalTwinResult:
    """Verified state reconstructed only from virtual physical-pin events."""

    reconstructed_frame: bytes
    source_frame: Optional[bytes]
    phases: int
    clock_rises: int
    latches: int
    gaps: int
    grid_checks: int
    pin_events: int
    hv_assertions: int
    final_pins: Mapping[str, int]

    @property
    def matches_source(self) -> bool:
        """Whether pin-level reconstruction equals the supplied source frame."""

        return (
            self.source_frame is not None
            and self.reconstructed_frame == self.source_frame
        )


def _fail(message: str, event_index: Optional[int] = None) -> DigitalTwinError:
    if event_index is None:
        return DigitalTwinError(message)
    return DigitalTwinError(f"event {event_index}: {message}")


def _set_binary_pin(
    pins: Dict[str, int], name: str, value: int, event_index: int
) -> int:
    if value not in (0, 1):
        raise _fail(f"{name} must be binary, got {value}", event_index)
    previous = pins[name]
    pins[name] = value
    return previous


def _reconstruct_frame(
    phase_bits: Mapping[int, Tuple[int, ...]]
) -> Tuple[bytes, int]:
    frame = bytearray(FRAME_BYTES)
    grid_checks = 0
    odd_lanes = (0, 2, 4)
    even_lanes = (5, 3, 1)

    for phase in range(1, SCAN_PHASES + 1):
        bits = phase_bits.get(phase)
        if bits is None or len(bits) != BITS_PER_PHASE:
            raise _fail(f"phase {phase} did not latch {BITS_PER_PHASE} bits")

        lanes = odd_lanes if phase & 1 else even_lanes
        source_count = 2 if phase == SCAN_PHASES else 3
        active_lanes = set(lanes[:source_count])
        base_column = (phase - 1) * 3

        for row in range(FRAME_HEIGHT):
            row_bits = bits[row * 6 : (row + 1) * 6]
            for lane, bit in enumerate(row_bits):
                if lane not in active_lanes and bit:
                    raise _fail(
                        f"phase {phase}, row {row} drove unused lane {lane}"
                    )
            for source in range(source_count):
                if row_bits[lanes[source]]:
                    byte_index = (row // 8) * FRAME_WIDTH + base_column + source
                    frame[byte_index] |= 1 << (row % 8)

        actual_grid = bits[PIXEL_BITS_PER_PHASE:]
        expected_grid = tuple(
            int(grid in (phase - 1, phase))
            for grid in range(GRID_BITS_PER_PHASE)
        )
        if actual_grid != expected_grid:
            raise _fail(f"phase {phase} has an invalid 48-bit grid selector")
        grid_checks += 1

    return bytes(frame), grid_checks


def decode_pin_trace(
    trace: bytes, source_frame: Optional[bytes] = None
) -> DigitalTwinResult:
    """Validate a binary pin trace and reconstruct its 512-byte framebuffer."""

    if not isinstance(trace, bytes):
        trace = bytes(trace)
    if not trace.startswith(TRACE_HEADER):
        raise _fail("invalid or missing VFDTPIN1 header")
    payload = trace[len(TRACE_HEADER) :]
    if not payload or len(payload) % 2 != 0:
        raise _fail("pin trace must contain complete two-byte events")
    if source_frame is not None:
        source_frame = bytes(source_frame)
        if len(source_frame) != FRAME_BYTES:
            raise ValueError(f"source frame must contain {FRAME_BYTES} bytes")

    pins = {
        "SIN": 0,
        "CLK": 0,
        "LAT": 0,
        "BLANK": 0,
        "EF": 0,
        "HV": 0,
    }
    phase_bits: Dict[int, Tuple[int, ...]] = {}
    shifted_bits: List[int] = []
    current_phase: Optional[int] = None
    gap_seen = False
    phase_count = 0
    clock_rises = 0
    latches = 0
    gaps = 0
    hv_assertions = 0
    ended = False
    event_count = len(payload) // 2

    for event_offset in range(0, len(payload), 2):
        event_index = event_offset // 2
        event = payload[event_offset]
        value = payload[event_offset + 1]
        if ended:
            raise _fail("events appear after END", event_index)

        if event == EVENT_PHASE:
            expected_phase = phase_count + 1
            if value != expected_phase or value > SCAN_PHASES:
                raise _fail(
                    f"expected phase {expected_phase}, got {value}", event_index
                )
            if current_phase is not None and current_phase not in phase_bits:
                raise _fail("next phase began before the previous latch", event_index)
            current_phase = value
            shifted_bits = []
            gap_seen = False
            phase_count += 1
        elif event == EVENT_SIN:
            _set_binary_pin(pins, "SIN", value, event_index)
        elif event == EVENT_CLK:
            previous = _set_binary_pin(pins, "CLK", value, event_index)
            if previous == 0 and value == 1:
                if current_phase is None:
                    raise _fail("clock rose outside a scan phase", event_index)
                if len(shifted_bits) >= BITS_PER_PHASE:
                    raise _fail("more than 240 bits shifted in one phase", event_index)
                shifted_bits.append(pins["SIN"])
                clock_rises += 1
        elif event == EVENT_GAP:
            if current_phase is None:
                raise _fail("pixel/grid gap occurred outside a phase", event_index)
            if value != PIXEL_BITS_PER_PHASE:
                raise _fail(f"invalid gap marker {value}", event_index)
            if gap_seen or len(shifted_bits) != PIXEL_BITS_PER_PHASE:
                raise _fail(
                    "gap must occur once after exactly 192 pixel bits",
                    event_index,
                )
            gap_seen = True
            gaps += 1
        elif event == EVENT_BLANK:
            _set_binary_pin(pins, "BLANK", value, event_index)
        elif event == EVENT_LAT:
            previous = _set_binary_pin(pins, "LAT", value, event_index)
            if previous == 0 and value == 1:
                if current_phase is None:
                    raise _fail("latch rose outside a scan phase", event_index)
                if pins["BLANK"] != 1:
                    raise _fail("latch rose while the display was unblanked", event_index)
                if len(shifted_bits) != BITS_PER_PHASE or not gap_seen:
                    raise _fail(
                        "latch requires 192 pixel and 48 grid bits",
                        event_index,
                    )
                if current_phase in phase_bits:
                    raise _fail("phase was latched more than once", event_index)
                phase_bits[current_phase] = tuple(shifted_bits)
                latches += 1
        elif event == EVENT_EF:
            _set_binary_pin(pins, "EF", value, event_index)
        elif event == EVENT_HV:
            previous = _set_binary_pin(pins, "HV", value, event_index)
            if previous == 0 and value == 1:
                hv_assertions += 1
        elif event == EVENT_END:
            if value != 0:
                raise _fail("END value must be zero", event_index)
            if pins["BLANK"] != 1 or pins["HV"] != 0 or pins["EF"] != 0:
                raise _fail("END occurred without fail-safe pin levels", event_index)
            ended = True
        else:
            raise _fail(f"unknown event code {event}", event_index)

    if not ended:
        raise _fail("pin trace is missing END")
    if phase_count != SCAN_PHASES:
        raise _fail(f"expected {SCAN_PHASES} phases, got {phase_count}")
    if clock_rises != SCAN_PHASES * BITS_PER_PHASE:
        raise _fail(f"expected 10320 rising clocks, got {clock_rises}")
    if latches != SCAN_PHASES or gaps != SCAN_PHASES:
        raise _fail("every phase must have one gap and one latch")
    if hv_assertions != 1:
        raise _fail(f"expected one frame-boundary HV pulse, got {hv_assertions}")

    reconstructed, grid_checks = _reconstruct_frame(phase_bits)
    if source_frame is not None and reconstructed != source_frame:
        byte_index = next(
            index
            for index, (actual, expected) in enumerate(
                zip(reconstructed, source_frame)
            )
            if actual != expected
        )
        different_bits = reconstructed[byte_index] ^ source_frame[byte_index]
        bit = (different_bits & -different_bits).bit_length() - 1
        x = byte_index % FRAME_WIDTH
        y = (byte_index // FRAME_WIDTH) * 8 + bit
        raise _fail(
            "pin reconstruction does not match source frame "
            f"at pixel ({x}, {y})"
        )
    return DigitalTwinResult(
        reconstructed_frame=reconstructed,
        source_frame=source_frame,
        phases=phase_count,
        clock_rises=clock_rises,
        latches=latches,
        gaps=gaps,
        grid_checks=grid_checks,
        pin_events=event_count,
        hv_assertions=hv_assertions,
        final_pins=dict(pins),
    )


def run_digital_twin(
    frame: bytes, engine: Union[os.PathLike[str], str]
) -> DigitalTwinResult:
    """Run the raw C scan/pin unit twin without the host transport layers."""

    frame = bytes(frame)
    if len(frame) != FRAME_BYTES:
        raise ValueError(f"frame must contain exactly {FRAME_BYTES} bytes")

    try:
        completed = subprocess.run(
            [os.fspath(engine)],
            input=frame,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5.0,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DigitalTwinError(f"could not run pin twin: {error}") from error

    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise DigitalTwinError(
            f"pin twin exited with {completed.returncode}: {detail or 'no detail'}"
        )
    return decode_pin_trace(completed.stdout, source_frame=frame)


def _pixel(frame: bytes, x: int, y: int) -> bool:
    return bool(frame[(y // 8) * FRAME_WIDTH + x] & (1 << (y % 8)))


def _half_block_rows(frame: bytes) -> List[str]:
    characters = {
        (False, False): " ",
        (True, False): "▀",
        (False, True): "▄",
        (True, True): "█",
    }
    rows: List[str] = []
    for y in range(0, FRAME_HEIGHT, 2):
        line = []
        for x in range(FRAME_WIDTH):
            top = _pixel(frame, x, y)
            bottom = _pixel(frame, x, y + 1)
            line.append(characters[(top, bottom)])
        rows.append("".join(line))
    return rows


def _braille_rows(frame: bytes) -> List[str]:
    dot_masks = ((0x01, 0x02, 0x04, 0x40), (0x08, 0x10, 0x20, 0x80))
    rows: List[str] = []
    for y in range(0, FRAME_HEIGHT, 4):
        line = []
        for x in range(0, FRAME_WIDTH, 2):
            dots = 0
            for dx in range(2):
                for dy in range(4):
                    if _pixel(frame, x + dx, y + dy):
                        dots |= dot_masks[dx][dy]
            line.append(chr(0x2800 + dots))
        rows.append("".join(line))
    return rows


def render_tui(
    result: DigitalTwinResult, *, color: bool = True, compact: bool = False
) -> str:
    """Render the reconstructed physical output as a terminal display."""

    passed = result.matches_source
    status = "PASS" if passed else "UNVERIFIED"
    rows = (
        _braille_rows(result.reconstructed_frame)
        if compact
        else _half_block_rows(result.reconstructed_frame)
    )
    width = len(rows[0])
    border_top = "┌" + "─" * width + "┐"
    border_bottom = "└" + "─" * width + "┘"
    display = [border_top, *("│" + row + "│" for row in rows), border_bottom]

    green = "\033[1;32m" if color else ""
    cyan = "\033[36m" if color else ""
    reset = "\033[0m" if color else ""
    summary = (
        f"128×32 / {FRAME_BYTES} bytes | PHASE {result.phases} | "
        f"CLK↑ {result.clock_rises} | LAT↑ {result.latches} | "
        f"GAP {result.gaps} | GRID✓ {result.grid_checks}"
    )
    pins = result.final_pins
    shutdown = (
        f"safe stop: BLANK={pins['BLANK']} HV={pins['HV']} EF={pins['EF']} | "
        f"events {result.pin_events} | HV pulse {result.hv_assertions}"
    )
    colored_display = [f"{cyan}{line}{reset}" for line in display]
    return "\n".join(
        [
            f"{green}DIGITAL TWIN: {status}{reset}",
            summary,
            shutdown,
            *colored_display,
        ]
    )


def _default_engine() -> str:
    configured = os.environ.get("MN12832L_SYSTEM_TWIN")
    if configured:
        return configured
    return str(Path(__file__).resolve().parents[2] / "build" / "vfd_system_twin")


def _render_demo(text: str) -> bytes:
    canvas = Image.new("1", (FRAME_WIDTH, FRAME_HEIGHT), 0)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.rectangle((0, 0, FRAME_WIDTH - 1, FRAME_HEIGHT - 1), outline=1)
    draw.text((3, 3), text[:20], font=font, fill=1)
    draw.line((3, 16, FRAME_WIDTH - 4, 16), fill=1)
    draw.text((3, 19), "PIN TWIN", font=font, fill=1)
    renderer = MvlsbRenderer()
    renderer.load_image(canvas)
    return renderer.snapshot()


def border_loader_position(step: int) -> Tuple[int, int]:
    """Return the wrapped outer-edge pixel for one animation step."""

    position = step % BORDER_PERIMETER_PIXELS
    if position < FRAME_WIDTH:
        return position, 0

    position -= FRAME_WIDTH
    if position < FRAME_HEIGHT - 1:
        return FRAME_WIDTH - 1, position + 1

    position -= FRAME_HEIGHT - 1
    if position < FRAME_WIDTH - 1:
        return FRAME_WIDTH - 2 - position, FRAME_HEIGHT - 1

    position -= FRAME_WIDTH - 1
    return 0, FRAME_HEIGHT - 2 - position


@lru_cache(maxsize=8)
def load_ascii_art_asset(
    name: str = DEFAULT_ASCII_ART_ASSET,
) -> Tuple[str, ...]:
    """Load and validate a packaged ``#``/``.`` monochrome art asset."""

    if not name or Path(name).name != name:
        raise ValueError("ASCII art asset name must be a plain file name")
    asset_path = resources.files(__package__).joinpath("assets").joinpath(name)
    rows = tuple(
        line.strip()
        for line in asset_path.read_text(encoding="ascii").splitlines()
        if line.strip()
    )
    if not rows or not rows[0]:
        raise ValueError(f"ASCII art asset {name!r} is empty")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError(f"ASCII art asset {name!r} is not rectangular")
    if set("".join(rows)) - {"#", "."}:
        raise ValueError(f"ASCII art asset {name!r} contains unsupported pixels")
    return rows


def _draw_ascii_art(
    draw: ImageDraw.ImageDraw,
    rows: Sequence[str],
    *,
    origin_x: int,
    origin_y: int,
    scale: int,
) -> None:
    for row_index, row in enumerate(rows):
        for column_index, pixel in enumerate(row):
            if pixel != "#":
                continue
            left = origin_x + column_index * scale
            top = origin_y + row_index * scale
            draw.rectangle(
                (left, top, left + scale - 1, top + scale - 1),
                fill=1,
            )


def render_border_loader_frame(step: int) -> bytes:
    """Render packaged ASCII art, a scan bar, and a clockwise border comet."""

    canvas = Image.new("1", (FRAME_WIDTH, FRAME_HEIGHT), 0)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, FRAME_WIDTH - 1, FRAME_HEIGHT - 1), outline=1)

    asset = load_ascii_art_asset()
    asset_scale = 2
    asset_width = len(asset[0]) * asset_scale
    _draw_ascii_art(
        draw,
        asset,
        origin_x=(FRAME_WIDTH - asset_width) // 2,
        origin_y=6,
        scale=asset_scale,
    )

    bar_left = 20
    bar_right = FRAME_WIDTH - 21
    bar_top = 24
    bar_bottom = 29
    draw.rectangle((bar_left, bar_top, bar_right, bar_bottom), outline=1)
    inner_left = bar_left + 1
    inner_width = bar_right - bar_left - 1
    for offset in range(18):
        x = inner_left + (step + offset) % inner_width
        draw.line((x, bar_top + 2, x, bar_bottom - 2), fill=1)

    for offset, radius in ((12, 0), (8, 1), (4, 1), (0, 2)):
        x, y = border_loader_position(step - offset)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=1,
        )

    renderer = MvlsbRenderer()
    renderer.load_image(canvas)
    return renderer.snapshot()


def _render_image(path: str) -> bytes:
    with Image.open(path) as source:
        image = source.convert("1")
        image.thumbnail((FRAME_WIDTH, FRAME_HEIGHT))
        canvas = Image.new("1", (FRAME_WIDTH, FRAME_HEIGHT), 0)
        origin = (
            (FRAME_WIDTH - image.width) // 2,
            (FRAME_HEIGHT - image.height) // 2,
        )
        canvas.paste(image, origin)
    renderer = MvlsbRenderer()
    renderer.load_image(canvas)
    return renderer.snapshot()


def _animate_border_loader(
    engine: str,
    *,
    frames: int,
    fps: float,
    step_pixels: int,
    color: bool,
    compact: bool,
    stream: Optional[TextIO] = None,
) -> int:
    interval = 1.0 / fps
    next_frame_at = time.monotonic()
    output = stream if stream is not None else sys.stdout
    interactive = output.isatty()
    transport = DigitalTwinTransport([engine], timeout=5.0)
    display = VfdDisplay(transport)

    if interactive:
        output.write("\033[?25l\033[2J")
    try:
        with display:
            for frame_index in range(frames):
                step = frame_index * step_pixels
                frame = render_border_loader_frame(step)
                display.present(frame)
                result = transport.last_result
                if result is None:
                    raise DigitalTwinError(
                        "accepted frame produced no system-twin pin trace"
                    )
                x, y = border_loader_position(step)
                if interactive:
                    output.write("\033[H\033[J")
                elif frame_index:
                    output.write("\n")
                output.write(
                    "source: Raspberry Pi stack → C system twin | "
                    f"frame {frame_index + 1}/{frames} | edge pixel ({x}, {y})\n"
                )
                output.write(
                    render_tui(result, color=color, compact=compact) + "\n"
                )
                output.flush()

                next_frame_at += interval
                if frame_index + 1 < frames:
                    delay = next_frame_at - time.monotonic()
                    if delay > 0:
                        time.sleep(delay)
    except KeyboardInterrupt:
        return 130
    finally:
        if interactive:
            output.write("\033[?25h")
            output.flush()
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point for an inspectable terminal digital twin."""

    parser = argparse.ArgumentParser(
        description="Render MN12832L frames through virtual STM32 pins"
    )
    parser.add_argument("--engine", default=_default_engine())
    parser.add_argument("--text", default="MN12832L")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--image", help="center an image inside the 128x32 frame")
    source.add_argument(
        "--border-loader",
        action="store_true",
        help="animate a dot clockwise around the display outline",
    )
    parser.add_argument("--frames", type=int, default=80)
    parser.add_argument("--fps", type=float, default=20.0)
    parser.add_argument("--step-pixels", type=int, default=4)
    parser.add_argument("--compact", action="store_true", help="use 64x8 Braille output")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args(argv)

    if args.border_loader:
        if args.frames <= 0:
            parser.error("--frames must be greater than zero")
        if args.fps <= 0:
            parser.error("--fps must be greater than zero")
        if args.step_pixels <= 0:
            parser.error("--step-pixels must be greater than zero")

    try:
        if args.border_loader:
            return _animate_border_loader(
                args.engine,
                frames=args.frames,
                fps=args.fps,
                step_pixels=args.step_pixels,
                color=not args.no_color,
                compact=args.compact,
            )
        frame = _render_image(args.image) if args.image else _render_demo(args.text)
        transport = DigitalTwinTransport([args.engine], timeout=5.0)
        display = VfdDisplay(transport)
        with display:
            display.present(frame)
            result = transport.last_result
        if result is None:
            raise DigitalTwinError(
                "accepted frame produced no system-twin pin trace"
            )
    except (
        DigitalTwinError,
        DisplayError,
        OSError,
        TransportError,
        ValueError,
    ) as error:
        parser.exit(2, f"digital twin failed: {error}\n")

    source_label = f'image "{args.image}"' if args.image else f'text "{args.text}"'
    print(f"source: {source_label}")
    print(render_tui(result, color=not args.no_color, compact=args.compact))
    return 0


if __name__ == "__main__":
    sys.exit(main())
