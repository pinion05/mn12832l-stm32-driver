#ifndef VFD_SCAN_H
#define VFD_SCAN_H

#include <stdbool.h>
#include <stdint.h>

#define VFD_WIDTH 128u
#define VFD_HEIGHT 32u
#define VFD_PAGE_COUNT 4u
#define VFD_SCAN_PHASES 43u
#define VFD_PIXEL_BITS_PER_PHASE 192u
#define VFD_GRID_BITS_PER_PHASE 48u
#define VFD_SCAN_FRAME_BYTES 30u

/*
 * Packs one 1-based scan phase exactly as the supplied bit-banged firmware:
 * 192 pixel bits first, followed by the 48-bit neighboring-grid selector.
 */
bool vfd_scan_pack_step(
    const uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH],
    uint8_t phase,
    uint8_t frame[VFD_SCAN_FRAME_BYTES]);

#endif
