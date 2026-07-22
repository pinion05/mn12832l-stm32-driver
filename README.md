# MN12832L STM32 Driver Hardening Workspace

This repository preserves and hardens the supplied source bundle for the
AliExpress GU128x32D/MN12832L 128x32 VFD module (item `1005003334875219`).
The untouched download remains at `/Users/pinion/Downloads/Plopydisk  men` and
is fingerprinted by `ORIGINAL_SHA256SUMS.txt`.

See [`ANALYSIS.md`](ANALYSIS.md) for the Korean protocol, defect, and residual-risk
report.

Beginner-friendly visual report:

- [`reports/mn12832l-improvement-report.html`](reports/mn12832l-improvement-report.html)
- [`reports/mn12832l-improvement-report.pdf`](reports/mn12832l-improvement-report.pdf)

## Status

**Host-verified driver core; not yet hardware-qualified firmware.**

The framebuffer blitters, 43-phase scan packer, 240-bit emitter, phase/HV state,
interrupt handoff contract, fault shutdown contract, and empirical delay code
generation are automated. The Raspberry Pi host package now covers model
rendering, native 512-byte MVLSB frames, CRC-framed transfer, persistent bridge
lifecycle, ACK/retry handling, and unchanged-frame suppression. The STM32 host
link validates packets and swaps its double buffer only at the 43 → 1 scan
boundary.

A fake HAL checks the board glue with strict warnings, but it does not replace
an exact STM32CubeF0 SDK, an on-target build, or the final UART/USB peripheral
binding.

## End-to-end software cycle

```text
high-level Python model
        ↓
Pillow or Adafruit framebuf rendering
        ↓
512-byte MVLSB frame
        ↓
VfdDisplay: deduplicate + sequence + CRC + retry
        ↓
persistent mn12832l-serial-bridge child process
        ↓
STM32 VfdHostLink: validate + backpressure + back buffer
        ↓  phase 43 → 1
atomic front/back swap
        ↓
tested VFD scan packer and pin emitter
```

The byte-level contract is documented in
[`docs/HOST_PROTOCOL.md`](docs/HOST_PROTOCOL.md).

## Pin-level digital twin (no display required)

The digital twin does not print the source image directly. It sends the real
512-byte frame through the production C scan packer/emitter, replaces the six
STM32 GPIO outputs (`SIN`, `CLK`, `LAT`, `BLANK`, `EF`, and `HV`) with virtual
pins, and reconstructs the image only from those pin events. A mismatch or an
unsafe control-pin sequence fails instead of drawing a false success screen.

```sh
# Full-width 128-column terminal view
make twin PYTHON=.venv/bin/python

# A 64-column compact view that is easier to see over SSH
make twin PYTHON=.venv/bin/python \
  TWIN_ARGS='--text "HELLO VFD" --compact --no-color'

# Test a real image (scaled to fit 128x32)
make twin PYTHON=.venv/bin/python \
  TWIN_ARGS='--image ./logo.png --compact'

# Animate a verified dot around the 128x32 outer edge
make twin PYTHON=.venv/bin/python \
  TWIN_ARGS='--border-loader --compact --frames 160 --fps 20'
```

The loader rasterizes the packaged `assets/loading_wordmark.txt` ASCII art,
adds a wrapped scan bar and border comet, then verifies every animated frame
through the C pin twin before drawing it.

A successful run reports `DIGITAL TWIN: PASS`, 43 phases, 10,320 rising clock
edges, 43 latches, 43 pixel/grid gaps, and safe final control-pin levels. See
[`docs/DIGITAL_TWIN.md`](docs/DIGITAL_TWIN.md) for the interface and limitations.

### Raspberry Pi installation

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[serial]'
```

### Persistent Python use

```python
import sys

from PIL import Image, ImageDraw, ImageFont

from mn12832l import MvlsbRenderer, SubprocessTransport, VfdDisplay

transport = SubprocessTransport([
    sys.executable,
    "-m",
    "mn12832l.serial_bridge",
    "--port",
    "/dev/ttyACM0",
    "--baud",
    "115200",
])
renderer = MvlsbRenderer()
image = Image.new("1", (128, 32), 0)
ImageDraw.Draw(image).text(
    (0, 0), "HELLO", font=ImageFont.load_default(), fill=1
)
renderer.load_image(image)

