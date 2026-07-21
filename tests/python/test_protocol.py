from __future__ import annotations

import unittest

from mn12832l.protocol import (
    ACK_PACKET_BYTES,
    FRAME_BYTES,
    FRAME_PACKET_BYTES,
    AckStatus,
    ProtocolError,
    crc16_ccitt,
    decode_ack,
    encode_ack,
    encode_frame,
)


class ProtocolTests(unittest.TestCase):
    def test_crc16_ccitt_false_standard_vector(self) -> None:
        self.assertEqual(crc16_ccitt(b"123456789"), 0x29B1)

    def test_frame_packet_has_stable_binary_layout(self) -> None:
        frame = bytes(range(256)) * 2

        packet = encode_frame(frame, sequence=0x1234)

        self.assertEqual(len(frame), FRAME_BYTES)
        self.assertEqual(len(packet), FRAME_PACKET_BYTES)
        self.assertEqual(packet[:8], b"VF\x01\x01\x34\x12\x00\x02")
        self.assertEqual(packet[8 : 8 + FRAME_BYTES], frame)
        self.assertEqual(
            int.from_bytes(packet[-2:], "little"), crc16_ccitt(packet[:-2])
        )

    def test_frame_encoder_rejects_wrong_size_and_sequence(self) -> None:
        for size in (FRAME_BYTES - 1, FRAME_BYTES + 1):
            with self.subTest(size=size), self.assertRaises(ValueError):
                encode_frame(bytes(size), sequence=0)

        for sequence in (-1, 0x10000):
            with self.subTest(sequence=sequence), self.assertRaises(ValueError):
                encode_frame(bytes(FRAME_BYTES), sequence=sequence)

    def test_ack_round_trip_checks_sequence_status_and_crc(self) -> None:
        packet = encode_ack(sequence=0xBEEF, status=AckStatus.OK)

        self.assertEqual(len(packet), ACK_PACKET_BYTES)
        ack = decode_ack(packet, expected_sequence=0xBEEF)
        self.assertEqual(ack.sequence, 0xBEEF)
        self.assertIs(ack.status, AckStatus.OK)

        with self.assertRaises(ProtocolError):
            decode_ack(packet, expected_sequence=0xBE00)

        corrupt = bytearray(packet)
        corrupt[-1] ^= 0x01
        with self.assertRaises(ProtocolError):
            decode_ack(corrupt)

    def test_ack_decoder_rejects_wrong_length_and_unknown_status(self) -> None:
        with self.assertRaises(ProtocolError):
            decode_ack(bytes(ACK_PACKET_BYTES - 1))

        packet = bytearray(encode_ack(7, AckStatus.OK))
        packet[6] = 0xFE
        crc = crc16_ccitt(packet[:-2])
        packet[-2:] = crc.to_bytes(2, "little")
        with self.assertRaises(ProtocolError):
            decode_ack(packet)


if __name__ == "__main__":
    unittest.main()
