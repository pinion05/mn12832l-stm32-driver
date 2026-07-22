#include "vfd_pin_trace.h"

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
    size_t events;
    bool failed;
} TwinPins;

_Static_assert(VFD_PIN_TRACE_EVENTS_PER_FRAME == 31272u,
               "pin trace event count changed unexpectedly");

static void twin_emit(TwinPins *pins, enum TwinEvent event, uint8_t value)
{
    const uint8_t record[2] = {(uint8_t)event, value};

    if (pins->failed || fwrite(record, 1u, sizeof(record), pins->stream) !=
                            sizeof(record)) {
        pins->failed = true;
    } else {
        ++pins->events;
    }
}

static void twin_write_scan_bit(bool bit, void *context)
{
    TwinPins *pins = context;

    twin_emit(pins, TWIN_EVENT_SIN, bit ? 1u : 0u);
    twin_emit(pins, TWIN_EVENT_CLK, 0u);
    twin_emit(pins, TWIN_EVENT_CLK, 1u);
}

static void twin_pixel_grid_gap(void *context)
{
    TwinPins *pins = context;

    twin_emit(pins, TWIN_EVENT_GAP, (uint8_t)VFD_PIXEL_BITS_PER_PHASE);
}

bool vfd_pin_trace_write(
    FILE *stream,
    const uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH])
{
    static const uint8_t header[8] = {
        'V', 'F', 'D', 'T', 'P', 'I', 'N', '1',
    };
    uint8_t scan_frame[VFD_SCAN_FRAME_BYTES];
    VfdScanState state;
    TwinPins pins = {stream, 0u, false};

    if (stream == NULL || framebuffer == NULL ||
        fwrite(header, 1u, sizeof(header), stream) != sizeof(header)) {
        return false;
    }

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
            return false;
        }

        twin_emit(&pins, TWIN_EVENT_BLANK, 1u);
        twin_emit(&pins, TWIN_EVENT_LAT, 1u);
        twin_emit(&pins, TWIN_EVENT_LAT, 0u);
        twin_emit(&pins, TWIN_EVENT_BLANK, 0u);

        vfd_scan_state_advance(&state);
        twin_emit(&pins, TWIN_EVENT_HV, state.hv_enabled ? 1u : 0u);
    }

    twin_emit(&pins, TWIN_EVENT_BLANK, 1u);
    twin_emit(&pins, TWIN_EVENT_HV, 0u);
    twin_emit(&pins, TWIN_EVENT_EF, 0u);
    twin_emit(&pins, TWIN_EVENT_END, 0u);
    return !pins.failed && ferror(stream) == 0 &&
           pins.events == VFD_PIN_TRACE_EVENTS_PER_FRAME;
}
