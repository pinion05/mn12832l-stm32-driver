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
    PutFont5x7ToBuff(0, 0, (uint8_t *)glyph);

    for (size_t x = 0; x < 5; ++x) {
        CHECK(data[0][x] == glyph[x]);
    }
    CHECK(data[0][5] == 0);
}

static void test_valid_unaligned_5x7_blit(void)
{
    const uint8_t glyph[5] = {0xff, 0x01, 0x02, 0x04, 0x08};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(10, 2, (uint8_t *)glyph);

    CHECK(data[0][10] == 0xfc);
    CHECK(data[1][10] == 0x03);
    CHECK(data[0][11] == 0x04);
    CHECK(data[1][11] == 0x00);
}

static void test_right_edge_clipping(void)
{
    const uint8_t glyph[5] = {1, 2, 3, 4, 5};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(127, 0, (uint8_t *)glyph);

    CHECK(data[0][127] == 1);
    CHECK(data[1][0] == 0);
}

static void test_bottom_edge_clipping(void)
{
    const uint8_t glyph[5] = {0xff, 0xff, 0xff, 0xff, 0xff};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(0, 31, (uint8_t *)glyph);
    for (size_t x = 0; x < 5; ++x) {
        CHECK(data[3][x] == 0x80);
    }
}

static void test_out_of_range_is_noop(void)
{
    const uint8_t glyph[5] = {0xff, 0xff, 0xff, 0xff, 0xff};

    memset(data, 0, sizeof(data));
    PutFont5x7ToBuff(0, 32, (uint8_t *)glyph);
    CHECK(framebuffer_is_zero());

    PutFont5x7ToBuff(128, 0, (uint8_t *)glyph);
    CHECK(framebuffer_is_zero());

    PutFont5x7ToBuff(0, 0, NULL);
    CHECK(framebuffer_is_zero());
}

int main(int argc, char **argv)
{
    const bool characterization_only = argc > 1 && strcmp(argv[1], "valid") == 0;

    test_valid_5x7_blit();
    test_valid_unaligned_5x7_blit();
    test_right_edge_clipping();
    test_bottom_edge_clipping();

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
