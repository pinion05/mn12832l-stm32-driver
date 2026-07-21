#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "vfd_host_link.h"

static int failures;

#define CHECK(condition)                                                       \
    do {                                                                       \
        if (!(condition)) {                                                    \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__,          \
                    #condition);                                               \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

static void fill_frame(uint8_t frame[VFD_PAGE_COUNT][VFD_WIDTH], uint8_t seed)
{
    size_t page;
    size_t column;

    for (page = 0u; page < VFD_PAGE_COUNT; ++page) {
        for (column = 0u; column < VFD_WIDTH; ++column) {
            frame[page][column] =
                (uint8_t)(seed + (uint8_t)(page * 17u) + (uint8_t)column);
        }
    }
}

static void build_frame_packet(
    const uint8_t frame[VFD_PAGE_COUNT][VFD_WIDTH],
    uint16_t sequence,
    uint8_t packet[VFD_HOST_FRAME_PACKET_BYTES])
{
    uint16_t crc;

    packet[0] = VFD_HOST_MAGIC_0;
    packet[1] = VFD_HOST_MAGIC_1;
    packet[2] = VFD_HOST_PROTOCOL_VERSION;
    packet[3] = VFD_HOST_COMMAND_FRAME;
    packet[4] = (uint8_t)(sequence & 0xffu);
    packet[5] = (uint8_t)(sequence >> 8u);
    packet[6] = (uint8_t)(VFD_HOST_FRAME_BYTES & 0xffu);
    packet[7] = (uint8_t)(VFD_HOST_FRAME_BYTES >> 8u);
    memcpy(&packet[VFD_HOST_FRAME_HEADER_BYTES], frame, VFD_HOST_FRAME_BYTES);
    crc = vfd_host_link_crc16(
        packet, VFD_HOST_FRAME_PACKET_BYTES - VFD_HOST_CRC_BYTES);
    packet[VFD_HOST_FRAME_PACKET_BYTES - 2u] = (uint8_t)(crc & 0xffu);
    packet[VFD_HOST_FRAME_PACKET_BYTES - 1u] = (uint8_t)(crc >> 8u);
}

static bool feed_bytes(
    VfdHostLink *link,
    const uint8_t *bytes,
    size_t size,
    uint8_t ack[VFD_HOST_ACK_PACKET_BYTES])
{
    bool produced = false;
    size_t index;

    for (index = 0u; index < size; ++index) {
        const bool current = vfd_host_link_feed(link, bytes[index], ack);
        CHECK(!produced || !current);
        produced = produced || current;
        if (index + 1u < size) {
            CHECK(!current);
        }
    }
    return produced;
}

static VfdHostAckStatus validate_ack(
    const uint8_t ack[VFD_HOST_ACK_PACKET_BYTES], uint16_t sequence)
{
    const uint16_t actual_crc = vfd_host_link_crc16(
        ack, VFD_HOST_ACK_PACKET_BYTES - VFD_HOST_CRC_BYTES);
    const uint16_t encoded_crc =
        (uint16_t)ack[VFD_HOST_ACK_PACKET_BYTES - 2u] |
        (uint16_t)((uint16_t)ack[VFD_HOST_ACK_PACKET_BYTES - 1u] << 8u);

    CHECK(ack[0] == VFD_HOST_MAGIC_0);
    CHECK(ack[1] == VFD_HOST_MAGIC_1);
    CHECK(ack[2] == VFD_HOST_PROTOCOL_VERSION);
    CHECK(ack[3] == VFD_HOST_COMMAND_ACK);
    CHECK(ack[4] == (uint8_t)(sequence & 0xffu));
    CHECK(ack[5] == (uint8_t)(sequence >> 8u));
    CHECK(encoded_crc == actual_crc);
    return (VfdHostAckStatus)ack[6];
}

static void test_crc_standard_vector(void)
{
    static const uint8_t vector[] = "123456789";

    CHECK(vfd_host_link_crc16(vector, sizeof(vector) - 1u) == 0x29b1u);
}

static void test_valid_frame_stages_then_swaps_at_boundary(void)
{
    VfdHostLink link;
    uint8_t initial[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t next[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t packet[VFD_HOST_FRAME_PACKET_BYTES];
    uint8_t ack[VFD_HOST_ACK_PACKET_BYTES];
    uint16_t displayed_sequence = 0u;

    fill_frame(initial, 1u);
    fill_frame(next, 99u);
    vfd_host_link_init(&link, initial);
    build_frame_packet(next, 0x1234u, packet);

    CHECK(memcmp(vfd_host_link_front(&link), initial, VFD_HOST_FRAME_BYTES) == 0);
    CHECK(feed_bytes(&link, packet, sizeof(packet), ack));
    CHECK(validate_ack(ack, 0x1234u) == VFD_HOST_ACK_OK);
    CHECK(vfd_host_link_has_pending(&link));
    CHECK(memcmp(vfd_host_link_front(&link), initial, VFD_HOST_FRAME_BYTES) == 0);

    CHECK(vfd_host_link_swap_if_pending(&link, &displayed_sequence));
    CHECK(displayed_sequence == 0x1234u);
    CHECK(!vfd_host_link_has_pending(&link));
    CHECK(memcmp(vfd_host_link_front(&link), next, VFD_HOST_FRAME_BYTES) == 0);
    CHECK(!vfd_host_link_swap_if_pending(&link, &displayed_sequence));
}

static void test_bad_crc_never_becomes_visible(void)
{
    VfdHostLink link;
    uint8_t initial[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t next[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t packet[VFD_HOST_FRAME_PACKET_BYTES];
    uint8_t ack[VFD_HOST_ACK_PACKET_BYTES];

    fill_frame(initial, 3u);
    fill_frame(next, 44u);
    vfd_host_link_init(&link, initial);
    build_frame_packet(next, 7u, packet);
    packet[VFD_HOST_FRAME_PACKET_BYTES - 1u] ^= 0x80u;

    CHECK(feed_bytes(&link, packet, sizeof(packet), ack));
    CHECK(validate_ack(ack, 7u) == VFD_HOST_ACK_CRC_ERROR);
    CHECK(!vfd_host_link_has_pending(&link));
    CHECK(memcmp(vfd_host_link_front(&link), initial, VFD_HOST_FRAME_BYTES) == 0);
}

static void test_header_errors_are_nacked_after_full_packet_is_consumed(void)
{
    struct HeaderCase {
        size_t index;
        uint8_t value;
        VfdHostAckStatus status;
    };
    static const struct HeaderCase cases[] = {
        {2u, 2u, VFD_HOST_ACK_VERSION_ERROR},
        {3u, 0x7fu, VFD_HOST_ACK_COMMAND_ERROR},
        {6u, 0xffu, VFD_HOST_ACK_LENGTH_ERROR},
    };
    uint8_t frame[VFD_PAGE_COUNT][VFD_WIDTH] = {{0u}};
    size_t case_index;

    for (case_index = 0u; case_index < sizeof(cases) / sizeof(cases[0]);
         ++case_index) {
        VfdHostLink link;
        uint8_t packet[VFD_HOST_FRAME_PACKET_BYTES];
        uint8_t ack[VFD_HOST_ACK_PACKET_BYTES];
        uint16_t crc;

        vfd_host_link_init(&link, NULL);
        build_frame_packet(frame, 8u, packet);
        packet[cases[case_index].index] = cases[case_index].value;
        crc = vfd_host_link_crc16(
            packet, VFD_HOST_FRAME_PACKET_BYTES - VFD_HOST_CRC_BYTES);
        packet[VFD_HOST_FRAME_PACKET_BYTES - 2u] = (uint8_t)(crc & 0xffu);
        packet[VFD_HOST_FRAME_PACKET_BYTES - 1u] = (uint8_t)(crc >> 8u);

        CHECK(feed_bytes(&link, packet, sizeof(packet), ack));
        CHECK(validate_ack(ack, 8u) == cases[case_index].status);
        CHECK(!vfd_host_link_has_pending(&link));
    }
}

static void test_pending_frame_is_idempotent_and_backpressures_new_sequence(void)
{
    VfdHostLink link;
    uint8_t first[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t second[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t first_packet[VFD_HOST_FRAME_PACKET_BYTES];
    uint8_t second_packet[VFD_HOST_FRAME_PACKET_BYTES];
    uint8_t ack[VFD_HOST_ACK_PACKET_BYTES];
    uint16_t sequence = 0u;

    fill_frame(first, 10u);
    fill_frame(second, 20u);
    build_frame_packet(first, 10u, first_packet);
    build_frame_packet(second, 11u, second_packet);
    vfd_host_link_init(&link, NULL);

    CHECK(feed_bytes(&link, first_packet, sizeof(first_packet), ack));
    CHECK(validate_ack(ack, 10u) == VFD_HOST_ACK_OK);

    CHECK(feed_bytes(&link, first_packet, sizeof(first_packet), ack));
    CHECK(validate_ack(ack, 10u) == VFD_HOST_ACK_OK);
    CHECK(vfd_host_link_has_pending(&link));

    CHECK(feed_bytes(&link, second_packet, sizeof(second_packet), ack));
    CHECK(validate_ack(ack, 11u) == VFD_HOST_ACK_BUSY);
    CHECK(vfd_host_link_swap_if_pending(&link, &sequence));
    CHECK(sequence == 10u);
    CHECK(memcmp(vfd_host_link_front(&link), first, VFD_HOST_FRAME_BYTES) == 0);

    CHECK(feed_bytes(&link, first_packet, sizeof(first_packet), ack));
    CHECK(validate_ack(ack, 10u) == VFD_HOST_ACK_OK);
    CHECK(!vfd_host_link_has_pending(&link));

    CHECK(feed_bytes(&link, second_packet, sizeof(second_packet), ack));
    CHECK(validate_ack(ack, 11u) == VFD_HOST_ACK_OK);
    CHECK(vfd_host_link_swap_if_pending(&link, &sequence));
    CHECK(memcmp(vfd_host_link_front(&link), second, VFD_HOST_FRAME_BYTES) == 0);
}

static void test_same_sequence_is_duplicate_only_when_payload_matches(void)
{
    VfdHostLink link;
    uint8_t first[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t second[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t first_packet[VFD_HOST_FRAME_PACKET_BYTES];
    uint8_t second_packet[VFD_HOST_FRAME_PACKET_BYTES];
    uint8_t ack[VFD_HOST_ACK_PACKET_BYTES];

    fill_frame(first, 1u);
    fill_frame(second, 2u);
    build_frame_packet(first, 0u, first_packet);
    build_frame_packet(second, 0u, second_packet);
    vfd_host_link_init(&link, NULL);

    CHECK(feed_bytes(&link, first_packet, sizeof(first_packet), ack));
    CHECK(validate_ack(ack, 0u) == VFD_HOST_ACK_OK);

    /* Same sequence but different bytes must not replace a pending frame. */
    CHECK(feed_bytes(&link, second_packet, sizeof(second_packet), ack));
    CHECK(validate_ack(ack, 0u) == VFD_HOST_ACK_BUSY);
    CHECK(vfd_host_link_swap_if_pending(&link, NULL));
    CHECK(memcmp(vfd_host_link_front(&link), first, VFD_HOST_FRAME_BYTES) == 0);

    /* After the swap it represents a restarted host and must be accepted. */
    CHECK(feed_bytes(&link, second_packet, sizeof(second_packet), ack));
    CHECK(validate_ack(ack, 0u) == VFD_HOST_ACK_OK);
    CHECK(vfd_host_link_has_pending(&link));
    CHECK(vfd_host_link_swap_if_pending(&link, NULL));
    CHECK(memcmp(vfd_host_link_front(&link), second, VFD_HOST_FRAME_BYTES) == 0);
}

static void test_receiver_resynchronizes_after_noise(void)
{
    VfdHostLink link;
    uint8_t frame[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t packet[VFD_HOST_FRAME_PACKET_BYTES];
    uint8_t ack[VFD_HOST_ACK_PACKET_BYTES];
    static const uint8_t noise[] = {0x00u, VFD_HOST_MAGIC_0, 0x00u, 0xffu};

    fill_frame(frame, 77u);
    build_frame_packet(frame, 22u, packet);
    vfd_host_link_init(&link, NULL);

    CHECK(!feed_bytes(&link, noise, sizeof(noise), ack));
    CHECK(feed_bytes(&link, packet, sizeof(packet), ack));
    CHECK(validate_ack(ack, 22u) == VFD_HOST_ACK_OK);
}

int main(void)
{
    test_crc_standard_vector();
    test_valid_frame_stages_then_swaps_at_boundary();
    test_bad_crc_never_becomes_visible();
    test_header_errors_are_nacked_after_full_packet_is_consumed();
    test_pending_frame_is_idempotent_and_backpressures_new_sequence();
    test_same_sequence_is_duplicate_only_when_payload_matches();
    test_receiver_resynchronizes_after_noise();

    if (failures != 0) {
        fprintf(stderr, "%d host-link test(s) failed\n", failures);
        return 1;
    }
    puts("vfd host-link tests passed");
    return 0;
}
