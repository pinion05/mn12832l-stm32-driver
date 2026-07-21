#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "vfd_scan.h"

static int failures;

typedef struct {
    bool bits[VFD_SCAN_FRAME_BYTES * 8u];
    size_t bit_count;
    size_t gap_count;
    size_t gap_after_bit;
} EmitCapture;

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

static void capture_bit(bool bit, void *context)
{
    EmitCapture *capture = context;
    CHECK(capture->bit_count < VFD_SCAN_FRAME_BYTES * 8u);
    if (capture->bit_count < VFD_SCAN_FRAME_BYTES * 8u) {
        capture->bits[capture->bit_count] = bit;
    }
    ++capture->bit_count;
}

static void capture_gap(void *context)
{
    EmitCapture *capture = context;
    ++capture->gap_count;
    capture->gap_after_bit = capture->bit_count;
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

static void test_every_phase_and_row_has_the_supplied_lane_mapping(void)
{
    static const size_t odd_lane[3] = {0u, 2u, 4u};
    static const size_t even_lane[3] = {5u, 3u, 1u};
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH];
    uint8_t frame[VFD_SCAN_FRAME_BYTES];

    for (uint8_t phase = 1u; phase <= VFD_SCAN_PHASES; ++phase) {
        const size_t base_column = ((size_t)phase - 1u) * 3u;
        const size_t source_count = phase == VFD_SCAN_PHASES ? 2u : 3u;
        const size_t *expected_lane = (phase & 1u) != 0u ? odd_lane : even_lane;

        for (size_t row = 0; row < VFD_HEIGHT; ++row) {
            for (size_t source = 0; source < source_count; ++source) {
                memset(framebuffer, 0, sizeof(framebuffer));
                framebuffer[row / 8u][base_column + source] =
                    (uint8_t)(1u << (row % 8u));

                CHECK(vfd_scan_pack_step(framebuffer, phase, frame));
                CHECK(frame_bit(frame, row * 6u + expected_lane[source]));
                CHECK(count_set_bits(frame, 0, VFD_PIXEL_BITS_PER_PHASE) == 1u);
            }
        }
    }
}

static void test_every_phase_selects_two_neighboring_grids(void)
{
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH] = {{0}};
    uint8_t frame[VFD_SCAN_FRAME_BYTES];

    for (uint8_t phase = 1u; phase <= VFD_SCAN_PHASES; ++phase) {
        CHECK(vfd_scan_pack_step(framebuffer, phase, frame));
        CHECK(count_set_bits(frame, VFD_PIXEL_BITS_PER_PHASE,
                             VFD_SCAN_FRAME_BYTES * 8u) == 2u);
        for (size_t grid = 0; grid < VFD_GRID_BITS_PER_PHASE; ++grid) {
            const bool expected =
                grid == (size_t)phase - 1u || grid == (size_t)phase;
            CHECK(frame_bit(frame, VFD_PIXEL_BITS_PER_PHASE + grid) == expected);
        }
    }
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

static void test_scan_state_wraps_and_pulses_hv(void)
{
    VfdScanState state;

    vfd_scan_state_init(&state);
    CHECK(state.phase == 1u);
    CHECK(!state.hv_enabled);

    for (uint8_t completed = 1u; completed < VFD_SCAN_PHASES; ++completed) {
        vfd_scan_state_advance(&state);
        CHECK(state.phase == (uint8_t)(completed + 1u));
        CHECK(!state.hv_enabled);
    }

    vfd_scan_state_advance(&state);
    CHECK(state.phase == 1u);
    CHECK(state.hv_enabled);
    CHECK(state.hv_ticks_remaining == 1u);

    vfd_scan_state_advance(&state);
    CHECK(state.phase == 2u);
    CHECK(!state.hv_enabled);
    CHECK(state.hv_ticks_remaining == 0u);
}

static void test_scan_state_null_is_safe(void)
{
    vfd_scan_state_init(NULL);
    vfd_scan_state_advance(NULL);
}

static void test_emit_frame_is_msb_first_with_one_protocol_gap(void)
{
    uint8_t frame[VFD_SCAN_FRAME_BYTES];
    EmitCapture capture = {0};

    for (size_t index = 0; index < sizeof(frame); ++index) {
        frame[index] = (uint8_t)(index * 37u + 11u);
    }

    CHECK(vfd_scan_emit_frame(frame, capture_bit, capture_gap, &capture));
    CHECK(capture.bit_count == sizeof(frame) * 8u);
    CHECK(capture.gap_count == 1u);
    CHECK(capture.gap_after_bit == VFD_PIXEL_BITS_PER_PHASE);

    for (size_t bit = 0; bit < capture.bit_count; ++bit) {
        const bool expected =
            (frame[bit / 8u] & (uint8_t)(0x80u >> (bit % 8u))) != 0u;
        CHECK(capture.bits[bit] == expected);
    }

    CHECK(!vfd_scan_emit_frame(NULL, capture_bit, capture_gap, &capture));
    CHECK(!vfd_scan_emit_frame(frame, NULL, capture_gap, &capture));
    CHECK(!vfd_scan_emit_frame(frame, capture_bit, NULL, &capture));
}

int main(void)
{
    test_zero_frame_grid_selection();
    test_odd_phase_pixel_order();
    test_even_phase_pixel_order();
    test_last_partial_phase();
    test_every_phase_and_row_has_the_supplied_lane_mapping();
    test_every_phase_selects_two_neighboring_grids();
    test_invalid_inputs_are_rejected();
    test_scan_state_wraps_and_pulses_hv();
    test_scan_state_null_is_safe();
    test_emit_frame_is_msb_first_with_one_protocol_gap();

    if (failures != 0) {
        fprintf(stderr, "%d scan test(s) failed\n", failures);
        return EXIT_FAILURE;
    }

    puts("scan tests passed");
    return EXIT_SUCCESS;
}
