from __future__ import annotations

import io
import unittest

from mn12832l.protocol import AckStatus, encode_ack, encode_frame
from mn12832l.serial_bridge import BridgeError, run_bridge


class FakeSerial:
    def __init__(self, replies: bytes, read_chunk_size: int = 3) -> None:
        self._replies = io.BytesIO(replies)
        self._read_chunk_size = read_chunk_size
        self.writes: list[bytes] = []
        self.flush_calls = 0

    def write(self, data: bytes) -> int:
        self.writes.append(bytes(data))
        return len(data)

    def flush(self) -> None:
        self.flush_calls += 1

    def read(self, size: int) -> bytes:
        return self._replies.read(min(size, self._read_chunk_size))


class SerialBridgeTests(unittest.TestCase):
    def test_bridge_keeps_one_device_open_for_multiple_packets(self) -> None:
        first = encode_frame(bytes(512), 1)
        second = encode_frame(bytes([0xFF]) * 512, 2)
        replies = encode_ack(1, AckStatus.OK) + encode_ack(2, AckStatus.OK)
        device = FakeSerial(replies)
        output = io.BytesIO()

        count = run_bridge(device, io.BytesIO(first + second), output)

        self.assertEqual(count, 2)
        self.assertEqual(device.writes, [first, second])
        self.assertEqual(device.flush_calls, 2)
        self.assertEqual(output.getvalue(), replies)

    def test_truncated_input_packet_is_rejected(self) -> None:
        packet = encode_frame(bytes(512), 1)
        with self.assertRaises(BridgeError):
            run_bridge(FakeSerial(b""), io.BytesIO(packet[:-1]), io.BytesIO())

    def test_short_serial_ack_is_rejected(self) -> None:
        packet = encode_frame(bytes(512), 1)
        with self.assertRaises(BridgeError):
            run_bridge(FakeSerial(b"VF"), io.BytesIO(packet), io.BytesIO())


if __name__ == "__main__":
    unittest.main()
