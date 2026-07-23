"""Pluggable input layer — menu does not know who sent the input."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List


class InputEvent(Enum):
    BTN1 = auto()
    BTN2 = auto()
    BTN3 = auto()
    BTN4 = auto()
    ENCODER_ROTATE_CW = auto()
    ENCODER_ROTATE_CCW = auto()
    ENCODER_CLICK = auto()


# 짧은 별명 (스펙 4.1.1)
BTN1 = InputEvent.BTN1
BTN2 = InputEvent.BTN2
BTN3 = InputEvent.BTN3
BTN4 = InputEvent.BTN4
ENCODER_ROTATE_CW = InputEvent.ENCODER_ROTATE_CW
ENCODER_ROTATE_CCW = InputEvent.ENCODER_ROTATE_CCW
ENCODER_CLICK = InputEvent.ENCODER_CLICK


class InputSource(ABC):
    """교체 가능한 입력 부품 약속. poll()은 쌓인 이벤트를 순서대로 돌려준다."""

    @abstractmethod
    def poll(self) -> List[InputEvent]:
        ...


class FakeInputSource(InputSource):
    """테스트/재생용 — 이벤트 리스트를 순서대로 한 번씩 내뱉는 더블."""

    def __init__(self, events: List[InputEvent]) -> None:
        self._events = list(events)

    def poll(self) -> List[InputEvent]:
        if not self._events:
            return []
        return [self._events.pop(0)]
