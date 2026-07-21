#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "vfd_scan.h"

static int failures;

#define CHECK(condition)                                                        \
    do {                                                                        \
        if (!(condition)) {                                                      \
            fprintf(stderr, "CHECK failed at %s:%d: %s\n", __FILE__, __LINE__, \
                    #condition);                                                 \
            failures++;                                                         \
        }                                                                       \
    } while (0)

static bool frame_bit(const uint8_t frame[VFD_SCAN_FRAME_BYTES], size_t bit)
{
    return (frame[bit / 8u] & (uint8_t)(0x80u >> (bit % 8u))) != 0;
}

static size_t count_set_bits(
    const uint8_t frame[VFD_SCAN_FRAME_BYTES],
    size_t begin,
    size_t end)
{
    size_t count = 0;
    for (size_t bit = begin; bit < end; ++bit) {
        count += frame_bit(frame, bit) ? 1u : 0u;
    }
    return count;
}

static void test_zero_frame_grid_selection(void)
{
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH] = {{0}};
    uint8_t frame[VFD_SCAN_FRAME_BYTES];

    CHECK(vfd_scan_pack_step(framebuffer, 1, frame));
    CHECK(count_set_bits(frame, 0, VFD_PIXEL_BITS_PER_PHASE) == 0);
    CHECK(frame[24] == 0xc0);
    CHECK(count_set_bits(frame, VFD_PIXEL_BITS_PER_PHASE,
                         VFD_PIXEL_BITS_PER_PHASE + VFD_GRID_BITS_PER_PHASE) == 2);

    CHECK(vfd_scan_pack_step(framebuffer, 43, frame));
    CHECK(frame[29] == 0x30);
    CHECK(count_set_bits(frame, VFD_PIXEL_BITS_PER_PHASE,
                         VFD_PIXEL_BITS_PER_PHASE + VFD_GRID_BITS_PER_PHASE) == 2);
}

static void test_odd_phase_pixel_order(void)
{
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH] = {{0}};
    uint8_t frame[VFD_SCAN_FRAME_BYTES];

    framebuffer[0][0] = 0x01;
    framebuffer[0][1] = 0x02;
    framebuffer[0][2] = 0x04;

    CHECK(vfd_scan_pack_step(framebuffer, 1, frame));
    CHECK(frame_bit(frame, 0));
    CHECK(frame_bit(frame, 6 + 2));
    CHECK(frame_bit(frame, 12 + 4));
    CHECK(count_set_bits(frame, 0, VFD_PIXEL_BITS_PER_PHASE) == 3);
}

static void test_even_phase_pixel_order(void)
{
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH] = {{0}};
    uint8_t frame[VFD_SCAN_FRAME_BYTES];

    framebuffer[0][3] = 0x01;
    framebuffer[0][4] = 0x02;
    framebuffer[0][5] = 0x04;

    CHECK(vfd_scan_pack_step(framebuffer, 2, frame));
    CHECK(frame_bit(frame, 5));
    CHECK(frame_bit(frame, 6 + 3));
    CHECK(frame_bit(frame, 12 + 1));
    CHECK(count_set_bits(frame, 0, VFD_PIXEL_BITS_PER_PHASE) == 3);
}

static void test_last_partial_phase(void)
{
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH] = {{0}};
    uint8_t frame[VFD_SCAN_FRAME_BYTES];

    framebuffer[0][126] = 0x01;
    framebuffer[0][127] = 0x01;

    CHECK(vfd_scan_pack_step(framebuffer, 43, frame));
    CHECK(frame_bit(frame, 0));
    CHECK(frame_bit(frame, 2));
    CHECK(!frame_bit(frame, 4));
    CHECK(count_set_bits(frame, 0, VFD_PIXEL_BITS_PER_PHASE) == 2);
}

static void test_invalid_inputs_are_rejected(void)
{
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH] = {{0}};
    uint8_t frame[VFD_SCAN_FRAME_BYTES];

    memset(frame, 0xa5, sizeof(frame));
    CHECK(!vfd_scan_pack_step(framebuffer, 0, frame));
    CHECK(count_set_bits(frame, 0, sizeof(frame) * 8u) == 0);

    memset(frame, 0xa5, sizeof(frame));
    CHECK(!vfd_scan_pack_step(framebuffer, 44, frame));
    CHECK(count_set_bits(frame, 0, sizeof(frame) * 8u) == 0);

    CHECK(!vfd_scan_pack_step(NULL, 1, frame));
    CHECK(!vfd_scan_pack_step(framebuffer, 1, NULL));
}

int main(void)
{
    test_zero_frame_grid_selection();
    test_odd_phase_pixel_order();
    test_even_phase_pixel_order();
    test_last_partial_phase();
    test_invalid_inputs_are_rejected();

    if (failures != 0) {
        fprintf(stderr, "%d scan test(s) failed\n", failures);
        return EXIT_FAILURE;
    }

    puts("scan tests passed");
    return EXIT_SUCCESS;
}
