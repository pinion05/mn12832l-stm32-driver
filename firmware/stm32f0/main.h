#ifndef MAIN_H
#define MAIN_H

#include <stdint.h>

#include "stm32f0xx_hal.h"

void VFD_SafeShutdown(void);
void _Error_Handler(const char *file, uint32_t line);

#endif
