#include "vfd_host_link.h"

#include <string.h>

enum {
    RECEIVE_MODE_DISCARD = 0,
    RECEIVE_MODE_WRITE = 1,
    RECEIVE_MODE_COMPARE_PENDING = 2,
    RECEIVE_MODE_BUSY = 3
};

_Static_assert(VFD_HOST_FRAME_BYTES == 512u,
               "host protocol requires a 512-byte logical frame");
_Static_assert(VFD_HOST_FRAME_PACKET_BYTES == 522u,
               "host frame packet size changed unexpectedly");
_Static_assert(VFD_HOST_ACK_PACKET_BYTES == 9u,
               "host ACK packet size changed unexpectedly");
_Static_assert(sizeof(VfdHostLink) <= 1080u,
               "host link unexpectedly exceeds its RAM budget");

static uint16_t crc16_update(uint16_t crc, uint8_t byte)
{
    unsigned int bit;

    crc = (uint16_t)(crc ^ (uint16_t)((uint16_t)byte << 8u));
    for (bit = 0u; bit < 8u; ++bit) {
        if ((crc & 0x8000u) != 0u) {
            crc = (uint16_t)((uint16_t)(crc << 1u) ^ 0x1021u);
        } else {
            crc = (uint16_t)(crc << 1u);
        }
    }
    return crc;
}

uint16_t vfd_host_link_crc16(const uint8_t *data, size_t size)
{
    uint16_t crc = 0xffffu;
    size_t index;

    if (data == NULL && size != 0u) {
        return 0u;
    }
    for (index = 0u; index < size; ++index) {
        crc = crc16_update(crc, data[index]);
    }
    return crc;
}

static void receiver_reset(VfdHostLink *link)
{
    link->receive_count = 0u;
    link->receive_crc = 0xffffu;
    link->wire_crc = 0u;
    link->receive_sequence = 0u;
    link->header_status = VFD_HOST_ACK_OK;
    link->receive_mode = RECEIVE_MODE_DISCARD;
    link->receive_matches_existing = false;
}

void vfd_host_link_init(
    VfdHostLink *link,
    const uint8_t initial_frame[VFD_PAGE_COUNT][VFD_WIDTH])
{
    if (link == NULL) {
        return;
    }

    memset(link, 0, sizeof(*link));
    if (initial_frame != NULL) {
        memcpy(link->buffers[0], initial_frame, VFD_HOST_FRAME_BYTES);
    }
    receiver_reset(link);
}

static void configure_receive(VfdHostLink *link)
{
    const uint16_t payload_length =
        (uint16_t)link->header[6] |
        (uint16_t)((uint16_t)link->header[7] << 8u);

    link->receive_sequence =
        (uint16_t)link->header[4] |
        (uint16_t)((uint16_t)link->header[5] << 8u);

    if (link->header[2] != VFD_HOST_PROTOCOL_VERSION) {
        link->header_status = VFD_HOST_ACK_VERSION_ERROR;
        return;
    }
    if (link->header[3] != VFD_HOST_COMMAND_FRAME) {
        link->header_status = VFD_HOST_ACK_COMMAND_ERROR;
        return;
    }
    if (payload_length != VFD_HOST_FRAME_BYTES) {
        link->header_status = VFD_HOST_ACK_LENGTH_ERROR;
        return;
    }

    if (link->pending) {
        if (link->receive_sequence == link->staged_sequence) {
            link->receive_mode = RECEIVE_MODE_COMPARE_PENDING;
            link->receive_matches_existing = true;
        } else {
            link->receive_mode = RECEIVE_MODE_BUSY;
        }
    } else {
        link->receive_mode = RECEIVE_MODE_WRITE;
        link->receive_matches_existing =
            link->has_displayed_sequence &&
            link->receive_sequence == link->displayed_sequence;
    }
}

static void encode_ack(
    uint16_t sequence,
    VfdHostAckStatus status,
    uint8_t ack_out[VFD_HOST_ACK_PACKET_BYTES])
{
    uint16_t crc;

    ack_out[0] = VFD_HOST_MAGIC_0;
    ack_out[1] = VFD_HOST_MAGIC_1;
    ack_out[2] = VFD_HOST_PROTOCOL_VERSION;
    ack_out[3] = VFD_HOST_COMMAND_ACK;
    ack_out[4] = (uint8_t)(sequence & 0xffu);
    ack_out[5] = (uint8_t)(sequence >> 8u);
    ack_out[6] = (uint8_t)status;
    crc = vfd_host_link_crc16(
        ack_out, VFD_HOST_ACK_PACKET_BYTES - VFD_HOST_CRC_BYTES);
    ack_out[7] = (uint8_t)(crc & 0xffu);
    ack_out[8] = (uint8_t)(crc >> 8u);
}

