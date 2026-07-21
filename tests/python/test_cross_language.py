from __future__ import annotations

import os
import unittest

from mn12832l.display import VfdDisplay
from mn12832l.protocol import AckStatus, decode_ack, encode_frame
from mn12832l.renderer import MvlsbRenderer
from mn12832l.transport import SubprocessTransport


class CrossLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        peer = os.environ.get("MN12832L_C_PEER")
        if not peer:
            self.skipTest("MN12832L_C_PEER is not configured")
        self.transport = SubprocessTransport([peer], timeout=2.0)

    def test_python_display_drives_persistent_c_receiver(self) -> None:
        display = VfdDisplay(self.transport, renderer=MvlsbRenderer())

        with display:
            first = display.present(bytes(512))
            second = display.present(bytes([0xA5]) * 512)

        self.assertEqual(first.sequence, 0)
        self.assertEqual(second.sequence, 1)
        self.assertEqual(first.attempts, 1)
        self.assertEqual(second.attempts, 1)

    def test_c_receiver_rejects_python_packet_corruption(self) -> None:
        packet = bytearray(encode_frame(bytes(512), sequence=33))
        packet[200] ^= 0x01

        self.transport.open()
        try:
            ack = decode_ack(
                self.transport.request(bytes(packet)), expected_sequence=33
            )
        finally:
            self.transport.close()

        self.assertIs(ack.status, AckStatus.CRC_ERROR)


if __name__ == "__main__":
    unittest.main()
