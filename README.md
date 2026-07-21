# MN12832L STM32 Driver Hardening Workspace

This workspace preserves and hardens the source bundle supplied for the
AliExpress GU128x32D/MN12832L 128x32 VFD module.

- `firmware/stm32f0/`: supplied STM32 source snapshot; board-specific hardening target.
- `reference/arduino/`: MIT-licensed upstream Arduino reference, retained for protocol comparison.
- `ORIGINAL_SHA256SUMS.txt`: hashes of the untouched download bundle.

The original files under `/Users/pinion/Downloads/Plopydisk  men` are not modified.
Hardware operation is not claimed until the exact STM32 part, clock, power sequencing,
and board revision are validated on a current-limited bench setup.
