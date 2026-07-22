#ifndef VFD_PIN_TRACE_H
#define VFD_PIN_TRACE_H

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "vfd_scan.h"

#define VFD_PIN_TRACE_HEADER_BYTES 8u
#define VFD_PIN_TRACE_EVENTS_PER_FRAME                                      \
    (7u + VFD_SCAN_PHASES *                                                  \
              (1u + 3u * (VFD_PIXEL_BITS_PER_PHASE + VFD_GRID_BITS_PER_PHASE) + \
               1u + 4u + 1u) +                                              \
     4u)

/* Emit one complete, self-validating virtual-pin scan trace. */
bool vfd_pin_trace_write(
    FILE *stream,
    const uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH]);

#endif