static VfdHostAckStatus finish_packet(VfdHostLink *link)
{
    if (link->wire_crc != link->receive_crc) {
        return VFD_HOST_ACK_CRC_ERROR;
    }
    if (link->header_status != VFD_HOST_ACK_OK) {
        return link->header_status;
    }
    if (link->receive_mode == RECEIVE_MODE_BUSY) {
        return VFD_HOST_ACK_BUSY;
    }
    if (link->receive_mode == RECEIVE_MODE_COMPARE_PENDING) {
        return link->receive_matches_existing ? VFD_HOST_ACK_OK
                                              : VFD_HOST_ACK_BUSY;
    }
    if (link->receive_mode == RECEIVE_MODE_WRITE) {
        if (link->receive_matches_existing) {
            return VFD_HOST_ACK_OK;
        }
        link->staged_sequence = link->receive_sequence;
        link->pending = true;
    }
    return VFD_HOST_ACK_OK;
}

bool vfd_host_link_feed(
    VfdHostLink *link,
    uint8_t byte,
    uint8_t ack_out[VFD_HOST_ACK_PACKET_BYTES])
{
    uint8_t *back_buffer;
    const uint8_t *front_buffer;
    uint16_t payload_index;
    VfdHostAckStatus status;

    if (link == NULL || ack_out == NULL) {
        return false;
    }

    if (link->receive_count == 0u) {
        if (byte != VFD_HOST_MAGIC_0) {
            return false;
        }
        link->header[0] = byte;
        link->receive_crc = crc16_update(0xffffu, byte);
        link->receive_count = 1u;
        return false;
    }

    if (link->receive_count == 1u && byte != VFD_HOST_MAGIC_1) {
        receiver_reset(link);
        if (byte == VFD_HOST_MAGIC_0) {
            link->header[0] = byte;
            link->receive_crc = crc16_update(0xffffu, byte);
            link->receive_count = 1u;
        }
        return false;
    }

    if (link->receive_count < VFD_HOST_FRAME_HEADER_BYTES) {
        link->header[link->receive_count] = byte;
        link->receive_crc = crc16_update(link->receive_crc, byte);
        ++link->receive_count;
        if (link->receive_count == VFD_HOST_FRAME_HEADER_BYTES) {
            configure_receive(link);
        }
        return false;
    }

    if (link->receive_count <
        VFD_HOST_FRAME_HEADER_BYTES + VFD_HOST_FRAME_BYTES) {
        payload_index =
            (uint16_t)(link->receive_count - VFD_HOST_FRAME_HEADER_BYTES);
        if (link->receive_mode == RECEIVE_MODE_WRITE) {
            back_buffer = &link->buffers[link->front_index ^ 1u][0][0];
            back_buffer[payload_index] = byte;
            front_buffer = &link->buffers[link->front_index][0][0];
            if (link->receive_matches_existing &&
                byte != front_buffer[payload_index]) {
                link->receive_matches_existing = false;
            }
        } else if (link->receive_mode == RECEIVE_MODE_COMPARE_PENDING) {
            back_buffer = &link->buffers[link->front_index ^ 1u][0][0];
            if (byte != back_buffer[payload_index]) {
                link->receive_matches_existing = false;
            }
        }
        link->receive_crc = crc16_update(link->receive_crc, byte);
        ++link->receive_count;
        return false;
    }

    if (link->receive_count ==
        VFD_HOST_FRAME_HEADER_BYTES + VFD_HOST_FRAME_BYTES) {
        link->wire_crc = byte;
        ++link->receive_count;
        return false;
    }

    link->wire_crc =
        (uint16_t)(link->wire_crc | (uint16_t)((uint16_t)byte << 8u));
    status = finish_packet(link);
    encode_ack(link->receive_sequence, status, ack_out);
    receiver_reset(link);
    return true;
}

const uint8_t (*vfd_host_link_front(const VfdHostLink *link))[VFD_WIDTH]
{
    if (link == NULL) {
        return NULL;
    }
    return link->buffers[link->front_index];
}

bool vfd_host_link_swap_if_pending(
    VfdHostLink *link, uint16_t *displayed_sequence)
{
    if (link == NULL || !link->pending) {
        return false;
    }

    link->front_index ^= 1u;
    link->pending = false;
    link->displayed_sequence = link->staged_sequence;
    link->has_displayed_sequence = true;
    if (displayed_sequence != NULL) {
        *displayed_sequence = link->displayed_sequence;
    }
    return true;
}

bool vfd_host_link_has_pending(const VfdHostLink *link)
{
    return link != NULL && link->pending;
}
