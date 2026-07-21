#ifndef VFD_HOST_LINK_H
#define VFD_HOST_LINK_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "vfd_scan.h"

#define VFD_HOST_MAGIC_0 0x56u
#define VFD_HOST_MAGIC_1 0x46u
#define VFD_HOST_PROTOCOL_VERSION 1u
#define VFD_HOST_COMMAND_FRAME 0x01u
#define VFD_HOST_COMMAND_ACK 0x80u
#define VFD_HOST_FRAME_HEADER_BYTES 8u
#define VFD_HOST_CRC_BYTES 2u
#define VFD_HOST_FRAME_BYTES (VFD_PAGE_COUNT * VFD_WIDTH)
#define VFD_HOST_FRAME_PACKET_BYTES                                            \
    (VFD_HOST_FRAME_HEADER_BYTES + VFD_HOST_FRAME_BYTES + VFD_HOST_CRC_BYTES)
#define VFD_HOST_ACK_PACKET_BYTES 9u

typedef enum {
    VFD_HOST_ACK_OK = 0,
    VFD_HOST_ACK_CRC_ERROR = 1,
    VFD_HOST_ACK_VERSION_ERROR = 2,
    VFD_HOST_ACK_COMMAND_ERROR = 3,
    VFD_HOST_ACK_LENGTH_ERROR = 4,
    VFD_HOST_ACK_BUSY = 5
} VfdHostAckStatus;

typedef struct {
    uint8_t buffers[2][VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t header[VFD_HOST_FRAME_HEADER_BYTES];
    uint16_t receive_count;
    uint16_t receive_crc;
    uint16_t wire_crc;
    uint16_t receive_sequence;
    uint16_t staged_sequence;
    uint16_t displayed_sequence;
    VfdHostAckStatus header_status;
    uint8_t receive_mode;
    uint8_t front_index;
    bool pending;
    bool has_displayed_sequence;
    bool receive_matches_existing;
} VfdHostLink;

/* Initialize the front buffer from initial_frame, or to black when NULL. */
void vfd_host_link_init(
    VfdHostLink *link,
    const uint8_t initial_frame[VFD_PAGE_COUNT][VFD_WIDTH]);

/*
 * Feed one byte from a main-loop-owned UART/USB receive queue.
 * Returns true exactly when ack_out contains one complete ACK/NACK packet.
 */
bool vfd_host_link_feed(
    VfdHostLink *link,
    uint8_t byte,
    uint8_t ack_out[VFD_HOST_ACK_PACKET_BYTES]);

/* Stable scan source. The pointer changes only after swap_if_pending(). */
const uint8_t (*vfd_host_link_front(const VfdHostLink *link))[VFD_WIDTH];

/* Call only at the 43 -> 1 scan boundary to make a received frame visible. */
bool vfd_host_link_swap_if_pending(
    VfdHostLink *link, uint16_t *displayed_sequence);

bool vfd_host_link_has_pending(const VfdHostLink *link);

/* CRC-16/CCITT-FALSE, shared with the Python host protocol. */
uint16_t vfd_host_link_crc16(const uint8_t *data, size_t size);

#endif
