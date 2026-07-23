import unittest

from mn12832l.menu.input import (
    ENCODER_CLICK,
    ENCODER_ROTATE_CCW,
    ENCODER_ROTATE_CW,
    BTN1,
    FakeInputSource,
    InputEvent,
    InputSource,
)


class InputEventTests(unittest.TestCase):
    def test_event_kinds_are_distinct(self) -> None:
        self.assertEqual(len({BTN1, ENCODER_ROTATE_CW, ENCODER_ROTATE_CCW, ENCODER_CLICK}), 4)

    def test_all_seven_events_exist(self) -> None:
        expected = {BTN1, InputEvent.BTN2, InputEvent.BTN3, InputEvent.BTN4,
                    ENCODER_ROTATE_CW, ENCODER_ROTATE_CCW, ENCODER_CLICK}
        self.assertEqual(len(expected), 7)


class FakeInputSourceTests(unittest.TestCase):
    def test_poll_drains_queued_events_in_order(self) -> None:
        source: InputSource = FakeInputSource([ENCODER_ROTATE_CW, ENCODER_CLICK])
        self.assertEqual(source.poll(), [ENCODER_ROTATE_CW])
        self.assertEqual(source.poll(), [ENCODER_CLICK])
        self.assertEqual(source.poll(), [])

    def test_poll_returns_list_type(self) -> None:
        source = FakeInputSource([])
        result = source.poll()
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
