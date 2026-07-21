# Raspberry Pi ↔ STM32 frame contract

This contract connects the Python host stack to the tested STM32 scan core.
Multi-byte integers are little-endian.

## Logical frame

- Resolution: 128 × 32 monochrome pixels.
- Size: 4096 bits = 512 bytes.
- Layout: four vertical eight-pixel pages (`MVLSB`).
- Pixel `(x, y)`: byte `(y / 8) * 128 + x`, bit `1 << (y % 8)`.

The Python `MvlsbRenderer` and the C `VfdHostLink` use this layout without a
second pixel conversion.

## Frame packet: 522 bytes

| Offset | Size | Value |
| ---: | ---: | --- |
| 0 | 2 | Magic ASCII `VF` (`56 46`) |
| 2 | 1 | Protocol version `01` |
| 3 | 1 | Frame command `01` |
| 4 | 2 | Sequence number |
| 6 | 2 | Payload length, always `512` (`00 02`) |
| 8 | 512 | Native MVLSB frame |
| 520 | 2 | CRC-16/CCITT-FALSE over bytes 0..519 |

## ACK packet: 9 bytes

| Offset | Size | Value |
| ---: | ---: | --- |
| 0 | 2 | Magic ASCII `VF` |
| 2 | 1 | Protocol version `01` |
| 3 | 1 | ACK command `80` |
| 4 | 2 | Sequence number |
| 6 | 1 | Status |
| 7 | 2 | CRC-16/CCITT-FALSE over bytes 0..6 |

Status values:

| Value | Name | Meaning |
| ---: | --- | --- |
| 0 | `OK` | Frame was staged, or the sequence was an accepted duplicate |
| 1 | `CRC_ERROR` | Packet checksum failed |
| 2 | `VERSION_ERROR` | Unsupported protocol version |
| 3 | `COMMAND_ERROR` | Unsupported command |
| 4 | `LENGTH_ERROR` | Payload length was not 512 |
| 5 | `BUSY` | A different frame is waiting for the next scan boundary |

`OK` means the complete frame is safely staged. Visibility occurs when the
scanner moves from phase 43 to phase 1. A retransmission with the same sequence
and identical payload is idempotent and receives `OK` without staging a second
copy. Reusing a sequence with different pixels is accepted after the previous
frame is visible, which allows a restarted host to begin again at sequence 0.

## Lifecycle

1. Start one persistent bridge process and open the serial device once.
2. Render the high-level model into a fresh 512-byte logical frame.
3. Skip transmission when it equals the last acknowledged frame.
4. Send one 522-byte packet and wait for its 9-byte ACK.
5. Retry `BUSY` or `CRC_ERROR` with the same sequence.
6. The STM32 writes only to the back buffer while scanning the front buffer.
7. At the 43 → 1 boundary, call `vfd_host_link_swap_if_pending()`.
8. Close the process and serial device only at application shutdown.

Opening a new bridge connection invalidates the host's unchanged-frame cache,
so the first frame is always replayed after a possible MCU reset.

## STM32 board glue still required

`VFD_HostProcessByte()` is the hardware-independent entry point. The final
board port must:

1. configure the selected UART or USB CDC peripheral;
2. enqueue received bytes in its ISR/DMA callback;
3. call `VFD_HostProcessByte()` from the main loop, not from a long ISR;
4. transmit the returned ACK when the function returns `true`.

The exact STM32 part, pins, clock source, and Cube HAL package are not present in
the supplied bundle, so this final peripheral binding is deliberately not
guessed.
