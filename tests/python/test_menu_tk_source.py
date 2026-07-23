import unittest
from collections import deque

from mn12832l.menu.input import BTN1, ENCODER_CLICK, ENCODER_ROTATE_CW
from mn12832l.menu.tk_source import TkinterSource


class TkinterSourceQueueTests(unittest.TestCase):
    def test_starts_empty(self) -> None:
        source = TkinterSource()
        self.assertEqual(source.poll(), [])

    def test_enqueue_then_poll_drains_fifo(self) -> None:
        # poll()은 큐를 drain-all 하되, FIFO 순서를 보존한다 (스펙 4.1.2).
        source = TkinterSource()
        source._enqueue(BTN1)
        source._enqueue(ENCODER_ROTATE_CW)
        self.assertEqual(source.poll(), [BTN1, ENCODER_ROTATE_CW])
        self.assertEqual(source.poll(), [])

    def test_poll_drains_all_at_once_if_multiple(self) -> None:
        source = TkinterSource()
        source._enqueue(BTN1)
        source._enqueue(ENCODER_CLICK)
        # 두 이벤트가 한 프레임에 몰려도 FIFO 순서 보존
        self.assertEqual(source.poll(), [BTN1, ENCODER_CLICK])

    def test_internal_queue_is_deque(self) -> None:
        source = TkinterSource()
        self.assertIsInstance(source._queue, deque)


if __name__ == "__main__":
    unittest.main()
