"""Screen → 512바이트 MVLSB 프레임. Pillow 기본 폰트 사용 (스펙 2.1, 4.3)."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from ..renderer import MvlsbRenderer
from .model import Screen, ScreenKind

_MAIN_ITEMS = ["MUSIC PLAYER", "MINI GAME", "SETTINGS"]


def _font() -> ImageFont.ImageFont:
    return ImageFont.load_default()


def draw_screen(screen: Screen, renderer: MvlsbRenderer) -> bytes:
    """Screen 데이터를 framebuffer에 그리고 512바이트 snapshot 반환."""
    image = Image.new("1", (128, 32), 0)
    draw = ImageDraw.Draw(image)
    font = _font()

    if screen.kind is ScreenKind.BOOT:
        draw.text((0, 0), "FLOPPYBIRD OS", font=font, fill=1)
        draw.text((0, 12), "v1.0", font=font, fill=1)
    elif screen.kind is ScreenKind.MAIN_MENU:
        for i, label in enumerate(_MAIN_ITEMS):
            y = i * 11
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
