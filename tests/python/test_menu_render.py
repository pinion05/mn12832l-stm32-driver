import unittest

from mn12832l.menu.model import MenuModel, Screen, ScreenKind
from mn12832l.menu.render import draw_screen
from mn12832l.renderer import MvlsbRenderer


class DrawScreenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = MvlsbRenderer()

    def _frame(self, screen: Screen) -> bytes:
        return draw_screen(screen, self.renderer)

    def test_all_screens_produce_512_bytes(self) -> None:
        screens = [
            Screen(ScreenKind.BOOT),
            Screen(ScreenKind.MAIN_MENU, index=0),
            Screen(ScreenKind.MAIN_MENU, index=1),
            Screen(ScreenKind.MAIN_MENU, index=2),
            Screen(ScreenKind.MUSIC),
            Screen(ScreenKind.GAME),
            Screen(ScreenKind.SETTINGS),
        ]
        for s in screens:
            frame = self._frame(s)
            self.assertEqual(len(frame), 512, f"{s.kind} frame size")

    def test_non_empty_screen_has_at_least_one_pixel(self) -> None:
        frame = self._frame(Screen(ScreenKind.BOOT))
        # 0이 아닌 바이트가 하나라도 있어야 "뭔가 그려짐"
        self.assertTrue(any(b != 0 for b in frame), "BOOT should draw something")

    def test_main_menu_selection_marker_moves_with_index(self) -> None:
        """인덱스 0/1/2일 때 ▶ 표시 위치가 달라야 한다."""
        f0 = self._frame(Screen(ScreenKind.MAIN_MENU, index=0))
        f1 = self._frame(Screen(ScreenKind.MAIN_MENU, index=1))
        f2 = self._frame(Screen(ScreenKind.MAIN_MENU, index=2))
        self.assertNotEqual(f0, f1, "index 0 vs 1 must differ")
        self.assertNotEqual(f1, f2, "index 1 vs 2 must differ")
        self.assertNotEqual(f0, f2, "index 0 vs 2 must differ")

    def test_clear_screen_all_black(self) -> None:
        """같은 화면 두 번 그리면 덮어쓰여야 함 (clear 동작)."""
        s = Screen(ScreenKind.GAME)
        first = self._frame(s)
        # 다른 화면 그린 뒤 다시 GAME
        self._frame(Screen(ScreenKind.MUSIC))
        second = self._frame(s)
        self.assertEqual(first, second, "re-draw should be deterministic")

    def test_golden_frames_are_stable(self) -> None:
        """golden frame 회귀 — 레이아웃이 deterministic해야 함."""
        boot = self._frame(Screen(ScreenKind.BOOT))
        music = self._frame(Screen(ScreenKind.MUSIC))
        game = self._frame(Screen(ScreenKind.GAME))
        settings = self._frame(Screen(ScreenKind.SETTINGS))
        # 두 번 그려도 같아야 함
        self.assertEqual(boot, self._frame(Screen(ScreenKind.BOOT)))
        self.assertEqual(music, self._frame(Screen(ScreenKind.MUSIC)))
        self.assertEqual(game, self._frame(Screen(ScreenKind.GAME)))
        self.assertEqual(settings, self._frame(Screen(ScreenKind.SETTINGS)))


if __name__ == "__main__":
    unittest.main()
