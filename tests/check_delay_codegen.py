#!/usr/bin/env python3
"""Reject optimized Cortex-M0 delay functions that collapse to no-ops."""

from __future__ import annotations

import re
import sys
from pathlib import Path


FUNCTIONS = (
    "vfd_delay_13us_empirical",
    "vfd_delay_17us_empirical",
    "vfd_delay_3us_empirical",
    "vfd_delay_255ns_empirical",
)


def function_body(assembly: str, name: str) -> str:
    match = re.search(
        rf"^{re.escape(name)}:\n(?P<body>.*?)^\.Lfunc_end\d+:\n",
        assembly,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing assembly body for {name}")
    return match.group("body")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} ASSEMBLY", file=sys.stderr)
        return 2

    assembly = Path(sys.argv[1]).read_text()
    for name in FUNCTIONS:
        body = function_body(assembly, name)
        if not re.search(r"^\s*nop\s*$", body, flags=re.MULTILINE):
            raise AssertionError(f"{name} has no emitted nop")
        if not re.search(r"^\s*bne\s+\.L\S+\s*$", body, flags=re.MULTILINE):
            raise AssertionError(f"{name} has no loop back-edge")

    print("delay code-generation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
