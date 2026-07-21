from __future__ import annotations

import os
import subprocess
import sys
import unittest

from mn12832l.twin import (
    DigitalTwinError,
    decode_pin_trace,
    render_tui,
    run_digital_twin,
)


class DigitalTwinTests(unittest.TestCase):
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

    def test_invalid_trace_and_frame_size_are_rejected(self) -> None:
        with self.assertRaises(DigitalTwinError):
            decode_pin_trace(b"not-a-pin-trace")
        with self.assertRaises(ValueError):
            run_digital_twin(bytes(511), self.engine)

    def test_cli_renders_text_demo_through_the_pin_twin(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
