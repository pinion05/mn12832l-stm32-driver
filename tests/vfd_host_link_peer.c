#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "vfd_host_link.h"

int main(void)
{
    VfdHostLink link;
    uint8_t ack[VFD_HOST_ACK_PACKET_BYTES];
    int input;

    vfd_host_link_init(&link, NULL);
    while ((input = getchar()) != EOF) {
        if (!vfd_host_link_feed(&link, (uint8_t)input, ack)) {
            continue;
        }
        if (fwrite(ack, 1u, sizeof(ack), stdout) != sizeof(ack)) {
            return 2;
        }
        if (fflush(stdout) != 0) {
            return 3;
        }
        if (ack[6] == (uint8_t)VFD_HOST_ACK_OK) {
            (void)vfd_host_link_swap_if_pending(&link, NULL);
        }
    }
    return ferror(stdin) != 0 ? 1 : 0;
}
