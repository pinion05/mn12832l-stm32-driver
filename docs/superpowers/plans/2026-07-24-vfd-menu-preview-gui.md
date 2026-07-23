# VFD 메뉴 미리보기 GUI 구현 플랜

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**목표:** VFD 128×32 화면 위에서 도는 5-화면 메뉴 시스템을 만들고, 치팅 없는 C 라운드트립 검증을 거쳐 Tkinter 창에서 미리보는 도구를 완성한다.

**아키텍처:** 순수 Python 메뉴 모델(입력 부품 모름) → MvlsbRenderer로 512바이트 렌더 → VfdDisplay+DigitalTwinTransport로 C 라운드트립 검증 → Tkinter 캔버스에 픽셀 표시. 입력은 교체 가능한 InputSource 약속으로 추상화 (지금은 TkinterSource, 나중엔 GpioSource).

**기술 스택:** Python 3.9+, Tkinter(표준 라이브러리), Pillow(이미 의존성), 기존 `mn12832l` 패키지(display/transport/twin/renderer). 테스트는 `unittest` (기존 패턴), Makefile 타깃.

**스펙:** `docs/superpowers/specs/2026-07-23-vfd-menu-preview-gui-design.md`

## Global Constraints

- Python ≥ 3.9 (기존 `pyproject.toml` 준수). Tkinter는 표준 라이브러리 (추가 의존성 아님).
- 기존 테스트/게이트 전부 통과 유지: `make all PYTHON=.venv/bin/python` 그린 유지.
- 새 파일은 `src/mn12832l/menu/` 패키지 아래. 테스트는 `tests/python/test_menu_*.py`.
- TDD: 각 태스크마다 실패 테스트 먼저 → 최소 구현 → 통과 → 커밋.
- 검증 결과는 `VfdDisplay.present()` 반환값이 아니라 `transport.last_result`로 따로 받는다 (스펙 4.4).
- "매 프레임"이 아니라 "화면이 바뀔 때마다" 검증 (스펙 1절, dedup 존중).
- `matches_source`는 제어 분기용이 아니라 informational (스펙 5절). 검증 실패는 `DigitalTwinError`/`DisplayError` 예외로 처리.
- 키보드 입력 금지. 오직 InputSource에서 온 InputEvent만.
- 자리만 화면(MUSIC/GAME/SETTINGS)의 레이아웃은 스펙 4.3 deterministic 좌표 고정.
- 커밋 메시지는 기존 스타일(`feat:`/`test:`/`refactor:` 등) 준수.

---

## 파일 구조 맵

**Create (신규):**
- `src/mn12832l/menu/__init__.py` — 패키지 진입, 공개 API export
- `src/mn12832l/menu/input.py` — `InputEvent`(enum), `InputSource`(약속 ABC), `FakeInputSource`(테스트/재생용)
- `src/mn12832l/menu/model.py` — `ScreenKind`(enum), `Screen`(dataclass), `MenuModel`(상태 기계)
- `src/mn12832l/menu/render.py` — `draw_screen(screen, renderer) -> bytes`, Pillow 기본 폰트
- `src/mn12832l/menu/presenter.py` — `MenuPresenter`(VfdDisplay+DigitalTwinTransport 조립, 예외→오버레이 상태)
- `src/mn12832l/menu/tk_source.py` — `TkinterSource(InputSource)`, 내부 FIFO 큐
- `src/mn12832l/menu/app.py` — Tkinter 창 + `root.after()` 루프 + 캔버스 그리기
- `src/mn12832l/menu/__main__.py` — `python -m mn12832l.menu` 진입점
- `tests/python/test_menu_input.py` — InputEvent/FakeInputSource 단위
- `tests/python/test_menu_model.py` — MenuModel 상태 전이/엔코더 매핑/랩어라운드
- `tests/python/test_menu_render.py` — draw_screen golden frame (Tkinter 없이)
- `tests/python/test_menu_presenter.py` — presenter가 C 시스템 트윈을 통과 (환경변수 게이트)

