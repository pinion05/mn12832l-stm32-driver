"""Tkinter 위젯 → InputEvent 어댑터. 내부 FIFO 큐로 poll/event 간극 해소 (스펙 4.1.2)."""

from __future__ import annotations

from collections import deque
from tkinter import Button, Misc
from typing import List

from .input import InputEvent, InputSource


class TkinterSource(InputSource):
    """Tkinter 콜백(이벤트)을 poll 기반 InputSource로 변환."""

    def __init__(self) -> None:
        self._queue: "deque[InputEvent]" = deque()

    def _enqueue(self, event: InputEvent) -> None:
        self._queue.append(event)

    def poll(self) -> List[InputEvent]:
        events = list(self._queue)
        self._queue.clear()
        return events

    # --- 위젯 생성 헬퍼 (command 콜백이 큐에 push) ---

    def make_button(self, parent: Misc, event: InputEvent, text: str) -> Button:
        return Button(parent, text=text, command=lambda: self._enqueue(event))

    def make_encoder_rotate(self, parent: Misc, direction: InputEvent, text: str) -> Button:
        return Button(parent, text=text, command=lambda: self._enqueue(direction))

    def make_encoder_click(self, parent: Misc) -> Button:
        return Button(parent, text="다이얼 누르기", command=lambda: self._enqueue(InputEvent.ENCODER_CLICK))
