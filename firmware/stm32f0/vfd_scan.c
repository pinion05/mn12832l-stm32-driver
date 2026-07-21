#include "vfd_scan.h"

#include <stddef.h>
#include <string.h>

_Static_assert(VFD_PAGE_COUNT * 8u == VFD_HEIGHT,
               "framebuffer pages must cover the display height");
_Static_assert(VFD_PIXEL_BITS_PER_PHASE == VFD_HEIGHT * 6u,
               "each row must emit six pixel lanes");
_Static_assert(VFD_PIXEL_BITS_PER_PHASE + VFD_GRID_BITS_PER_PHASE ==
                   VFD_SCAN_FRAME_BYTES * 8u,
               "scan frame size must cover pixel and grid bits");
_Static_assert((VFD_SCAN_PHASES - 1u) * 3u + 2u == VFD_WIDTH,
               "the final two-column phase must end at column 127");

static void set_frame_bit(
    uint8_t frame[VFD_SCAN_FRAME_BYTES],
    size_t bit_index,
    bool value)
{
    if (value) {
        frame[bit_index / 8u] |= (uint8_t)(0x80u >> (bit_index % 8u));
    }
}

bool vfd_scan_pack_step(
    const uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH],
    uint8_t phase,
    uint8_t frame[VFD_SCAN_FRAME_BYTES])
{
    if (frame == NULL) {
        return false;
    }

    memset(frame, 0, VFD_SCAN_FRAME_BYTES);

    if (framebuffer == NULL || phase == 0u || phase > VFD_SCAN_PHASES) {
        return false;
    }

    const size_t column = ((size_t)phase - 1u) * 3u;
    size_t output_bit = 0;

    for (size_t row = 0; row < VFD_HEIGHT; ++row) {
        const size_t page = row / 8u;
        const uint8_t mask = (uint8_t)(1u << (row % 8u));
        const bool b1 = (framebuffer[page][column] & mask) != 0u;
        const bool b2 = (framebuffer[page][column + 1u] & mask) != 0u;
        const bool b3 = phase < VFD_SCAN_PHASES &&
                        (framebuffer[page][column + 2u] & mask) != 0u;
        const bool odd_phase = (phase & 1u) != 0u;
        const bool lanes[6] = {
            odd_phase ? b1 : false,
            odd_phase ? false : b3,
            odd_phase ? b2 : false,
            odd_phase ? false : b2,
            odd_phase ? b3 : false,
            odd_phase ? false : b1,
        };

        for (size_t lane = 0; lane < 6u; ++lane) {
            set_frame_bit(frame, output_bit, lanes[lane]);
            ++output_bit;
        }
    }

    for (size_t grid = 0; grid < VFD_GRID_BITS_PER_PHASE; ++grid) {
        const bool selected = grid == (size_t)phase - 1u || grid == (size_t)phase;
        set_frame_bit(frame, output_bit, selected);
        ++output_bit;
    }

    return output_bit == VFD_SCAN_FRAME_BYTES * 8u;
}

void vfd_scan_state_init(VfdScanState *state)
{
    if (state == NULL) {
        return;
    }

    state->phase = 1u;
    state->hv_ticks_remaining = 0u;
    state->hv_enabled = false;
}

void vfd_scan_state_advance(VfdScanState *state)
{
    if (state == NULL) {
        return;
    }

    ++state->phase;
    if (state->phase > VFD_SCAN_PHASES) {
        state->phase = 1u;
        state->hv_ticks_remaining = VFD_HV_PULSE_TICKS;
        state->hv_enabled = true;
    }

    if (state->hv_ticks_remaining > 0u) {
        --state->hv_ticks_remaining;
        if (state->hv_ticks_remaining == 0u) {
            state->hv_enabled = false;
        }
    }
}

bool vfd_scan_emit_frame(
    const uint8_t frame[VFD_SCAN_FRAME_BYTES],
    VfdScanBitWriter write_bit,
    VfdScanGapHook pixel_grid_gap,
    void *context)
{
    if (frame == NULL || write_bit == NULL || pixel_grid_gap == NULL) {
        return false;
    }

    for (size_t bit = 0; bit < VFD_SCAN_FRAME_BYTES * 8u; ++bit) {
        if (bit == VFD_PIXEL_BITS_PER_PHASE) {
            pixel_grid_gap(context);
        }

        const bool value =
            (frame[bit / 8u] & (uint8_t)(0x80u >> (bit % 8u))) != 0u;
        write_bit(value, context);
    }

    return true;
}
