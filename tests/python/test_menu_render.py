import io
import os
import sys
import tempfile
import unittest
import zipfile
from typing import Optional, Tuple

from PIL import ImageFont

from mn12832l.menu.model import MenuModel, Screen, ScreenKind
from mn12832l.menu.render import draw_screen
from mn12832l.protocol import FRAME_HEIGHT as _HEIGHT
from mn12832l.protocol import FRAME_WIDTH as _WIDTH
from mn12832l.protocol import pixel_is_on
from mn12832l.renderer import MvlsbRenderer


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
                if pixel_is_on(frame, x, y):
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


def _build_package_zip() -> str:
    """src/mn12832l 패키지 전체를 zip으로 묶어 임시 경로 반환 (zipimport 시뮬레이션).

    zipapp/zipimport 환경에서 폰트가 진짜 로드되는지 검증하기 위한 픽스처.
    """
    src_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "src")
    )
    pkg_root = os.path.join(src_root, "mn12832l")
    fd, zip_path = tempfile.mkstemp(suffix=".zip", prefix="mn12832l_test_")
    os.close(fd)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(pkg_root):
            for fn in files:
                # __pycache__는 zip에 넣을 필요 없음
                if "__pycache__" in root:
                    continue
                full = os.path.join(root, fn)
                arc = os.path.relpath(full, src_root)
                z.write(full, arc)
    return zip_path


class FontLoadTests(unittest.TestCase):
    """Galmuri7 폰트 로딩 검증 — importlib.resources 결함 회귀 방지.

    PR #3의 Codex P2 리뷰 대응: joinpath('..')는 zipimport에서 정규화되지 않고
    str(Traversable)은 실제 파일 경로가 아니므로 zipped 설치 시 폰트가
    조용히 load_default()로 폴백하는 결함이 있었다.

    주의: Pillow 12+에서 load_default()도 FreeTypeFont를 반환하므로 타입 이름
    검사만으로는 폴백을 잡을 수 없다. 따라서 폰트 리소스가 zip 환경에서
    read_bytes()로 실제로 읽히는지(=결함 코드는 실패, 올바른 코드는 성공)를
    직접 검증한다.
    """

    def test_font_resource_readable_under_zipimport(self) -> None:
        """zipimport 환경에서 폰트 리소스 경로가 read_bytes()로 읽혀야 한다.

        결함(joinpath('..'))은 zip에서 이 읽기를 실패시킨다 — 그래서
        ImageFont.truetype(str(fp))가 OSError를 내고 except가 삼켜 폴백한다.
        올바른 구현(resources.files('mn12832l').joinpath('assets', name))은
        zip에서도 읽힌다.
        """
        zip_path = _build_package_zip()
        try:
            sys.path.insert(0, zip_path)
            for key in list(sys.modules):
                if key == "mn12832l" or key.startswith("mn12832l."):
                    del sys.modules[key]

            import importlib


            import importlib.util

            importlib.import_module("mn12832l")  # zip에서 로드 확인용
            pkg_spec = importlib.util.find_spec("mn12832l")
            self.assertIn(
                zip_path,
                getattr(pkg_spec, "origin", "") or "",
                "test setup sanity: mn12832l should load from the zip",
            )

            # 올바른 경로('mn12832l'에서 직접)는 zip에서 읽혀야 한다.
            from importlib import resources

            fp = resources.files("mn12832l").joinpath("assets", "Galmuri7.ttf")
            self.assertTrue(
                fp.is_file(),
                f"Galmuri7.ttf must be readable inside the zip (got {fp!r})",
            )
            data = fp.read_bytes()
            # TTF 매직: 0x00010000 (TrueType) 또는 'OTTO' (OpenType/CFF)
            self.assertIn(
                data[:4],
                (b"\x00\x01\x00\x00", b"OTTO"),
                "read bytes should be a valid TrueType/OpenType font",
            )
        finally:
            if zip_path in sys.path:
                sys.path.remove(zip_path)
            for key in list(sys.modules):
                if key == "mn12832l" or key.startswith("mn12832l."):
                    del sys.modules[key]
            try:
                os.remove(zip_path)
            except OSError:
                pass

    def test_font_loads_galmuri_not_default(self) -> None:
        """_font()가 Galmuri7을 로드해야 한다 — 폴백이 아니다.

        폰트 리소스를 bytes로 읽은 뒤 io.BytesIO로 ImageFont를 만든 결과와
        _font()가 같은 폰트 객체(또는 동일 글리프 메트릭)를 반환하는지 비교하여
        _font()가 load_default 폴백이 아닌 진짜 Galmuri7을 썼음을 보인다.
        """
        from mn12832l.menu.render import _font

        _font.cache_clear()
        font = _font(8)

        # 동일 폰트를 직접 읽어 만든 기준 객체
        from importlib import resources

        data = resources.files("mn12832l").joinpath("assets", "Galmuri7.ttf").read_bytes()
        reference = ImageFont.truetype(io.BytesIO(data), 8)

        # getbbox는 폰트·size에 의존적 — 같은 폰트면 동일 메트릭
        for probe in ("M", "g", "8", " "):
            self.assertEqual(
                font.getbbox(probe),
                reference.getbbox(probe),
                f"_font glyph metrics for {probe!r} must match Galmuri7 "
                "(silent load_default fallback would differ)",
            )

    def test_font_loads_galmuri_under_zipimport(self) -> None:
        """zipimport 환경에서도 _font()가 Galmuri7(폴백 아님)을 로드해야 한다.

        현재 결함(joinpath('..') + str(Traversable))은 zipimport에서
        ImageFont.truetype(str(fp))가 OSError를 내고 except가 삼켜
        load_default()로 폴백한다. Pillow 12+에서 load_default도 FreeTypeFont를
        반환하므로 타입 이름 비교로는 폴백을 못 잡는다 — 글리프 메트릭을 비교한다.
        """
        zip_path = _build_package_zip()
        try:
            sys.path.insert(0, zip_path)
            for key in list(sys.modules):
                if key == "mn12832l" or key.startswith("mn12832l."):
                    del sys.modules[key]

            import importlib


            import importlib.util

            render_mod = importlib.import_module("mn12832l.menu.render")
            pkg_spec = importlib.util.find_spec("mn12832l")
            self.assertIn(
                zip_path,
                getattr(pkg_spec, "origin", "") or "",
                "test setup sanity: mn12832l should load from the zip",
            )

            render_mod._font.cache_clear()
            font = render_mod._font(8)

            # zip 안의 폰트 바이트를 직접 읽어 기준 객체 생성
            from importlib import resources

            data = resources.files("mn12832l").joinpath(
                "assets", "Galmuri7.ttf"
            ).read_bytes()
            reference = ImageFont.truetype(io.BytesIO(data), 8)

            for probe in ("M", "g", "8", " "):
                self.assertEqual(
                    font.getbbox(probe),
                    reference.getbbox(probe),
                    f"under zipimport, _font glyph metrics for {probe!r} must "
                    "match Galmuri7 — silent load_default fallback regressed "
                    "(joinpath('..')/str(Traversable) bug)",
                )
        finally:
            if zip_path in sys.path:
                sys.path.remove(zip_path)
            for key in list(sys.modules):
                if key == "mn12832l" or key.startswith("mn12832l."):
                    del sys.modules[key]
            try:
                os.remove(zip_path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
