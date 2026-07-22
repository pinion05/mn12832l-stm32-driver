#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

#include "vfd_pin_trace.h"

static bool twin_read_frame(
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH])
{
    const size_t expected = VFD_PAGE_COUNT * VFD_WIDTH;
    const size_t received = fread(framebuffer, 1u, expected, stdin);

    if (received != expected || ferror(stdin) != 0) {
        return false;
    }
    return fgetc(stdin) == EOF;
}

int main(void)
{
    uint8_t framebuffer[VFD_PAGE_COUNT][VFD_WIDTH];

#ifdef _WIN32
    if (_setmode(_fileno(stdin), _O_BINARY) == -1 ||
        _setmode(_fileno(stdout), _O_BINARY) == -1) {
        fputs("failed to configure binary standard streams\n", stderr);
        return 1;
    }
#endif

    if (!twin_read_frame(framebuffer)) {
        fputs("expected exactly one 512-byte MVLSB frame on stdin\n", stderr);
        return 2;
    }
    if (!vfd_pin_trace_write(stdout, framebuffer) || fflush(stdout) != 0) {
        fputs("production scan core could not emit the pin trace\n", stderr);
        return 3;
    }
    return 0;
}