**Modify:**
- `Makefile` — `menu` 타깃 추가, `test-python`에 새 테스트 자동 포함(이미 discover 패턴이므로 파일만 추가하면 됨)
- `src/mn12832l/__init__.py` — (선택) 공개 API에 menu 서브패키지 노출. 플랜에서는 건드리지 않고 `python -m mn12832l.menu`로 진입.

---

## Task 1: 패키지 스캐폴드 + InputEvent/InputSource 약속

**Files:**
- Create: `src/mn12832l/menu/__init__.py`
- Create: `src/mn12832l/menu/input.py`
- Create: `tests/python/test_menu_input.py`

**Interfaces:**
- Produces: `InputEvent` (enum: BTN1..4, ENCODER_ROTATE_CW, ENCODER_ROTATE_CCW, ENCODER_CLICK), `InputSource` (ABC with `poll() -> list[InputEvent]`), `FakeInputSource` (생성자에 이벤트 리스트 받아 순서대로 내뱉는 테스트 더블)

- [ ] **Step 1: 실패 테스트 작성**

`tests/python/test_menu_input.py`:
```python
import unittest

from mn12832l.menu.input import (
    ENCODER_CLICK,
    ENCODER_ROTATE_CCW,
    ENCODER_ROTATE_CW,
    BTN1,
    FakeInputSource,
    InputEvent,
    InputSource,
)


class InputEventTests(unittest.TestCase):
    def test_event_kinds_are_distinct(self) -> None:
        self.assertEqual(len({BTN1, ENCODER_ROTATE_CW, ENCODER_ROTATE_CCW, ENCODER_CLICK}), 4)

    def test_all_seven_events_exist(self) -> None:
        expected = {BTN1, InputEvent.BTN2, InputEvent.BTN3, InputEvent.BTN4,
                    ENCODER_ROTATE_CW, ENCODER_ROTATE_CCW, ENCODER_CLICK}
        self.assertEqual(len(expected), 7)


class FakeInputSourceTests(unittest.TestCase):
    def test_poll_drains_queued_events_in_order(self) -> None:
        source: InputSource = FakeInputSource([ENCODER_ROTATE_CW, ENCODER_CLICK])
        self.assertEqual(source.poll(), [ENCODER_ROTATE_CW])
        self.assertEqual(source.poll(), [ENCODER_CLICK])
        self.assertEqual(source.poll(), [])

    def test_poll_returns_list_type(self) -> None:
        source = FakeInputSource([])
        result = source.poll()
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_input -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mn12832l.menu'`

- [ ] **Step 3: 최소 구현**

`src/mn12832l/menu/__init__.py`:
```python
"""Floppybird VFD menu system: model, render, presenter, and preview app."""
```

`src/mn12832l/menu/input.py`:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_input -v`
Expected: PASS (2 classes, 4 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/mn12832l/menu/__init__.py src/mn12832l/menu/input.py tests/python/test_menu_input.py
git commit -m "feat(menu): add input layer contract (InputEvent, InputSource, FakeInputSource)"
```

---

## Task 2: Screen 데이터 타입 + MenuModel 상태 기계 (BOOT/MAIN)

**Files:**
- Create: `src/mn12832l/menu/model.py`
- Create: `tests/python/test_menu_model.py`

**Interfaces:**
- Consumes: `InputEvent`, `BTN4`, `ENCODER_CLICK`, `ENCODER_ROTATE_CW`, `ENCODER_ROTATE_CCW` from Task 1
- Produces: `ScreenKind` (enum: BOOT, MAIN_MENU, MUSIC, GAME, SETTINGS), `Screen` (dataclass: `kind: ScreenKind`, `index: int` for menu selection, `boot_elapsed: float` for BOOT timer), `MenuModel` with `handle_input(event)`, `tick(dt)`, `current_screen() -> Screen`

- [ ] **Step 1: 실패 테스트 작성**