with VfdDisplay(transport, renderer=renderer) as display:
    display.present(renderer.snapshot())
```

For Korean text, replace `ImageFont.load_default()` with a Korean TrueType font.
Adafruit `framebuffer.text()` also works when its required binary font file is
passed via `font_name`; its drawing primitives need no external font file.

## Module-to-MCU mapping recovered from the supplied code

| Module header | STM32 pin | Role in this workspace |
| --- | --- | --- |
| `SIN` | `PA1` | Serial pixel/grid data |
| `CLK` | `PA2` | Shift clock |
| `LAT` | `PA3` | Output latch |
| `BLK` | `PA4` | Active-high blank/fail-safe output |
| `EF` | `PF0` | Filament/converter enable control |
| `HV` | `PF1` | High-voltage enable pulse control |
| `SO1`, `SO2` | — | Not used by the supplied STM32 path |
| `GND`, `5V` | board power | Verify current and logic levels before connection |

The `HV` and `EF` interpretations are based on the module silkscreen and supplied
firmware. Do not assume their voltage tolerance, polarity, or safe timing from
the names alone.

## Supported STM32 source set

- `main.c`, `main.h`: board sequencing, fail-safe GPIO state, timer handoff.
- `stm32f0xx_it.c/.h`, `stm32f0xx_hal_msp.c`: TIM14 and fault glue.
- `GT20L_Font.c/.h`: clipped framebuffer blitters.
- `vfd_host_link.c/.h`: fixed frame protocol, CRC, idempotent ACKs, and
  scan-boundary double buffering.
- `vfd_scan.c/.h`: tested scan packing, emission, and phase/HV state.
- `vfd_delay.c/.h`: non-optimizable empirical delay loops.
- `vfd_framebuffer.c`, `font.c`, `demo_fonts.h`: supplied demonstration data.
- `system_stm32f0xx.c`: supplied ST CMSIS system file; vendor-owned and excluded
  from local Semgrep rules until the exact MCU package is restored.

`firmware/stm32f0/legacy/unsupported/` retains duplicate/incompatible supplied
sources but is deliberately not part of the supported build set.

The nested Arduino library is kept under `reference/arduino/` only for protocol
comparison. It targets a raw-panel/GCP arrangement and is not a drop-in driver
for this converter-board header.

## Verification

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
make clean all PYTHON=.venv/bin/python
PATH="$HOME/.qlty/bin:$PATH" QLTY_NO_UPDATE_CHECK=1 CI=1 \
  qlty check --all --no-progress --summary
```

The gates include:

- UBSan font clipping and production `8x16 @ y=13` rendering tests.
- All 43 phases × all 32 rows odd/even lane-mapping properties.
- Exact 192-pixel-bit + 48-grid-bit MSB-first emission and protocol-gap test.
- Pin-level C/Python digital-twin round trip for all 512 framebuffer bytes,
  including 10,320 clocks, 43 blanked latches, grid selectors, and safe stop.
- Python/C CRC golden vector, fixed packet layout, ACK validation, retry, and
  persistent-child integration tests.
- STM32 CRC rejection, noise resynchronization, duplicate-sequence idempotency,
  busy backpressure, and boundary-only double-buffer swap tests.
- Phase wrap and supplied one-timer-interval HV-pulse state test.
- Cortex-M0 `-O2` assembly check for a `nop` and loop back-edge in every delay.
- `-Werror` host builds for the pure core and fake-HAL board glue.
- Clang static analyzer, Semgrep policy rules, and verified-secret scanning.
- Source contracts for atomic IRQ handoff, production packer integration, safe
  GPIO preload, and Error/NMI/HardFault shutdown.

## Required before flashing hardware

1. Identify the exact STM32F0 part and board revision.
2. Restore matching CMSIS/HAL headers and sources, startup assembly, linker
   script, device define, programmer settings, and a real target build system.
3. Confirm 5 V current capacity and every logic level with the seller schematic
   or measurements on a current-limited bench supply.
4. Verify `BLK`, `LAT`, `EF`, and `HV` polarity and the four historical delay
   durations with an oscilloscope/logic analyzer.
5. Confirm the HV duty cycle and display refresh before extended operation.
6. Select and configure the actual UART or USB CDC peripheral, feed its queued
   bytes to `VFD_HostProcessByte()`, and transmit each returned ACK.

No hardware, electrical, or production-readiness claim is made until those six
steps pass.
