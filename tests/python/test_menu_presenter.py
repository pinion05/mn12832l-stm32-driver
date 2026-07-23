import os
import unittest

from mn12832l.menu.model import Screen, ScreenKind
from mn12832l.menu.presenter import MenuPresenter


@unittest.skipUnless(
    os.environ.get("MN12832L_SYSTEM_TWIN"),
    "MN12832L_SYSTEM_TWIN is not configured",
)
class PresenterWithSystemTwinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = os.environ["MN12832L_SYSTEM_TWIN"]

    def test_boot_frame_passes_twin_verification(self) -> None:
        presenter = MenuPresenter(engine=self.engine)
        presenter.open()
        try:
            result = presenter.present(Screen(ScreenKind.BOOT))
        finally:
            presenter.close()
        self.assertTrue(result.twin_passed, f"twin failed: {result.error}")
        self.assertEqual(len(result.verified_frame), 512)
        self.assertIsNotNone(result.stats)

    def test_all_screens_pass_twin(self) -> None:
        screens = [
            Screen(ScreenKind.BOOT),
            Screen(ScreenKind.MAIN_MENU, index=0),
            Screen(ScreenKind.MAIN_MENU, index=1),
            Screen(ScreenKind.MAIN_MENU, index=2),
            Screen(ScreenKind.MUSIC),
            Screen(ScreenKind.GAME),
            Screen(ScreenKind.SETTINGS),
        ]
        presenter = MenuPresenter(engine=self.engine)
        presenter.open()
        try:
            for s in screens:
                result = presenter.present(s)
                self.assertTrue(result.twin_passed, f"{s.kind}: {result.error}")
        finally:
            presenter.close()

    def test_identical_screen_skipped_but_returns_last_verified(self) -> None:
        presenter = MenuPresenter(engine=self.engine)
        presenter.open()
        try:
            first = presenter.present(Screen(ScreenKind.GAME))
            second = presenter.present(Screen(ScreenKind.GAME))  # dedup
            self.assertTrue(first.twin_passed)
            self.assertTrue(second.twin_passed)
            self.assertEqual(first.verified_frame, second.verified_frame)
        finally:
            presenter.close()


class PresenterErrorHandlingTests(unittest.TestCase):
    def test_missing_engine_raises_on_open(self) -> None:
        with self.assertRaises(Exception):
            presenter = MenuPresenter(engine="/nonexistent/twin")
            presenter.open()


if __name__ == "__main__":
    unittest.main()