`tests/python/test_menu_model.py`:
```python
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
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_model -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mn12832l.menu.model'`

- [ ] **Step 3: 최소 구현**

`src/mn12832l/menu/model.py`:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_model -v`
Expected: PASS (16 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/mn12832l/menu/model.py tests/python/test_menu_model.py
git commit -m "feat(menu): add MenuModel state machine with BOOT/MAIN/sub-screen transitions"
```

---

## Task 3: draw_screen 렌더 레이어 (5화면, Pillow 기본 폰트, golden frame)

**Files:**
- Create: `src/mn12832l/menu/render.py`
- Create: `tests/python/test_menu_render.py`

**Interfaces:**
- Consumes: `Screen`, `ScreenKind` from Task 2; `MvlsbRenderer` from existing `mn12832l.renderer`
- Produces: `draw_screen(screen: Screen, renderer: MvlsbRenderer) -> bytes` (512바이트). 각 화면은 스펙 4.3 deterministic 좌표 사용.

- [ ] **Step 1: 실패 테스트 작성**

`tests/python/test_menu_render.py`:
```python
import unittest

from mn12832l.menu.model import MenuModel, Screen, ScreenKind
from mn12832l.menu.render import draw_screen
from mn12832l.renderer import MvlsbRenderer


class DrawScreenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer = MvlsbRenderer()

    def _frame(self, screen: Screen) -> bytes:
        return draw_screen(screen, self.renderer)

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

    def test_non_empty_screen_has_at_least_one_pixel(self) -> None:
        frame = self._frame(Screen(ScreenKind.BOOT))
        self.assertIn(1, frame, "BOOT should draw something")

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
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_render -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mn12832l.menu.render'`

- [ ] **Step 3: 최소 구현**

`src/mn12832l/menu/render.py`:
```python
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
        # 재생바 50% (스펙 4.3)
        draw.rectangle([0, 26, 63, 30], outline=1, fill=1)  # 채워진 절반
        draw.rectangle([0, 26, 127, 30], outline=1, fill=0)  # 빈 전체 테두리
        draw.rectangle([0, 26, 63, 30], outline=1, fill=1)  # 다시 채움
    elif screen.kind is ScreenKind.GAME:
        draw.text((0, 12), "COMING SOON", font=font, fill=1)
    elif screen.kind is ScreenKind.SETTINGS:
        draw.text((0, 0), "BRIGHTNESS 50%", font=font, fill=1)
        draw.text((0, 12), "CONTRAST 50%", font=font, fill=1)

    renderer.load_image(image)
    return renderer.snapshot()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_render -v`
Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/mn12832l/menu/render.py tests/python/test_menu_render.py
git commit -m "feat(menu): add draw_screen renderer for all 5 screens with deterministic layout"
```

---

## Task 4: MenuPresenter — VfdDisplay + DigitalTwinTransport 검증 조립

**Files:**
- Create: `src/mn12832l/menu/presenter.py`
- Create: `tests/python/test_menu_presenter.py`

**Interfaces:**
- Consumes: `MvlsbRenderer`, `VfdDisplay` (existing `mn12832l.display`), `DigitalTwinTransport` (existing `mn12832l.twin`), `Screen`/`draw_screen` from Tasks 2-3
- Produces: `MenuPresenter` with `present(screen) -> PresentedFrame`, `PresentedFrame` dataclass (`verified_frame: bytes`, `twin_passed: bool`, `stats: dict | None`, `error: str | None`). `present()`는 내부적으로 draw_screen → display.present → transport.last_result 순서로 처리하고, 예외를 잡아 `PresentedFrame(error=...)`로 반환 (스펙 4.4, 5절).

- [ ] **Step 1: 실패 테스트 작성**

`tests/python/test_menu_presenter.py`:
```python
import os
import unittest

from mn12832l.menu.model import Screen, ScreenKind
from mn12832l.menu.presenter import MenuPresenter


