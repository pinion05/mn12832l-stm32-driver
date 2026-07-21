from __future__ import annotations

import sys
import unittest
from pathlib import Path

from mn12832l.protocol import AckStatus, decode_ack, encode_frame
from mn12832l.transport import SubprocessTransport, TransportClosedError


HERE = Path(__file__).resolve().parent


class SubprocessTransportTests(unittest.TestCase):
    def test_one_persistent_child_handles_multiple_frames(self) -> None:
        transport = SubprocessTransport(
            [sys.executable, str(HERE / "fake_bridge.py")], timeout=2.0
        )
        transport.open()
        first_pid = transport.pid

        first = decode_ack(transport.request(encode_frame(bytes(512), 1)))
        second = decode_ack(
            transport.request(encode_frame(bytes([0xFF]) * 512, 2))
        )

        self.assertIs(first.status, AckStatus.OK)
        self.assertIs(second.status, AckStatus.OK)
        self.assertEqual(transport.pid, first_pid)
        transport.close()

    def test_request_requires_open_transport(self) -> None:
        transport = SubprocessTransport(
            [sys.executable, str(HERE / "fake_bridge.py")], timeout=2.0
        )
        with self.assertRaises(TransportClosedError):
            transport.request(encode_frame(bytes(512), 0))

    def test_empty_command_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SubprocessTransport([])


if __name__ == "__main__":
    unittest.main()
