# Hardening plan

## Target result

Produce a host-testable, statically checked board-driver core while preserving the
supplied hardware scan order and explicitly separating unsupported/orphan code.

## Locked behavior before edits

1. Framebuffer layout is 128 x 32 monochrome pixels in four vertical 8-pixel pages.
2. One scan step emits 192 pixel bits followed by a 48-bit grid selector.
3. The active display uses 43 scan phases and two neighboring grid bits.
4. Odd/even phases retain the supplied six-bit pixel ordering.
5. Font blits clip at the 128 x 32 framebuffer boundary.

## First-pass defect scope

- ISR/main visibility and event handling.
- Buffer bounds and non-void return paths.
- Deterministic, non-optimizable delay primitives without changing empirical constants.
- Duplicate/orphan source separation.
- Host regression tests for scan packing and font clipping.
- Warning-clean host builds and Clang static analysis.

## Out of scope without hardware evidence

- Changing HV/EF duty cycle or polarity.
- Changing the empirical latch/blank timing constants.
- Selecting an exact STM32F0 part, linker script, startup file, or programmer setup.
- Claiming electrical or production readiness.
