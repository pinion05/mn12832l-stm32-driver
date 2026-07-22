#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

#include "vfd_host_link.h"
#include "vfd_pin_trace.h"

static bool process_packet(
    VfdHostLink *link,
    const uint8_t packet[VFD_HOST_FRAME_PACKET_BYTES])
{
    uint8_t ack[VFD_HOST_ACK_PACKET_BYTES];
    bool produced_ack = false;

    for (size_t index = 0u; index < VFD_HOST_FRAME_PACKET_BYTES; ++index) {
        const bool produced = vfd_host_link_feed(link, packet[index], ack);
        if (produced_ack ||
            (produced && index + 1u != VFD_HOST_FRAME_PACKET_BYTES)) {
            return false;
        }
        produced_ack = produced_ack || produced;
    }
    if (!produced_ack || fwrite(ack, 1u, sizeof(ack), stdout) != sizeof(ack)) {
        return false;
    }

    if (ack[6] == (uint8_t)VFD_HOST_ACK_OK) {
        (void)vfd_host_link_swap_if_pending(link, NULL);
        if (!vfd_pin_trace_write(stdout, vfd_host_link_front(link))) {
            return false;
        }
    }
    return fflush(stdout) == 0;
}

static bool read_packet(
    uint8_t packet[VFD_HOST_FRAME_PACKET_BYTES], bool *reached_eof)
{
    size_t total = 0u;

    *reached_eof = false;
    while (total < VFD_HOST_FRAME_PACKET_BYTES) {
        const size_t received = fread(
            &packet[total], 1u, VFD_HOST_FRAME_PACKET_BYTES - total, stdin);

        if (received != 0u) {
            total += received;
            continue;
        }
        if (feof(stdin) != 0) {
            *reached_eof = total == 0u;
            return *reached_eof;
        }
        return false;
    }
    return true;
}

int main(void)
{
    VfdHostLink link;
    uint8_t packet[VFD_HOST_FRAME_PACKET_BYTES];
    bool reached_eof;

#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 ||
        _setmode(_fileno(stdout), _O_BINARY) == -1) {
        fputs("failed to configure binary standard streams\n", stderr);
        return 1;
    }
#endif

    vfd_host_link_init(&link, NULL);
    for (;;) {
        if (!read_packet(packet, &reached_eof)) {
            fputs("system twin received a truncated frame packet\n", stderr);
            return 2;
        }
        if (reached_eof) {
            return 0;
        }
        if (!process_packet(&link, packet)) {
            fputs("system twin could not process a frame packet\n", stderr);
            return 3;
        }
    }
}
