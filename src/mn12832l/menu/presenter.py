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
