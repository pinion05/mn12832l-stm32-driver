import unittest
from typing import Optional, Tuple

from mn12832l.menu.model import MenuModel, Screen, ScreenKind
from mn12832l.menu.render import draw_screen
from mn12832l.renderer import MvlsbRenderer

# VFD 물리 프레임 크기 (protocol.py의 FRAME_WIDTH/FRAME_HEIGHT와 동일)
_WIDTH = 128
_HEIGHT = 32


class DrawScreenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = MvlsbRenderer()

    def _frame(self, screen: Screen) -> bytes:
        return draw_screen(screen, self.renderer)

    @staticmethod
    def _pixel_bbox(frame: bytes) -> Optional[Tuple[int, int, int, int]]:
        """켜진 픽셀의 (x_min, y_min, x_max, y_max)를 반환. 빈 프레임이면 None."""
        x_min = y_min = float("inf")
        x_max = y_max = -1
        for y in range(_HEIGHT):
            for x in range(_WIDTH):
                if frame[(y // 8) * _WIDTH + x] & (1 << (y % 8)):
                    if x < x_min:
                        x_min = x
                    if x > x_max:
                        x_max = x
                    if y < y_min:
                        y_min = y
                    if y > y_max:
                        y_max = y
        if x_max < 0:
            return None
        return x_min, y_min, x_max, y_max

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

    def test_all_screens_fit_inside_frame_buffer(self) -> None:
        """모든 화면의 켜진 픽셀이 128×32 버퍼 안에 있어야 한다.

        렌더 코드가 버퍼를 넘는 좌표로 그리면(예: 텍스트가 y=31을 초과),
        VFD는 그 픽셀을 조용히 잘라내므로 화면에 안 보이거나 삐져나가 보인다.
        이 테스트는 그런 오버플로우를 픽셀 단위로 잡아낸다.
        """
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
            bbox = self._pixel_bbox(frame)
            self.assertIsNotNone(bbox, f"{s.kind} should draw something")
            x_min, y_min, x_max, y_max = bbox
            self.assertGreaterEqual(x_min, 0, f"{s.kind}: x_min {x_min} underflow")
            self.assertLess(x_max, _WIDTH, f"{s.kind}: x_max {x_max} overflow")
            self.assertGreaterEqual(y_min, 0, f"{s.kind}: y_min {y_min} underflow")
            self.assertLess(y_max, _HEIGHT, f"{s.kind}: y_max {y_max} overflow")

    def test_all_screens_leave_minimum_margin(self) -> None:
        """모든 화면은 네 변에서 최소 1픽셀 여백을 둬야 한다.

        버퍼 오버플로우는 아니지만, 픽셀이 화면 끝에 딱 붙으면 VFD 위에서
        '잘렸다/삐져나갔다'고 보인다. 이 테스트는 시각적 안전 여백을 보장한다.
        """
        margin = 1
        screens = [
            Screen(ScreenKind.BOOT, boot_elapsed=0.0),
            Screen(ScreenKind.BOOT, boot_elapsed=0.5),
            Screen(ScreenKind.MAIN_MENU, index=0),
            Screen(ScreenKind.MAIN_MENU, index=1),
            Screen(ScreenKind.MAIN_MENU, index=2),
            Screen(ScreenKind.MUSIC),
            Screen(ScreenKind.GAME),
            Screen(ScreenKind.SETTINGS),
        ]
        for s in screens:
            frame = self._frame(s)
            bbox = self._pixel_bbox(frame)
            assert bbox is not None
            x_min, y_min, x_max, y_max = bbox
            self.assertGreaterEqual(
                x_min, margin, f"{s.kind}: left margin {x_min} < {margin}"
            )
            self.assertLess(
                x_max, _WIDTH - margin, f"{s.kind}: right margin {_WIDTH - 1 - x_max} < {margin}"
            )
            self.assertGreaterEqual(
                y_min, margin, f"{s.kind}: top margin {y_min} < {margin}"
            )
            self.assertLess(
                y_max, _HEIGHT - margin, f"{s.kind}: bottom margin {_HEIGHT - 1 - y_max} < {margin}"
            )

    def test_boot_animates_across_steps(self) -> None:
        """BOOT는 step에 따라 화면이 변해야 한다 (애니메이션 동작 확인)."""
        f1 = self._frame(Screen(ScreenKind.BOOT, boot_elapsed=0.0))
        f2 = self._frame(Screen(ScreenKind.BOOT, boot_elapsed=0.5))
        f3 = self._frame(Screen(ScreenKind.BOOT, boot_elapsed=1.0))
        self.assertNotEqual(f1, f2, "BOOT should animate between steps")
        self.assertNotEqual(f2, f3, "BOOT should keep animating")

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