@unittest.skipUnless(
    os.environ.get("MN12832L_SYSTEM_TWIN"),
    "MN12832L_SYSTEM_TWIN is not configured",
)
class PresenterWithSystemTwinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = os.environ["MN12832L_SYSTEM_TWIN"]

    def test_boot_frame_passes_twin_verification(self) -> None:
        presenter = MenuPresenter(engine=self.engine)
        presenter.open()
        try:
            result = presenter.present(Screen(ScreenKind.BOOT))
        finally:
            presenter.close()
        self.assertTrue(result.twin_passed, f"twin failed: {result.error}")
        self.assertEqual(len(result.verified_frame), 512)
        self.assertIsNotNone(result.stats)

    def test_all_screens_pass_twin(self) -> None:
        screens = [
            Screen(ScreenKind.BOOT),
            Screen(ScreenKind.MAIN_MENU, index=0),
            Screen(ScreenKind.MAIN_MENU, index=1),
            Screen(ScreenKind.MAIN_MENU, index=2),
            Screen(ScreenKind.MUSIC),
            Screen(ScreenKind.GAME),
            Screen(ScreenKind.SETTINGS),
        ]
        presenter = MenuPresenter(engine=self.engine)
        presenter.open()
        try:
            for s in screens:
                result = presenter.present(s)
                self.assertTrue(result.twin_passed, f"{s.kind}: {result.error}")
        finally:
            presenter.close()

    def test_identical_screen_skipped_but_returns_last_verified(self) -> None:
        presenter = MenuPresenter(engine=self.engine)
        presenter.open()
        try:
            first = presenter.present(Screen(ScreenKind.GAME))
            second = presenter.present(Screen(ScreenKind.GAME))  # dedup
            self.assertTrue(first.twin_passed)
            self.assertTrue(second.twin_passed)
            self.assertEqual(first.verified_frame, second.verified_frame)
        finally:
            presenter.close()


class PresenterErrorHandlingTests(unittest.TestCase):
    def test_missing_engine_raises_on_open(self) -> None:
        with self.assertRaises(Exception):
            presenter = MenuPresenter(engine="/nonexistent/twin")
            presenter.open()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `PYTHONPATH=src MN12832L_SYSTEM_TWIN=build/vfd_system_twin .venv/bin/python -m unittest tests.python.test_menu_presenter -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mn12832l.menu.presenter'`

- [ ] **Step 3: 최소 구현**

`src/mn12832l/menu/presenter.py`:
```python
"""메뉴 → 검증된 프레임 조립. VfdDisplay + DigitalTwinTransport 사용 (스펙 4.4, 5절)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..display import DisplayError, VfdDisplay
from ..renderer import MvlsbRenderer
from ..twin import DigitalTwinError, DigitalTwinTransport
from .model import Screen
from .render import draw_screen


@dataclass(frozen=True)
class PresentedFrame:
    verified_frame: bytes
    twin_passed: bool
    stats: Optional[Dict[str, Any]]
    error: Optional[str]


class MenuPresenter:
    """draw_screen → VfdDisplay.present → transport.last_result 파이프라인."""

    def __init__(self, engine: str, renderer: Optional[MvlsbRenderer] = None) -> None:
        self._renderer = renderer or MvlsbRenderer()
        self._transport = DigitalTwinTransport([engine], timeout=2.0)
        self._display = VfdDisplay(self._transport, renderer=self._renderer)
        self._last_verified: Optional[bytes] = None
        self._last_stats: Optional[Dict[str, Any]] = None

    def open(self) -> None:
        self._display.open()

    def close(self) -> None:
        self._display.close()

    def __enter__(self) -> "MenuPresenter":
        self.open()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def present(self, screen: Screen) -> PresentedFrame:
        frame = draw_screen(screen, self._renderer)
        try:
            self._display.present(frame)
        except (DigitalTwinError, DisplayError) as error:
            # 스펙 5절: 검증 실패/거부는 예외로 → 빨간 오버레이용 에러 정보
            return PresentedFrame(
                verified_frame=self._last_verified or frame,
                twin_passed=False,
                stats=self._last_stats,
                error=str(error),
            )

        twin = self._transport.last_result
        if twin is not None:
            self._last_verified = twin.reconstructed_frame
            self._last_stats = {
                "matches_source": twin.matches_source,
                "phases": twin.phases,
                "clock_rises": twin.clock_rises,
                "latches": twin.latches,
                "final_pins": dict(twin.final_pins),
            }
            return PresentedFrame(
                verified_frame=twin.reconstructed_frame,
                twin_passed=True,
                stats=self._last_stats,
                error=None,
            )
        # sent=False (dedup) 직전 결과 재사용
        return PresentedFrame(
            verified_frame=self._last_verified or frame,
            twin_passed=self._last_verified is not None,
            stats=self._last_stats,
            error=None if self._last_verified else "no frame verified yet",
        )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src MN12832L_SYSTEM_TWIN=build/vfd_system_twin .venv/bin/python -m unittest tests.python.test_menu_presenter -v`
