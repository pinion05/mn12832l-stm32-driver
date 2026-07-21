#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "vfd_scan.h"

enum TwinEvent {
    TWIN_EVENT_PHASE = 1,
    TWIN_EVENT_SIN = 2,
    TWIN_EVENT_CLK = 3,
    TWIN_EVENT_GAP = 4,
    TWIN_EVENT_BLANK = 5,
    TWIN_EVENT_LAT = 6,
    TWIN_EVENT_EF = 7,
    TWIN_EVENT_HV = 8,
    TWIN_EVENT_END = 9,
};

typedef struct {
    FILE *stream;
    bool failed;
} TwinPins;

static void twin_emit(TwinPins *pins, enum TwinEvent event, uint8_t value)
{
    const uint8_t record[2] = {(uint8_t)event, value};

    if (pins->failed || fwrite(record, 1u, sizeof(record), pins->stream) !=
                            sizeof(record)) {
        pins->failed = true;
    }
}

static void twin_write_scan_bit(bool bit, void *context)
{
    TwinPins *pins = context;

    /* This is the virtual equivalent of PA1 plus one PA2 clock pulse. */
    twin_emit(pins, TWIN_EVENT_SIN, bit ? 1u : 0u);
    twin_emit(pins, TWIN_EVENT_CLK, 0u);
    twin_emit(pins, TWIN_EVENT_CLK, 1u);
}

static void twin_pixel_grid_gap(void *context)
{
    TwinPins *pins = context;

    twin_emit(pins, TWIN_EVENT_GAP, (uint8_t)VFD_PIXEL_BITS_PER_PHASE);
}

static bool twin_read_frame(
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH])
{
    const size_t expected = VFD_PAGE_COUNT * VFD_WIDTH;
    const size_t received = fread(framebuffer, 1u, expected, stdin);

    if (received != expected || ferror(stdin) != 0) {
        return false;
    }

    return fgetc(stdin) == EOF;
}

int main(void)
{
    static const uint8_t header[8] = {
        'V', 'F', 'D', 'T', 'P', 'I', 'N', '1',
    };
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t scan_frame[VFD_SCAN_FRAME_BYTES];
    VfdScanState state;
    TwinPins pins = {stdout, false};

    if (!twin_read_frame(framebuffer)) {
        fputs("expected exactly one 512-byte MVLSB frame on stdin\n", stderr);
        return 2;
    }

    if (fwrite(header, 1u, sizeof(header), stdout) != sizeof(header)) {
        return 3;
    }

    /* Power-on fail-safe levels, followed by the converter enable. */
    twin_emit(&pins, TWIN_EVENT_SIN, 0u);
    twin_emit(&pins, TWIN_EVENT_CLK, 0u);
    twin_emit(&pins, TWIN_EVENT_LAT, 0u);
    twin_emit(&pins, TWIN_EVENT_BLANK, 1u);
    twin_emit(&pins, TWIN_EVENT_EF, 0u);
    twin_emit(&pins, TWIN_EVENT_HV, 0u);
    twin_emit(&pins, TWIN_EVENT_EF, 1u);

    vfd_scan_state_init(&state);
    for (uint8_t completed = 0u; completed < VFD_SCAN_PHASES; ++completed) {
        twin_emit(&pins, TWIN_EVENT_PHASE, state.phase);
        if (!vfd_scan_pack_step(framebuffer, state.phase, scan_frame) ||
            !vfd_scan_emit_frame(scan_frame, twin_write_scan_bit,
                                 twin_pixel_grid_gap, &pins)) {
            fputs("production scan core rejected a digital-twin phase\n", stderr);
            return 4;
        }

        /* The virtual shift register becomes visible only on LAT while blank. */
        twin_emit(&pins, TWIN_EVENT_BLANK, 1u);
        twin_emit(&pins, TWIN_EVENT_LAT, 1u);
        twin_emit(&pins, TWIN_EVENT_LAT, 0u);
        twin_emit(&pins, TWIN_EVENT_BLANK, 0u);

        vfd_scan_state_advance(&state);
        twin_emit(&pins, TWIN_EVENT_HV, state.hv_enabled ? 1u : 0u);
    }

    /* Model the production fail-safe shutdown order before terminating. */
    twin_emit(&pins, TWIN_EVENT_BLANK, 1u);
    twin_emit(&pins, TWIN_EVENT_HV, 0u);
    twin_emit(&pins, TWIN_EVENT_EF, 0u);
    twin_emit(&pins, TWIN_EVENT_END, 0u);

    if (pins.failed || fflush(stdout) != 0) {
        return 5;
    }

    return 0;
}
