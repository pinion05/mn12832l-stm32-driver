import unittest

from mn12832l.menu.input import ENCODER_CLICK, ENCODER_ROTATE_CCW, ENCODER_ROTATE_CW, BTN4
from mn12832l.menu.model import MenuModel, ScreenKind


class BootTransitionTests(unittest.TestCase):
    def test_starts_in_boot(self) -> None:
        model = MenuModel()
        self.assertIs(model.current_screen().kind, ScreenKind.BOOT)

    def test_boot_advances_to_main_after_two_seconds(self) -> None:
        model = MenuModel()
        model.tick(1.9)
        self.assertIs(model.current_screen().kind, ScreenKind.BOOT)
        model.tick(0.1)
        self.assertIs(model.current_screen().kind, ScreenKind.MAIN_MENU)

    def test_input_ignored_during_boot(self) -> None:
        model = MenuModel()
        model.handle_input(ENCODER_CLICK)
        self.assertIs(model.current_screen().kind, ScreenKind.BOOT)


class MainMenuTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = MenuModel()
        self.model.tick(2.0)  # BOOT → MAIN

    def test_starts_at_index_zero(self) -> None:
        self.assertEqual(self.model.current_screen().index, 0)

    def test_encoder_cw_increments_index(self) -> None:
        self.model.handle_input(ENCODER_ROTATE_CW)
        self.assertEqual(self.model.current_screen().index, 1)

    def test_encoder_ccw_decrements_index(self) -> None:
        self.model.handle_input(ENCODER_ROTATE_CW)
        self.model.handle_input(ENCODER_ROTATE_CCW)
        self.assertEqual(self.model.current_screen().index, 0)

    def test_encoder_wraps_around_at_end(self) -> None:
        for _ in range(3):  # 3개 항목 → 끝까지 감
            self.model.handle_input(ENCODER_ROTATE_CW)
        self.assertEqual(self.model.current_screen().index, 0)  # 랩어라운드

    def test_encoder_wraps_around_at_start(self) -> None:
        self.model.handle_input(ENCODER_ROTATE_CCW)  # 0 → 마지막
        self.assertEqual(self.model.current_screen().index, 2)

    def test_click_enters_music_at_index_0(self) -> None:
        self.model.handle_input(ENCODER_CLICK)
        self.assertIs(self.model.current_screen().kind, ScreenKind.MUSIC)

    def test_click_enters_game_at_index_1(self) -> None:
        self.model.handle_input(ENCODER_ROTATE_CW)
        self.model.handle_input(ENCODER_CLICK)
        self.assertIs(self.model.current_screen().kind, ScreenKind.GAME)

    def test_click_enters_settings_at_index_2(self) -> None:
        self.model.handle_input(ENCODER_ROTATE_CW)
        self.model.handle_input(ENCODER_ROTATE_CW)
        self.model.handle_input(ENCODER_CLICK)
        self.assertIs(self.model.current_screen().kind, ScreenKind.SETTINGS)


class BackFromSubScreenTests(unittest.TestCase):
    def _enter(self, model: MenuModel, index: int) -> None:
        model.tick(2.0)
        for _ in range(index):
            model.handle_input(ENCODER_ROTATE_CW)
        model.handle_input(ENCODER_CLICK)

    def test_btn4_returns_from_music(self) -> None:
        model = MenuModel()
        self._enter(model, 0)
        model.handle_input(BTN4)
        self.assertIs(model.current_screen().kind, ScreenKind.MAIN_MENU)

    def test_btn4_returns_from_game(self) -> None:
        model = MenuModel()
        self._enter(model, 1)
        model.handle_input(BTN4)
        self.assertIs(model.current_screen().kind, ScreenKind.MAIN_MENU)

    def test_btn4_returns_from_settings(self) -> None:
        model = MenuModel()
        self._enter(model, 2)
        model.handle_input(BTN4)
        self.assertIs(model.current_screen().kind, ScreenKind.MAIN_MENU)

    def test_index_preserved_on_return(self) -> None:
        model = MenuModel()
        self._enter(model, 1)
        model.handle_input(BTN4)
        self.assertEqual(model.current_screen().index, 1)


if __name__ == "__main__":
    unittest.main()
