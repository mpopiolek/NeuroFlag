from __future__ import annotations

import sys

from app.domain import norms
from app.domain.norms import NormsLoadError
from app.ui.app_window import AppWindow
from app.ui.views.metadata_form import MetadataFormView


def main() -> None:
    smoke_test = "--smoke-test" in sys.argv
    try:
        _config = norms.load()
    except NormsLoadError as exc:
        sys.exit(f"Błąd ładowania norm: {exc}")
    if smoke_test:
        sys.exit(0)
    app = AppWindow()
    app.show_view(MetadataFormView)
    app.mainloop()


if __name__ == "__main__":
    main()
