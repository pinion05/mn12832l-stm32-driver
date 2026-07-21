#include "GT20L_Font.h"

#include <stdbool.h>
#include <stddef.h>

static bool blit_is_valid(uint8_t x, uint8_t y, const uint8_t *font)
{
    return font != NULL && x < VFD_FONT_BUFFER_WIDTH &&
           y < VFD_FONT_BUFFER_PAGES * 8u;
}

static void blit_8px_columns(
    uint8_t x,
    uint8_t y,
    const uint8_t *font,
    size_t width,
    bool suppress_offset_one_spill)
{
    if (!blit_is_valid(x, y, font)) {
        return;
    }

    const size_t first_page = y / 8u;
    const uint8_t offset = (uint8_t)(y % 8u);

    for (size_t column = 0; column < width && x < VFD_FONT_BUFFER_WIDTH;
         ++column, ++x) {
        if (offset == 0u) {
            data[first_page][x] = font[column];
            continue;
        }

        data[first_page][x] |= (uint8_t)(font[column] << offset);
        if (first_page + 1u < VFD_FONT_BUFFER_PAGES &&
            !(suppress_offset_one_spill && offset == 1u)) {
            data[first_page + 1u][x] |=
                (uint8_t)(font[column] >> (8u - offset));
        }
    }
}

static void blit_16px_columns(
    uint8_t x,
    uint8_t y,
    const uint8_t *font,
    size_t width)
{
    if (!blit_is_valid(x, y, font)) {
        return;
    }

    const size_t first_page = y / 8u;
    const uint8_t offset = (uint8_t)(y % 8u);

    for (size_t column = 0; column < width && x < VFD_FONT_BUFFER_WIDTH;
         ++column, ++x) {
        const uint8_t upper = font[column * 2u];
        const uint8_t lower = font[column * 2u + 1u];

        if (offset == 0u) {
            data[first_page][x] = upper;
            if (first_page + 1u < VFD_FONT_BUFFER_PAGES) {
                data[first_page + 1u][x] = lower;
            }
            continue;
        }

        data[first_page][x] |= (uint8_t)(upper << offset);
        if (first_page + 1u < VFD_FONT_BUFFER_PAGES) {
            data[first_page + 1u][x] |=
                (uint8_t)((upper >> (8u - offset)) | (lower << offset));
        }
        if (first_page + 2u < VFD_FONT_BUFFER_PAGES) {
            data[first_page + 2u][x] |= (uint8_t)(lower >> (8u - offset));
        }
    }
}

void PutFont15x16ToBuff(uint8_t x, uint8_t y, const uint8_t *font)
{
    blit_16px_columns(x, y, font, 15u);
}

void PutFont8x16ToBuff(uint8_t x, uint8_t y, const uint8_t *font)
{
    blit_16px_columns(x, y, font, 8u);
}

void PutFont7x8ToBuff(uint8_t x, uint8_t y, const uint8_t *font)
{
    blit_8px_columns(x, y, font, 7u, false);
}

void PutFont5x7ToBuff(uint8_t x, uint8_t y, const uint8_t *font)
{
    blit_8px_columns(x, y, font, 5u, true);
}