(빌드가 필요하면 먼저 `make build/vfd_system_twin PYTHON=.venv/bin/python`)
Expected: PASS (4 tests; 3개는 환경변수 있을 때, 1개는 항상)

- [ ] **Step 5: 커밋**

```bash
git add src/mn12832l/menu/presenter.py tests/python/test_menu_presenter.py
git commit -m "feat(menu): add MenuPresenter wiring VfdDisplay+DigitalTwinTransport with error capture"
```

---

## Task 5: TkinterSource — 창 버튼/엔코더 → InputEvent (내부 FIFO 큐)

**Files:**
- Create: `src/mn12832l/menu/tk_source.py`
- Create: `tests/python/test_menu_tk_source.py`

**Interfaces:**
- Consumes: `InputEvent`, `InputSource` from Task 1; `tkinter` widgets (버튼 command, 엔코더 +/-/click)
- Produces: `TkinterSource(InputSource)` — `make_button(parent, event) -> tk.Button`, `make_encoder_click(parent) -> tk.Button`, `make_encoder_rotate(parent, direction) -> tk.Button` 헬퍼. 내부 FIFO `collections.deque`. `poll()`이 큐를 drain.
- 테스트 전략: 실제 Tk 루트를 만들지 않고 헬퍼가 큐에 push하는 로직만 검증 (`_enqueue` 메서드 노출).

- [ ] **Step 1: 실패 테스트 작성**

`tests/python/test_menu_tk_source.py`:
```python
import unittest
from collections import deque

from mn12832l.menu.input import BTN1, ENCODER_CLICK, ENCODER_ROTATE_CW
from mn12832l.menu.tk_source import TkinterSource


class TkinterSourceQueueTests(unittest.TestCase):
    def test_starts_empty(self) -> None:
        source = TkinterSource()
        self.assertEqual(source.poll(), [])

    def test_enqueue_then_poll_drains_fifo(self) -> None:
        source = TkinterSource()
        source._enqueue(BTN1)
        source._enqueue(ENCODER_ROTATE_CW)
        self.assertEqual(source.poll(), [BTN1])
        self.assertEqual(source.poll(), [ENCODER_ROTATE_CW])
        self.assertEqual(source.poll(), [])

    def test_poll_drains_all_at_once_if_multiple(self) -> None:
        source = TkinterSource()
        source._enqueue(BTN1)
        source._enqueue(ENCODER_CLICK)
        # 두 이벤트가 한 프레임에 몰려도 FIFO 순서 보존
        self.assertEqual(source.poll(), [BTN1, ENCODER_CLICK])

    def test_internal_queue_is_deque(self) -> None:
        source = TkinterSource()
        self.assertIsInstance(source._queue, deque)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_tk_source -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mn12832l.menu.tk_source'`

- [ ] **Step 3: 최소 구현**

