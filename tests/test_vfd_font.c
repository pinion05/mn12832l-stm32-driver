#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "GT20L_Font.h"

uint8_t data[4][128];

static int failures;

#define CHECK(condition)                                                        \
    do {                                                                        \
        if (!(condition)) {                                                      \
            fprintf(stderr, "CHECK failed at %s:%d: %s\n", __FILE__, __LINE__, \
                    #condition);                                                 \
            failures++;                                                         \
        }                                                                       \
    } while (0)

static bool framebuffer_is_zero(void)
{
    for (size_t page = 0; page < 4; ++page) {
        for (size_t x = 0; x < 128; ++x) {
            if (data[page][x] != 0) {
                return false;
            }
        }
    }
    return true;
}

static void test_valid_5x7_blit(void)
{
    const uint8_t glyph[5] = {0x01, 0x02, 0x04, 0x08, 0x10};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(0, 0, glyph);

    for (size_t x = 0; x < 5; ++x) {
        CHECK(data[0][x] == glyph[x]);
    }
    CHECK(data[0][5] == 0);
}

static void test_valid_unaligned_5x7_blit(void)
{
    const uint8_t glyph[5] = {0xff, 0x01, 0x02, 0x04, 0x08};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(10, 2, glyph);

    CHECK(data[0][10] == 0xfc);
    CHECK(data[1][10] == 0x03);
    CHECK(data[0][11] == 0x04);
    CHECK(data[1][11] == 0x00);
}

static void test_right_edge_clipping(void)
{
    const uint8_t glyph[5] = {1, 2, 3, 4, 5};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(127, 0, glyph);

    CHECK(data[0][127] == 1);
    CHECK(data[1][0] == 0);
}

static void test_bottom_edge_clipping(void)
{
    const uint8_t glyph[5] = {0xff, 0xff, 0xff, 0xff, 0xff};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(0, 31, glyph);
    for (size_t x = 0; x < 5; ++x) {
        CHECK(data[3][x] == 0x80);
    }
}

static void test_valid_7x8_blit(void)
{
    const uint8_t glyph[7] = {0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40};

    memset(data, 0, sizeof(data));
    PutFont7x8ToBuff(3, 3, glyph);

    for (size_t x = 0; x < 7; ++x) {
        CHECK(data[0][3 + x] == (uint8_t)(glyph[x] << 3));
        CHECK(data[1][3 + x] == (uint8_t)(glyph[x] >> 5));
    }
}

static void test_valid_8x16_blit(void)
{
    const uint8_t glyph[16] = {
        0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f, 0x10,
    };

    memset(data, 0, sizeof(data));
    PutFont8x16ToBuff(4, 8, glyph);

    for (size_t column = 0; column < 8; ++column) {
        CHECK(data[1][4 + column] == glyph[column * 2]);
        CHECK(data[2][4 + column] == glyph[column * 2 + 1]);
    }
}

static void test_valid_15x16_blit(void)
{
    uint8_t glyph[30];
    for (size_t byte = 0; byte < sizeof(glyph); ++byte) {
        glyph[byte] = (uint8_t)(byte + 1);
    }

    memset(data, 0, sizeof(data));
    PutFont15x16ToBuff(120, 16, glyph);

    for (size_t column = 0; column < 8; ++column) {
        CHECK(data[2][120 + column] == glyph[column * 2]);
        CHECK(data[3][120 + column] == glyph[column * 2 + 1]);
    }
}

static void test_unaligned_8x16_three_page_blit(void)
{
    const uint8_t glyph[16] = {
        0x01, 0x82, 0x03, 0x84, 0x05, 0x86, 0x07, 0x88,
        0x09, 0x8a, 0x0b, 0x8c, 0x0d, 0x8e, 0x0f, 0x90,
    };

    memset(data, 0, sizeof(data));
    PutFont8x16ToBuff(20, 13, glyph);

    for (size_t column = 0; column < 8; ++column) {
        const uint8_t upper = glyph[column * 2u];
        const uint8_t lower = glyph[column * 2u + 1u];
        CHECK(data[1][20 + column] == (uint8_t)(upper << 5u));
        CHECK(data[2][20 + column] ==
              (uint8_t)((upper >> 3u) | (lower << 5u)));
        CHECK(data[3][20 + column] == (uint8_t)(lower >> 3u));
    }
}

static void test_16px_bottom_right_clipping(void)
{
    const uint8_t glyph[16] = {
        0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
        0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    };

    memset(data, 0, sizeof(data));
    PutFont8x16ToBuff(127, 31, glyph);
    CHECK(data[3][127] == 0x80u);
    CHECK(data[0][0] == 0u);
}

static void test_5x7_offset_one_preserves_supplied_behavior(void)
{
    const uint8_t glyph[5] = {0xff, 0x7f, 0x3f, 0x1f, 0x0f};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(8, 1, glyph);
    for (size_t column = 0; column < 5; ++column) {
        CHECK(data[0][8 + column] == (uint8_t)(glyph[column] << 1u));
        CHECK(data[1][8 + column] == 0u);
    }
}

static void test_out_of_range_is_noop(void)
{
    const uint8_t glyph[5] = {0xff, 0xff, 0xff, 0xff, 0xff};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(0, 32, glyph);
    CHECK(framebuffer_is_zero());

    PutFont5x7ToBuff(128, 0, glyph);
    CHECK(framebuffer_is_zero());

    PutFont5x7ToBuff(0, 0, NULL);
    PutFont7x8ToBuff(0, 0, NULL);
    PutFont8x16ToBuff(0, 0, NULL);
    PutFont15x16ToBuff(0, 0, NULL);
    CHECK(framebuffer_is_zero());
}

int main(int argc, char **argv)
{
    const bool characterization_only = argc > 1 && strcmp(argv[1], "valid") == 0;

    test_valid_5x7_blit();
    test_valid_unaligned_5x7_blit();
    test_right_edge_clipping();
    test_bottom_edge_clipping();
    test_valid_7x8_blit();
    test_valid_8x16_blit();
    test_valid_15x16_blit();
    test_unaligned_8x16_three_page_blit();
    test_16px_bottom_right_clipping();
    test_5x7_offset_one_preserves_supplied_behavior();

    if (!characterization_only) {
        test_out_of_range_is_noop();
    }

    if (failures != 0) {
        fprintf(stderr, "%d font test(s) failed\n", failures);
        return EXIT_FAILURE;
    }

    puts("font tests passed");
    return EXIT_SUCCESS;
}
