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
#define VFD_HV_PULSE_TICKS 2u

typedef struct {
    uint8_t phase;
    uint8_t hv_ticks_remaining;
    bool hv_enabled;
} VfdScanState;

typedef void (*VfdScanBitWriter)(bool bit, void *context);
typedef void (*VfdScanGapHook)(void *context);

/*
 * Packs one 1-based scan phase exactly as the supplied bit-banged firmware:
 * 192 pixel bits first, followed by the 48-bit neighboring-grid selector.
 */
bool vfd_scan_pack_step(
    const uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH],
    uint8_t phase,
    uint8_t frame[VFD_SCAN_FRAME_BYTES]);

/* Preserves the supplied one-timer-interval HV pulse at each frame boundary. */
void vfd_scan_state_init(VfdScanState *state);
void vfd_scan_state_advance(VfdScanState *state);

/* Emits all 240 bits MSB-first and invokes the gap hook after bit 192. */
bool vfd_scan_emit_frame(
    const uint8_t frame[VFD_SCAN_FRAME_BYTES],
    VfdScanBitWriter write_bit,
    VfdScanGapHook pixel_grid_gap,
    void *context);

#endif