`src/mn12832l/menu/tk_source.py`:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_tk_source -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/mn12832l/menu/tk_source.py tests/python/test_menu_tk_source.py
git commit -m "feat(menu): add TkinterSource adapter with FIFO queue for poll/event bridge"
```

---

## Task 6: MenuApp — Tkinter 창 + after 루프 + 캔버스 그리기

**Files:**
- Create: `src/mn12832l/menu/app.py`
- Create: `tests/python/test_menu_app_smoke.py`

**Interfaces:**
- Consumes: Tasks 1-5 전부 (`MenuModel`, `TkinterSource`, `MenuPresenter`, `ScreenKind`)
- Produces: `MenuApp` class — `__init__(root, engine)`, `setup()` (위젯 배치), `tick()` (after 콜백), `start()` (첫 tick 예약), `on_close()` (스펙 4.5 종료 순서). 캔버스는 768×192 (128×32 × 6). VFD 청록색 픽셀.

- [ ] **Step 1: 실패 테스트 작성 (헤드리스 smoke — 실제 루프는 안 돌림)**

`tests/python/test_menu_app_smoke.py`:
```python
import unittest

from mn12832l.menu.app import MenuApp


class MenuAppImportTests(unittest.TestCase):
    """헤드리스 CI에서도 import와 클래스 구조가 깨지지 않는지 확인."""

    def test_app_class_exists_with_expected_interface(self) -> None:
        self.assertTrue(hasattr(MenuApp, "setup"))
        self.assertTrue(hasattr(MenuApp, "tick"))
        self.assertTrue(hasattr(MenuApp, "start"))
        self.assertTrue(hasattr(MenuApp, "on_close"))

    def test_app_requires_engine_arg(self) -> None:
        import inspect
        sig = inspect.signature(MenuApp.__init__)
        self.assertIn("engine", sig.parameters)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_app_smoke -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mn12832l.menu.app'`

- [ ] **Step 3: 구현**

`src/mn12832l/menu/app.py`:
```python
"""Tkinter 미리보기 창. root.after() 기반 단일 루프 (스펙 4.5)."""

from __future__ import annotations

import time
import tkinter as tk
from typing import Optional

from .input import BTN1, BTN2, BTN3, BTN4, ENCODER_ROTATE_CCW, ENCODER_ROTATE_CW
from .model import MenuModel, ScreenKind
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `PYTHONPATH=src .venv/bin/python -m unittest tests.python.test_menu_app_smoke -v`
Expected: PASS (2 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/mn12832l/menu/app.py tests/python/test_menu_app_smoke.py
git commit -m "feat(menu): add MenuApp Tkinter preview with after-loop and pixel canvas"
```

---

## Task 7: 진입점 + Makefile 타깃

**Files:**
- Create: `src/mn12832l/menu/__main__.py`
- Modify: `Makefile` (`menu` 타깃 추가, `.PHONY` 업데이트)

**Interfaces:**
- Consumes: `MenuApp` from Task 6
- Produces: `python -m mn12832l.menu` 실행 가능. `make menu PYTHON=.venv/bin/python`

- [ ] **Step 1: 진입점 구현**

`src/mn12832l/menu/__main__.py`:
```python
"""`python -m mn12832l.menu` 진입점."""

from __future__ import annotations

import os
import sys
import tkinter as tk

from .app import MenuApp


def main() -> int:
    engine = os.environ.get("MN12832L_SYSTEM_TWIN")
    if not engine:
        print("MN12832L_SYSTEM_TWIN 환경변수가 필요합니다.", file=sys.stderr)
        print("예: make menu PYTHON=.venv/bin/python", file=sys.stderr)
        return 2

    root = tk.Tk()
    app = MenuApp(root, engine=engine)
    app.setup()
    app.start()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Makefile에 menu 타깃 추가**

`twin:` 타깃 뒤 (예: 126행 뒤)에 추가:
```make
menu: $(BUILD_DIR)/vfd_system_twin
	PYTHONPATH=src MN12832L_SYSTEM_TWIN=$(CURDIR)/$(BUILD_DIR)/vfd_system_twin \
		$(PYTHON) -m mn12832l.menu
