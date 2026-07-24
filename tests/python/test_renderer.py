from __future__ import annotations

import unittest

from PIL import Image, ImageDraw

from mn12832l.protocol import FRAME_BYTES
from mn12832l.renderer import MvlsbRenderer


class RendererTests(unittest.TestCase):
    def test_corner_pixels_use_the_vfd_native_512_byte_layout(self) -> None:
        renderer = MvlsbRenderer()
        checks = (
            (0, 0, 0, 0x01),
            (127, 7, 127, 0x80),
            (0, 8, 128, 0x01),
            (127, 31, 511, 0x80),
        )

        for x, y, byte_index, mask in checks:
            with self.subTest(x=x, y=y):
                renderer.clear()
                renderer.framebuffer.pixel(x, y, 1)
                frame = renderer.snapshot()
                self.assertEqual(len(frame), FRAME_BYTES)
                self.assertEqual(frame[byte_index], mask)
                self.assertEqual(sum(value != 0 for value in frame), 1)

    def test_render_clears_previous_frame_before_drawing_model(self) -> None:
        renderer = MvlsbRenderer()
        renderer.framebuffer.pixel(1, 1, 1)

        frame = renderer.render(
            {"x": 10, "y": 9},
            lambda model, fb: fb.pixel(model["x"], model["y"], 1),
        )

        self.assertEqual(frame[1], 0)
        self.assertEqual(frame[128 + 10], 0x02)

    def test_pillow_mode_one_image_is_packed_without_custom_converter(self) -> None:
        image = Image.new("1", (128, 32), 0)
        draw = ImageDraw.Draw(image)
        draw.point((0, 0), fill=1)
        draw.point((127, 31), fill=1)
        draw.line((1, 8, 3, 8), fill=1)

        renderer = MvlsbRenderer()
        renderer.load_image(image)
        frame = renderer.snapshot()

        self.assertEqual(frame[0], 0x01)
        self.assertEqual(frame[511], 0x80)
        self.assertEqual(frame[129:132], b"\x01\x01\x01")

    def test_wrong_sized_image_is_rejected(self) -> None:
        renderer = MvlsbRenderer()
        with self.assertRaises(ValueError):
            renderer.load_image(Image.new("1", (127, 32), 0))


if __name__ == "__main__":
    unittest.main()
