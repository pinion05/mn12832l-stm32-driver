"""Screen → 512바이트 MVLSB 프레임. Galmuri7 폰트 사용 (스펙 2.1, 4.3)."""

from __future__ import annotations

import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from ..renderer import MvlsbRenderer
from ..twin import load_ascii_art_asset
from .model import Screen, ScreenKind

_MAIN_ITEMS = ["MUSIC PLAYER", "MINI GAME", "SETTINGS"]

_FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "Galmuri7.ttf")


@lru_cache(maxsize=4)
def _font(size: int = 8) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except (OSError, IOError):
        return ImageFont.load_default()


def _draw_wordmark(draw: ImageDraw.ImageDraw) -> None:
    """패키지에 든 FLOPPYBIRD 워드마크(ASCII 아트)를 128×32 중앙에 그린다.

    에셋은 41×7 픽셀. 화면 한가운데(scale=3)에 오도록 origin을 계산한다.
    남은 하단 공간에 'v1.0' 텍스트를 함께 표시한다.
    """
    rows = load_ascii_art_asset()
    scale = 3
    width = len(rows[0]) * scale
    height = len(rows) * scale
    origin_x = (128 - width) // 2
    origin_y = (32 - height) // 2 - 3  # v1.0 텍스트 공간 확보
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


def draw_screen(screen: Screen, renderer: MvlsbRenderer) -> bytes:
    """Screen 데이터를 framebuffer에 그리고 512바이트 snapshot 반환."""
    image = Image.new("1", (128, 32), 0)
    draw = ImageDraw.Draw(image)
    font = _font(8)

    if screen.kind is ScreenKind.BOOT:
        _draw_wordmark(draw)
        draw.text((54, 26), "v1.0", font=font, fill=1)
    elif screen.kind is ScreenKind.MAIN_MENU:
        for i, label in enumerate(_MAIN_ITEMS):
            y = i * 10
            marker = ">" if i == screen.index else " "
            draw.text((0, y), f"{marker} {label}", font=font, fill=1)
    elif screen.kind is ScreenKind.MUSIC:
        draw.text((0, 0), "NOW PLAYING", font=font, fill=1)
        draw.text((0, 12), "TRACK 01", font=font, fill=1)
        # 재생바 50% (스펙 4.3 — y=24)
        draw.rectangle([0, 24, 127, 28], outline=1, fill=0)  # 전체 테두리
        draw.rectangle([0, 24, 63, 28], outline=1, fill=1)   # 왼쪽 절반 채움
    elif screen.kind is ScreenKind.GAME:
        draw.text((0, 12), "COMING SOON", font=font, fill=1)
    elif screen.kind is ScreenKind.SETTINGS:
        draw.text((0, 0), "BRIGHTNESS 50%", font=font, fill=1)
        draw.text((0, 12), "CONTRAST 50%", font=font, fill=1)

    renderer.load_image(image)
    return renderer.snapshot()
