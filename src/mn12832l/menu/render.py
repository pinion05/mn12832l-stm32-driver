"""Screen → 512바이트 MVLSB 프레임. Galmuri7 폰트 사용 (스펙 2.1, 4.3)."""

from __future__ import annotations

import io
from functools import lru_cache
from importlib import resources

from PIL import Image, ImageDraw, ImageFont

from ..protocol import FRAME_HEIGHT, FRAME_WIDTH
from ..renderer import MvlsbRenderer
from ..twin import load_ascii_art_asset
from .model import Screen, ScreenKind

_MAIN_ITEMS = ["MUSIC PLAYER", "MINI GAME", "SETTINGS"]


@lru_cache(maxsize=4)
def _font(size: int = 8) -> ImageFont.ImageFont:
    """패키지에 든 Galmuri7.ttf를 importlib.resources로 로드 (wheel/zipapp 호환).

    assets는 mn12832l 패키지 루트에 있으므로 상위 디렉토리 순회(joinpath('..')) 없이
    'mn12832l'에서 직접 참조한다 — joinpath('..')는 zipapp/zipimport 안에서
    정규화되지 않아 실패한다.

    리소스를 read_bytes()로 읽어 io.BytesIO에 담아 Pillow에 전달한다. 이 방식은
    (1) str(Traversable)이 실제 파일 경로가 아니라 zip 안 경로라 ImageFont.truetype
    이 못 여는 문제를 피하고, (2) as_file() 컨텍스트 매니저의 임시 파일 수명 문제를
    회피하면서 @lru_cache를 유지할 수 있게 한다 (BytesIO는 seek(0) 후 재사용 가능).
    """
    try:
        # joinpath를 체인으로 넘긴다 — Python 3.9 zipimport에서
        # zipfile.Path.joinpath가 인자를 하나만 받으므로 묶어 넘기면 TypeError가 난다.
        data = resources.files("mn12832l").joinpath(
            "assets"
        ).joinpath("Galmuri7.ttf").read_bytes()
        return ImageFont.truetype(io.BytesIO(data), size)
    except OSError:
        # IOError/FileNotFoundError는 OSError의 별칭/하위 클래스라 하나로 충분.
        return ImageFont.load_default()


def _draw_wordmark(draw: ImageDraw.ImageDraw) -> None:
    """패키지에 든 FLOPPYBIRD 워드마크(ASCII 아트)를 상단 중앙에 그린다.

    에셋은 41×7 픽셀. scale=2(82×14)로 그린다.
    """
    rows = load_ascii_art_asset()
    scale = 2
    width = len(rows[0]) * scale
    origin_x = (FRAME_WIDTH - width) // 2
    origin_y = 2
    for row_index, row in enumerate(rows):
        for column_index, pixel in enumerate(row):
            if pixel != "#":
                continue
            left = origin_x + column_index * scale
            top = origin_y + row_index * scale
            draw.rectangle(
                (left, top, left + scale - 1, top + scale - 1),
                fill=1,
            )


def _draw_loading_bar(draw: ImageDraw.ImageDraw, step: int) -> None:
    """워드마크 아래에 움직이는 스캔바를 그린다 (패키지 로딩 애니메이션 재사용).

    바 영역은 y=20~24. 바 안을 채우는 세로선이 step에 따라 좌→우로 순환한다.
    """
    bar_left = 20
    bar_right = FRAME_WIDTH - 21
    bar_top = 20
    bar_bottom = 24
    draw.rectangle((bar_left, bar_top, bar_right, bar_bottom), outline=1)
    inner_left = bar_left + 1
    inner_width = bar_right - bar_left - 1
    for offset in range(18):
        x = inner_left + (step + offset) % inner_width
        draw.line((x, bar_top + 2, x, bar_bottom - 2), fill=1)


def draw_screen(screen: Screen, renderer: MvlsbRenderer) -> bytes:
    """Screen 데이터를 framebuffer에 그리고 512바이트 snapshot 반환."""
    image = Image.new("1", (128, 32), 0)
    draw = ImageDraw.Draw(image)
    font = _font(8)

    if screen.kind is ScreenKind.BOOT:
        # 패키지 로딩 애니메이션: 워드마크(정적) + 스캔바(좌→우 순환).
        # step은 boot_elapsed(초)를 100fps로 변환 — 기본 20fps의 5배속.
        step = int(screen.boot_elapsed * 100)
        _draw_wordmark(draw)
        _draw_loading_bar(draw, step)
    elif screen.kind is ScreenKind.MAIN_MENU:
        # 항목 3개를 y=3/12/21에 배치 → 폰트(8px) 포함 y~29, 바닥 여백 2확보
        for i, label in enumerate(_MAIN_ITEMS):
            y = 3 + i * 9
            marker = ">" if i == screen.index else " "
            draw.text((1, y), f"{marker} {label}", font=font, fill=1)
    elif screen.kind is ScreenKind.MUSIC:
        draw.text((1, 2), "NOW PLAYING", font=font, fill=1)
        draw.text((1, 12), "TRACK 01", font=font, fill=1)
        # 재생바 50% — 양끝 1px 여백 (스펙 4.3 — y=24)
        draw.rectangle([1, 24, 126, 28], outline=1, fill=0)  # 전체 테두리
        draw.rectangle([1, 24, 63, 28], outline=1, fill=1)   # 왼쪽 절반 채움
    elif screen.kind is ScreenKind.GAME:
        draw.text((1, 12), "COMING SOON", font=font, fill=1)
    elif screen.kind is ScreenKind.SETTINGS:
        draw.text((1, 2), "BRIGHTNESS 50%", font=font, fill=1)
        draw.text((1, 12), "CONTRAST 50%", font=font, fill=1)

    renderer.load_image(image)
    return renderer.snapshot()
