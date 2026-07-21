#ifndef VFD_DELAY_H
#define VFD_DELAY_H

/*
 * Loop counts are preserved from the supplied firmware. The time-based names
 * are historical; verify their real durations on the target with a logic
 * analyzer after the exact MCU, clock tree, and compiler flags are known.
 */
void vfd_delay_13us_empirical(void);
void vfd_delay_17us_empirical(void);
void vfd_delay_3us_empirical(void);
void vfd_delay_255ns_empirical(void);

#endif