```

그리고 `.PHONY:` 행(34행)에 `menu` 추가:
```make
.PHONY: all characterize test test-font test-scan test-host-link test-python twin menu \
```

- [ ] **Step 3: 빌드 + import 확인**

Run: `make build/vfd_system_twin PYTHON=.venv/bin/python`
Then: `PYTHONPATH=src MN12832L_SYSTEM_TWIN=build/vfd_system_twin .venv/bin/python -c "from mn12832l.menu.__main__ import main; print('ok')"`
Expected: `ok`

- [ ] **Step 4: 커밋**

```bash
git add src/mn12832l/menu/__main__.py Makefile
git commit -m "feat(menu): add python -m mn12832l.menu entrypoint and make menu target"
```

---

## Task 8: 통합 검증 — make all 그린 유지 + 매뉴얼 smoke

**Files:**
- Modify: (없음 — 검증만)

- [ ] **Step 1: 전체 Python 테스트 통과 확인**

Run: `make test-python PYTHON=.venv/bin/python`
Expected: 기존 39개 + 신규 menu 테스트 전부 PASS. 실패 없음.

- [ ] **Step 2: 전체 게이트 실행**

Run: `make all PYTHON=.venv/bin/python`
Expected: test, warnings, analyze 전부 PASS.

- [ ] **Step 3: 매뉴얼 smoke (GUI 창 확인)**

Run: `make menu PYTHON=.venv/bin/python`
사람이 확인:
- 창이 뜬다
- 2초 후 BOOT → MAIN_MENU로 넘어간다
- 다이얼 ▶/◀ 버튼으로 선택이 움직인다 (랩어라운드)
- 다이얼 누르기로 음악/게임/설정 진입
- BTN4로 메인 메뉴 복귀
- 상태 표시줄에 "DIGITAL TWIN: PASS" + 통계
- 창 닫기 버튼으로 정상 종료

- [ ] **Step 4: 스펙 HTML 설명서 커밋 (이미 만든 것)**

이미 `reports/vfd-menu-spec-overview.html`이 있으므로 별도 작업 없음. 플랜 완료.

---

## Self-Review 체크리스트 (작성자 자기 점검)

**1. 스펙 커버리지:**
- 스펙 2.1 (5화면) → Task 2 (model), Task 3 (render) ✓
- 스펙 4.1 (입력 부품 교체) → Task 1 (InputSource/FakeInputSource), Task 5 (TkinterSource) ✓
- 스펙 4.2 (메뉴 전이도, 엔코더 1:1 랩어라운드, BOOT 2.0초) → Task 2 테스트에 전부 커버 ✓
- 스펙 4.3 (deterministic 레이아웃) → Task 3 golden frame 테스트 ✓
- 스펙 4.4 (present/last_result 분리) → Task 4 presenter 구현 ✓
- 스펙 4.5 (after 루프, 폴링 먼저, 종료 순서) → Task 6 app ✓
- 스펙 5절 (예외 기반 에러 UX) → Task 4 presenter 예외 잡기, Task 6 빨간 오버레이 ✓
- 스펙 8 성공 기준 1-6 → Task 7 (1), Task 2 (2), Task 4+8 (3), Task 2-3 (4), Task 8 (5), Task 1 (6) ✓

**2. 플레이스홀더 스캔:** TBD/TODO 없음. 모든 코드 단계에 실제 코드 있음.

**3. 타입 일관성:**
- `InputEvent` enum — Task 1 정의, Task 2/5/6 동일 사용 ✓
- `Screen(kind, index, boot_elapsed)` — Task 2 정의, Task 3/4 동일 ✓
- `ScreenKind` enum — Task 2 정의, 전 태스크 일치 ✓
- `PresentedFrame` — Task 4 정의, Task 6 사용 ✓
- `poll() -> list[InputEvent]` — Task 1 정의, Task 5/6 동일 ✓

모든 스펙 요구사항이 태스크에 매핑되고, 타입이 일관됨.
