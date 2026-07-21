from __future__ import annotations

import unittest

import mn12832l
from mn12832l.display import (
    DisplayClosedError,
    DisplayError,
    FrameRejectedError,
)
from mn12832l.protocol import ProtocolError
from mn12832l.transport import (
    TransportClosedError,
    TransportError,
    TransportTimeoutError,
)


class PackageApiTests(unittest.TestCase):
    def test_public_exceptions_are_reexported(self) -> None:
        expected = {
            "DisplayClosedError": DisplayClosedError,
            "DisplayError": DisplayError,
            "FrameRejectedError": FrameRejectedError,
            "ProtocolError": ProtocolError,
            "TransportClosedError": TransportClosedError,
            "TransportError": TransportError,
            "TransportTimeoutError": TransportTimeoutError,
        }

        for name, exception_type in expected.items():
            with self.subTest(name=name):
                self.assertIs(getattr(mn12832l, name), exception_type)
                self.assertIn(name, mn12832l.__all__)


if __name__ == "__main__":
    unittest.main()
