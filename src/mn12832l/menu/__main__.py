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
