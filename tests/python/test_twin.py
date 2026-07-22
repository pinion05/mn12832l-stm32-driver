from __future__ import annotations

import io
import os
import subprocess
import sys
import unittest

from mn12832l.display import VfdDisplay
from mn12832l.protocol import AckStatus, decode_ack, encode_frame
from mn12832l.twin import (
    DigitalTwinError,
    DigitalTwinTransport,
    _animate_border_loader,
    border_loader_position,
    decode_pin_trace,
    load_ascii_art_asset,
    render_border_loader_frame,
    render_tui,
    run_digital_twin,
)


def _pixel(frame: bytes, x: int, y: int) -> bool:
    return bool(frame[(y // 8) * 128 + x] & (1 << (y % 8)))


class _InteractiveBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


class DigitalTwinUnitTests(unittest.TestCase):
    def test_border_loader_position_follows_every_outer_edge_and_wraps(self) -> None:
        checks = (
            (0, (0, 0)),
            (127, (127, 0)),
            (128, (127, 1)),
            (158, (127, 31)),
            (159, (126, 31)),
            (285, (0, 31)),
            (286, (0, 30)),
            (315, (0, 1)),
            (316, (0, 0)),
            (-1, (0, 1)),
        )

        for step, expected in checks:
            with self.subTest(step=step):
                self.assertEqual(border_loader_position(step), expected)

    def test_loading_ascii_art_asset_is_packaged_and_rectangular(self) -> None:
        asset = load_ascii_art_asset()

        self.assertEqual(len(asset), 7)
        self.assertTrue(all(len(row) == 41 for row in asset))
        self.assertEqual(asset[0][:5], "#....")
        self.assertEqual(asset[-1][-5:], ".###.")
        self.assertLessEqual(set("".join(asset)), {"#", "."})

    def test_border_loader_frame_composes_wordmark_scan_bar_and_head(self) -> None:
        corner_frame = render_border_loader_frame(0)
        top_frame = render_border_loader_frame(64)

        self.assertEqual(len(corner_frame), 512)
        self.assertTrue(_pixel(corner_frame, 1, 1))
        self.assertFalse(_pixel(top_frame, 1, 1))
        self.assertTrue(_pixel(top_frame, 64, 1))
        self.assertTrue(_pixel(top_frame, 23, 6))
        self.assertFalse(_pixel(top_frame, 25, 6))
        self.assertTrue(_pixel(top_frame, 37, 6))
        self.assertTrue(_pixel(corner_frame, 21, 26))
        self.assertFalse(_pixel(top_frame, 21, 26))
        self.assertTrue(_pixel(top_frame, 85, 26))
        for x, y in ((0, 0), (127, 0), (127, 31), (0, 31)):
            with self.subTest(corner=(x, y)):
                self.assertTrue(_pixel(top_frame, x, y))

    def test_invalid_trace_and_frame_size_are_rejected_before_io(self) -> None:
        with self.assertRaises(DigitalTwinError):
            decode_pin_trace(b"not-a-pin-trace")
        with self.assertRaises(ValueError):
            run_digital_twin(bytes(511), "unused-engine")


class PinTwinIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = os.environ.get("MN12832L_PIN_TWIN")
        if not engine:
            self.skipTest("MN12832L_PIN_TWIN is not configured")
        self.engine = engine

    def test_c_pin_trace_round_trips_every_frame_bit(self) -> None:
        frame = bytes((index * 37 + 11) & 0xFF for index in range(512))

        result = run_digital_twin(frame, self.engine)

        self.assertEqual(result.reconstructed_frame, frame)
        self.assertEqual(result.phases, 43)
        self.assertEqual(result.clock_rises, 43 * 240)
        self.assertEqual(result.latches, 43)
        self.assertEqual(result.gaps, 43)
        self.assertEqual(result.grid_checks, 43)
        self.assertEqual(result.pin_events, 31272)
        self.assertTrue(result.matches_source)

    def test_tui_renders_reconstructed_pixels_and_pin_summary(self) -> None:
        frame = bytearray(512)
        frame[0] = 0x01
        frame[127] = 0x80
        frame[511] = 0x80
        result = run_digital_twin(frame, self.engine)

        output = render_tui(result, color=False, compact=False)

        self.assertIn("DIGITAL TWIN: PASS", output)
        self.assertIn("CLK↑ 10320", output)
        self.assertIn("LAT↑ 43", output)
        self.assertIn("128×32 / 512 bytes", output)
        self.assertIn("▀", output)
        self.assertIn("▄", output)

    def test_loader_frame_round_trips_the_raw_scan_twin(self) -> None:
        frame = render_border_loader_frame(64)

        result = run_digital_twin(frame, self.engine)

        self.assertTrue(result.matches_source)

    def test_decoder_rejects_an_unsafe_virtual_pin_shutdown(self) -> None:
        completed = subprocess.run(
            [self.engine],
            input=bytes(512),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5.0,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        trace = bytearray(completed.stdout)
        self.assertEqual(trace[-8:], bytes((5, 1, 8, 0, 7, 0, 9, 0)))
        trace[-3] = 1

        with self.assertRaisesRegex(DigitalTwinError, "fail-safe"):
            decode_pin_trace(bytes(trace))

    def test_decoder_rejects_pin_output_that_differs_from_source(self) -> None:
        completed = subprocess.run(
            [self.engine],
            input=bytes(512),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5.0,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        trace = bytearray(completed.stdout)
        first_phase = 8 + 7 * 2
        self.assertEqual(trace[first_phase : first_phase + 4], bytes((1, 1, 2, 0)))
        trace[first_phase + 3] = 1

        with self.assertRaisesRegex(DigitalTwinError, "does not match"):
            decode_pin_trace(bytes(trace), source_frame=bytes(512))


class SystemTwinEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = os.environ.get("MN12832L_SYSTEM_TWIN")
        if not engine:
            self.skipTest("MN12832L_SYSTEM_TWIN is not configured")
        self.engine = engine

    def test_vfd_display_drives_the_complete_c_system_twin(self) -> None:
        transport = DigitalTwinTransport([self.engine], timeout=2.0)
        display = VfdDisplay(transport)
        first_frame = render_border_loader_frame(0)
        second_frame = render_border_loader_frame(64)

        with display:
            process_id = transport.pid
            first_present = display.present(first_frame)
            first_twin = transport.last_result
            second_present = display.present(second_frame)
            second_twin = transport.last_result
            self.assertEqual(transport.pid, process_id)

        self.assertEqual(first_present.sequence, 0)
        self.assertEqual(second_present.sequence, 1)
        self.assertIsNotNone(first_twin)
        self.assertIsNotNone(second_twin)
        self.assertEqual(first_twin.reconstructed_frame, first_frame)
        self.assertEqual(second_twin.reconstructed_frame, second_frame)
        self.assertTrue(first_twin.matches_source)
        self.assertTrue(second_twin.matches_source)

    def test_system_twin_nacks_corruption_without_rendering_stale_output(self) -> None:
        transport = DigitalTwinTransport([self.engine], timeout=2.0)
        packet = bytearray(encode_frame(bytes(512), sequence=33))
        packet[200] ^= 0x01

        transport.open()
        try:
            ack = decode_ack(
                transport.request(bytes(packet)), expected_sequence=33
            )
        finally:
            transport.close()

        self.assertIs(ack.status, AckStatus.CRC_ERROR)
        self.assertIsNone(transport.last_result)

    def test_cli_renders_text_through_the_complete_system_twin(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "mn12832l.twin",
                "--engine",
                self.engine,
                "--text",
                "HELLO VFD",
                "--compact",
                "--no-color",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=5.0,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("DIGITAL TWIN: PASS", completed.stdout)
        self.assertIn("HELLO", completed.stdout)

    def test_cli_animates_frames_through_the_complete_system_twin(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "mn12832l.twin",
                "--engine",
                self.engine,
                "--border-loader",
                "--frames",
                "2",
                "--fps",
                "1000",
                "--step-pixels",
                "7",
                "--compact",
                "--no-color",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=5.0,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.count("DIGITAL TWIN: PASS"), 2)
        self.assertIn("Raspberry Pi stack → C system twin", completed.stdout)
        self.assertIn("frame 2/2", completed.stdout)

    def test_interactive_loader_clears_each_frame_and_restores_cursor(self) -> None:
        stream = _InteractiveBuffer()

        return_code = _animate_border_loader(
            self.engine,
            frames=2,
            fps=1000,
            step_pixels=7,
            color=False,
            compact=True,
            stream=stream,
        )

        output = stream.getvalue()
        self.assertEqual(return_code, 0)
        self.assertTrue(output.startswith("\033[?25l\033[2J"))
        self.assertEqual(output.count("\033[H\033[J"), 2)
        self.assertTrue(output.endswith("\033[?25h"))


if __name__ == "__main__":
    unittest.main()
