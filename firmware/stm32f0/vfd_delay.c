#include "vfd_delay.h"

#include <stdint.h>

#if !defined(__clang__) && !defined(__GNUC__)
#error "vfd_delay requires a compiler with GNU-style inline assembly"
#endif

#define VFD_DEFINE_EMPIRICAL_DELAY(function_name, iteration_count) \
    void function_name(void)                                      \
    {                                                             \
        volatile uint8_t remaining = (iteration_count);           \
        while (remaining != 0u) {                                 \
            __asm__ volatile("nop" ::: "memory");                 \
            --remaining;                                         \
        }                                                         \
    }

VFD_DEFINE_EMPIRICAL_DELAY(vfd_delay_13us_empirical, 80u)
VFD_DEFINE_EMPIRICAL_DELAY(vfd_delay_17us_empirical, 106u)
VFD_DEFINE_EMPIRICAL_DELAY(vfd_delay_3us_empirical, 18u)
VFD_DEFINE_EMPIRICAL_DELAY(vfd_delay_255ns_empirical, 1u)
