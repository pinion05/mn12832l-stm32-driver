#ifndef MAIN_H
#define MAIN_H

#include <stdbool.h>
#include <stdint.h>

#include "stm32f0xx_hal.h"
#include "vfd_host_link.h"

void VFD_SafeShutdown(void);
/* Call from the main loop after dequeuing one UART/USB receive byte. */
bool VFD_HostProcessByte(
    uint8_t byte, uint8_t ack_out[VFD_HOST_ACK_PACKET_BYTES]);
void _Error_Handler(const char *file, uint32_t line);

#endif
