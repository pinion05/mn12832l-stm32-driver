"""Tkinter 미리보기 창. root.after() 기반 단일 루프 (스펙 4.5)."""

from __future__ import annotations

import time
import tkinter as tk
from typing import Optional

from .input import BTN1, BTN2, BTN3, BTN4, ENCODER_ROTATE_CCW, ENCODER_ROTATE_CW
from .model import MenuModel
from .presenter import MenuPresenter
from .tk_source import TkinterSource

_SCALE = 6  # 128×32 → 768×192
_WIDTH = 128
_HEIGHT = 32
_FPS_MS = 50  # 20fps

_VFD_ON = "#33ffcc"
_VFD_OFF = "#02060a"


class MenuApp:
    def __init__(self, root: tk.Tk, engine: str) -> None:
        self._root = root
        self._model = MenuModel()
        self._source = TkinterSource()
        self._presenter = MenuPresenter(engine=engine)
        self._canvas: Optional[tk.Canvas] = None
        self._status: Optional[tk.Label] = None
        self._screen_label: Optional[tk.Label] = None
        self._last_tick_time = 0.0
        self._closed = False

    def setup(self) -> None:
        self._root.title("Floppybird Menu Preview")
        self._canvas = tk.Canvas(
            self._root, width=_WIDTH * _SCALE, height=_HEIGHT * _SCALE,
            bg=_VFD_OFF, highlightthickness=1, highlightbackground="#143a32",
        )
        self._canvas.pack(padx=12, pady=12)

        self._status = tk.Label(self._root, text="...", fg=_VFD_ON, bg="#04080a",
                                font=("Menlo", 11), anchor="w", justify="left")
        self._status.pack(fill="x", padx=12)

        # 버튼 행
        btn_frame = tk.Frame(self._root)
        btn_frame.pack(pady=6)
        for event, label in [(BTN1, "BTN1"), (BTN2, "BTN2"), (BTN3, "BTN3"),
                             (BTN4, "BTN4 (뒤로)")]:
            self._source.make_button(btn_frame, event, label).pack(side="left", padx=4)

        # 엔코더 행
        enc_frame = tk.Frame(self._root)
        enc_frame.pack(pady=6)
        self._source.make_encoder_rotate(enc_frame, ENCODER_ROTATE_CCW, "◀ 다이얼").pack(side="left", padx=4)
        self._source.make_encoder_click(enc_frame).pack(side="left", padx=4)
        self._source.make_encoder_rotate(enc_frame, ENCODER_ROTATE_CW, "다이얼 ▶").pack(side="left", padx=4)

        self._screen_label = tk.Label(self._root, text="Screen: BOOT", fg="#7aa399",
                                      bg="#04080a", font=("Menlo", 10))
        self._screen_label.pack(pady=4)

        self._root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start(self) -> None:
        self._presenter.open()
        self._last_tick_time = time.monotonic()
        self._root.after(_FPS_MS, self.tick)

    def tick(self) -> None:
        if self._closed:
            return
        now = time.monotonic()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        # 1. 입력 소비 (스펙 4.5 — 폴링 단계가 명시적으로 먼저)
        for event in self._source.poll():
            self._model.handle_input(event)

        # 2. 시간 기반 전이
        self._model.tick(dt)

        # 3-5. 렌더 + 검증 + 표시
        result = self._presenter.present(self._model.current_screen())
        self._draw_frame(result.verified_frame, result.twin_passed, result.error, result.stats)

        self._root.after(_FPS_MS, self.tick)

    def _draw_frame(self, frame: bytes, passed: bool, error: Optional[str],
                    stats: Optional[dict]) -> None:
        if self._canvas is None:
            return
        self._canvas.delete("all")
        color = _VFD_ON if passed else "#ff5c6c"

        # 512바이트 → 픽셀
        for y in range(_HEIGHT):
            byte_row = y // 8
            bit = y % 8
            for x in range(_WIDTH):
                on = bool(frame[byte_row * _WIDTH + x] & (1 << bit))
                if on:
                    self._canvas.create_rectangle(
                        x * _SCALE, y * _SCALE, (x + 1) * _SCALE, (y + 1) * _SCALE,
                        fill=color, outline="",
                    )

        if not passed and error:
            self._canvas.create_text(
                _WIDTH * _SCALE // 2, _HEIGHT * _SCALE // 2,
                text=f"FAIL: {error[:40]}", fill="#ff5c6c", font=("Menlo", 10),
            )

        status_lines = []
        if passed and stats:
            status_lines.append("DIGITAL TWIN: PASS")
            status_lines.append(
                f"PHASE {stats.get('phases','?')} | "
                f"CLK {stats.get('clock_rises','?')} | "
                f"LAT {stats.get('latches','?')}"
            )
        elif error:
            status_lines.append(f"FAIL: {error[:50]}")
        else:
            status_lines.append("waiting...")
        if self._status is not None:
            self._status.config(text="\n".join(status_lines))

        if self._screen_label is not None:
            self._screen_label.config(text=f"Screen: {self._model.current_screen().kind.name}")

    def on_close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._presenter.close()
        finally:
            self._root.destroy()
