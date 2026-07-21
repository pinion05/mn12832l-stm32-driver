#!/usr/bin/env python3
"""Transitional source contracts for STM32 glue without the exact vendor SDK."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "firmware" / "stm32f0"


def function_body(source: str, name: str) -> str:
    signature = re.search(
        rf"\b{re.escape(name)}\s*\([^;]*?\)\s*\{{", source, re.DOTALL
    )
    if signature is None:
        raise AssertionError(f"missing function definition: {name}")

    opening = source.find("{", signature.start())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError(f"unterminated function definition: {name}")


def require_in_order(body: str, *needles: str) -> None:
    cursor = 0
    for needle in needles:
        found = body.find(needle, cursor)
        if found < 0:
            raise AssertionError(f"missing ordered contract token: {needle}")
        cursor = found + len(needle)


def main() -> int:
    board = (FIRMWARE / "main.c").read_text()
    interrupts = (FIRMWARE / "stm32f0xx_it.c").read_text()

    if not re.search(r"\bvolatile\s+uint8_t\s+vfd_scan_due\s*;", board):
        raise AssertionError("ISR/main scan flag must be volatile")

    require_in_order(
        function_body(board, "vfd_scan_event_take"),
        "__get_PRIMASK()",
        "__disable_irq()",
        "vfd_scan_due = 0u",
        "__enable_irq()",
    )
    require_in_order(
        function_body(board, "VFD_SafeShutdown"),
        "vfd_blank()",
        "vfd_hv_disable()",
        "vfd_ef_disable()",
    )
    require_in_order(
        function_body(board, "MX_GPIO_Init"),
        "HAL_GPIO_WritePin(GPIOA, VFD_BLK_PIN, GPIO_PIN_SET)",
        "HAL_GPIO_WritePin(GPIOF, VFD_EF_PIN | VFD_HV_PIN, GPIO_PIN_RESET)",
    )

    main_body = function_body(board, "main")
    require_in_order(main_body, "HAL_Init()", "MX_GPIO_Init()", "SystemClock_Config()")
    for call in ("vfd_scan_pack_step", "vfd_scan_emit_frame"):
        if call not in main_body:
            raise AssertionError(f"production main is not using tested {call}")
    require_in_order(
        main_body,
        "memset(scan_frame, 0, sizeof(scan_frame))",
        "vfd_scan_emit_frame",
        "vfd_latch_previous_frame(false)",
        "vfd_ef_enable()",
    )
    require_in_order(
        main_body,
        "render_supplied_demo()",
        "vfd_host_link_init(&vfd_host_link, data)",
        "vfd_scan_pack_step(vfd_host_link_front(&vfd_host_link)",
    )
    require_in_order(
        main_body,
        "vfd_scan_state_advance(&scan_state)",
        "scan_state.phase == 1u",
        "vfd_host_link_swap_if_pending(&vfd_host_link, NULL)",
        "vfd_scan_pack_step(vfd_host_link_front(&vfd_host_link)",
    )

    host_byte_body = function_body(board, "VFD_HostProcessByte")
    require_in_order(
        host_byte_body,
        "vfd_host_ready",
        "vfd_host_link_feed(&vfd_host_link, byte, ack_out)",
    )

    if "VFD_SafeShutdown()" not in function_body(board, "_Error_Handler"):
        raise AssertionError("error handler lacks fail-safe shutdown")
    for fault in ("NMI_Handler", "HardFault_Handler"):
        if "VFD_SafeShutdown()" not in function_body(interrupts, fault):
            raise AssertionError(f"{fault} lacks fail-safe shutdown")
    if "vfd_scan_due = 1u" not in function_body(interrupts, "TIM14_IRQHandler"):
        raise AssertionError("timer ISR does not raise the scan event")

    forbidden = ("MX_SPI1_Init", "Font_FastRead", "Font_Read", "HAL_SPI_")
    active_sources = "\n".join(
        path.read_text()
        for path in FIRMWARE.glob("*.c")
        if path.is_file()
    )
    for token in forbidden:
        if token in active_sources:
            raise AssertionError(f"unsupported font-ROM path remains active: {token}")

    print("firmware source-contract checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
