"""VFD 메뉴 상태 기계 — VFD/렌더링에 독립적인 순수 Python 모델."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List

from .input import ENCODER_CLICK, ENCODER_ROTATE_CCW, ENCODER_ROTATE_CW, BTN4, InputEvent

_BOOT_DURATION = 2.0
_MAIN_ITEMS = 3  # MUSIC, GAME, SETTINGS


class ScreenKind(Enum):
    BOOT = auto()
    MAIN_MENU = auto()
    MUSIC = auto()
    GAME = auto()
    SETTINGS = auto()


# MAIN_MENU 인덱스 → 하위 화면 매핑 (스펙 4.2.1)
_MAIN_TARGETS = [ScreenKind.MUSIC, ScreenKind.GAME, ScreenKind.SETTINGS]


@dataclass(frozen=True)
class Screen:
    kind: ScreenKind
    index: int = 0
    boot_elapsed: float = 0.0


class MenuModel:
    """메뉴 상태. 입력 부품(InputSource)을 모름 — 이벤트만 받는다."""

    def __init__(self) -> None:
        self._kind = ScreenKind.BOOT
        self._index = 0
        self._boot_elapsed = 0.0

    def handle_input(self, event: InputEvent) -> None:
        if self._kind is ScreenKind.BOOT:
            return  # 부팅 중 입력 무시 (스펙 4.2.2)
        if self._kind is ScreenKind.MAIN_MENU:
            self._handle_main(event)
        else:
            self._handle_sub(event)

    def _handle_main(self, event: InputEvent) -> None:
        if event is ENCODER_ROTATE_CW:
            self._index = (self._index + 1) % _MAIN_ITEMS
        elif event is ENCODER_ROTATE_CCW:
            self._index = (self._index - 1) % _MAIN_ITEMS
        elif event is ENCODER_CLICK:
            self._kind = _MAIN_TARGETS[self._index]

    def _handle_sub(self, event: InputEvent) -> None:
        if event is BTN4:  # 뒤로 (스펙 4.2.2)
            self._kind = ScreenKind.MAIN_MENU

    def tick(self, dt: float) -> None:
        if self._kind is ScreenKind.BOOT:
            self._boot_elapsed += dt
            if self._boot_elapsed >= _BOOT_DURATION:
                self._kind = ScreenKind.MAIN_MENU

    def current_screen(self) -> Screen:
        return Screen(kind=self._kind, index=self._index, boot_elapsed=self._boot_elapsed)
