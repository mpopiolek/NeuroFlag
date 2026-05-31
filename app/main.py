from __future__ import annotations

import sys

import customtkinter as ctk

from app.domain import norms
from app.domain.norms import NormsLoadError


def main() -> None:
    smoke_test = "--smoke-test" in sys.argv
    try:
        _config = norms.load()
    except NormsLoadError as exc:
        sys.exit(f"Błąd ładowania norm: {exc}")
    if smoke_test:
        sys.exit(0)
    app = ctk.CTk()
    app.title("NeuroFlag")
    app.geometry("800x600")
    app.mainloop()


if __name__ == "__main__":
    main()
