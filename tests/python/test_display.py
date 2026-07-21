from __future__ import annotations

import unittest

from mn12832l.display import (
    DisplayClosedError,
    FrameRejectedError,
    VfdDisplay,
)
from mn12832l.protocol import AckStatus, encode_ack
from mn12832l.renderer import MvlsbRenderer


class RecordingTransport:
    def __init__(self, statuses: list[AckStatus] | None = None) -> None:
        self.open_calls = 0
        self.close_calls = 0
        self.packets: list[bytes] = []
        self._statuses = list(statuses or [])

    def open(self) -> None:
        self.open_calls += 1

    def request(self, packet: bytes) -> bytes:
        self.packets.append(packet)
        sequence = int.from_bytes(packet[4:6], "little")
        status = self._statuses.pop(0) if self._statuses else AckStatus.OK
        return encode_ack(sequence, status)

    def close(self) -> None:
        self.close_calls += 1


class DisplayTests(unittest.TestCase):
    def test_context_manager_initializes_once_and_closes_once(self) -> None:
        transport = RecordingTransport()
        display = VfdDisplay(transport, renderer=MvlsbRenderer())

        with display:
            display.open()

        self.assertEqual(transport.open_calls, 1)
        self.assertEqual(transport.close_calls, 1)

    def test_update_connects_model_rendering_and_transmission(self) -> None:
        transport = RecordingTransport()
        display = VfdDisplay(transport, renderer=MvlsbRenderer())

        with display:
            result = display.update(
                {"x": 127, "y": 31},
                lambda model, fb: fb.pixel(model["x"], model["y"], 1),
            )

        self.assertTrue(result.sent)
        self.assertEqual(result.sequence, 0)
        self.assertEqual(result.attempts, 1)
        self.assertEqual(len(transport.packets), 1)
        self.assertEqual(transport.packets[0][8 + 511], 0x80)

    def test_unchanged_frame_is_not_sent_twice(self) -> None:
        transport = RecordingTransport()
        display = VfdDisplay(transport, renderer=MvlsbRenderer())
        frame = bytes(512)

        with display:
            first = display.present(frame)
            second = display.present(frame)

        self.assertTrue(first.sent)
        self.assertFalse(second.sent)
        self.assertEqual(second.sequence, first.sequence)
        self.assertEqual(len(transport.packets), 1)

    def test_reopening_resends_state_after_possible_mcu_reset(self) -> None:
        transport = RecordingTransport()
        display = VfdDisplay(transport, renderer=MvlsbRenderer())
        frame = bytes([0x33]) * 512

        with display:
            first = display.present(frame)
        with display:
            second = display.present(frame)

        self.assertTrue(first.sent)
        self.assertTrue(second.sent)
        self.assertEqual(len(transport.packets), 2)
        self.assertEqual(transport.open_calls, 2)
        self.assertEqual(transport.close_calls, 2)

    def test_busy_ack_retries_same_sequence(self) -> None:
        transport = RecordingTransport([AckStatus.BUSY, AckStatus.OK])
        display = VfdDisplay(
            transport,
            renderer=MvlsbRenderer(),
            retry_limit=1,
            retry_delay=0,
        )

        with display:
            result = display.present(bytes([0xA5]) * 512)

        self.assertEqual(result.attempts, 2)
        self.assertEqual(
            [packet[4:6] for packet in transport.packets],
            [b"\x00\x00", b"\x00\x00"],
        )

    def test_rejected_frame_does_not_advance_sequence_or_cache_frame(self) -> None:
        transport = RecordingTransport([AckStatus.CRC_ERROR, AckStatus.OK])
        display = VfdDisplay(
            transport,
            renderer=MvlsbRenderer(),
            retry_limit=0,
            retry_delay=0,
        )

        with display:
            with self.assertRaises(FrameRejectedError):
                display.present(bytes([1]) * 512)
            result = display.present(bytes([1]) * 512)

        self.assertEqual(result.sequence, 0)
        self.assertEqual(len(transport.packets), 2)

    def test_present_requires_open_display_and_exact_frame_size(self) -> None:
        display = VfdDisplay(RecordingTransport(), renderer=MvlsbRenderer())

        with self.assertRaises(DisplayClosedError):
            display.present(bytes(512))

        with display, self.assertRaises(ValueError):
            display.present(bytes(511))


if __name__ == "__main__":
    unittest.main()
