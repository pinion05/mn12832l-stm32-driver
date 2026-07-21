# MN12832L STM32 Driver Hardening Workspace

This repository preserves and hardens the supplied source bundle for the
AliExpress GU128x32D/MN12832L 128x32 VFD module (item `1005003334875219`).
The untouched download remains at `/Users/pinion/Downloads/Plopydisk  men` and
is fingerprinted by `ORIGINAL_SHA256SUMS.txt`.

See [`ANALYSIS.md`](ANALYSIS.md) for the Korean protocol, defect, and residual-risk
report.

## Status

**Host-verified driver core; not yet hardware-qualified firmware.**

The framebuffer blitters, 43-phase scan packer, 240-bit emitter, phase/HV state,
interrupt handoff contract, fault shutdown contract, and empirical delay code
generation are automated. A fake HAL checks the board glue with strict warnings,
but it does not replace an exact STM32CubeF0 SDK or an on-target build.

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
make clean all
PATH="$HOME/.qlty/bin:$PATH" QLTY_NO_UPDATE_CHECK=1 CI=1 \
  qlty check --all --no-progress --summary
```

The gates include:

- UBSan font clipping and production `8x16 @ y=13` rendering tests.
- All 43 phases × all 32 rows odd/even lane-mapping properties.
- Exact 192-pixel-bit + 48-grid-bit MSB-first emission and protocol-gap test.
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

No hardware, electrical, or production-readiness claim is made until those five
steps pass.
