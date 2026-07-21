# Unsupported supplied sources

These files are preserved for provenance but are intentionally excluded from the
hardened firmware source set:

- `VFD_Font.c` duplicates the four public framebuffer blitters in `GT20L_Font.c`.
- `drv_font.c` and `inf_font.c` form an incomplete STM32F4 Standard Peripheral
  Library path, require missing headers, and conflict with the STM32F0 HAL target
  and the active PA4/BLK pin assignment.

They are not part of the host verification gates or the documented target source
manifest. The untouched download remains available through the hashes at the
repository root.
