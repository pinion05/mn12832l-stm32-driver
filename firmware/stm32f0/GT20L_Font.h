#ifndef GT20L_FONT_H
#define GT20L_FONT_H

#include <stdint.h>

#define VFD_FONT_BUFFER_PAGES 4u
#define VFD_FONT_BUFFER_WIDTH 128u

extern uint8_t data[VFD_FONT_BUFFER_PAGES][VFD_FONT_BUFFER_WIDTH];

/* Font data is stored vertically, least-significant pixel first. */
void PutFont15x16ToBuff(uint8_t x, uint8_t y, const uint8_t *font);
void PutFont8x16ToBuff(uint8_t x, uint8_t y, const uint8_t *font);
void PutFont7x8ToBuff(uint8_t x, uint8_t y, const uint8_t *font);
void PutFont5x7ToBuff(uint8_t x, uint8_t y, const uint8_t *font);

#endif
