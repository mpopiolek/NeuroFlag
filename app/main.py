from __future__ import annotations

import sys
from pathlib import Path

from app.domain import norms
from app.domain.norms import NormsLoadError, load
from app.config.settings import is_password_enabled
from app.ui.app_window import AppWindow
from app.ui.views.metadata_form import MetadataFormView


def format_norms_error_message(exc: NormsLoadError) -> str:
    return (
        f"Nie można wczytać pliku norms.json:\n\n{exc}\n\n"
        f"Sprawdź plik norms.json w folderze aplikacji\n"
        f"(obok neuroflag.exe) lub przywróć plik domyślny z norms.json.template."
    )


def _show_norms_error(message: str) -> None:
    import tkinter
    import tkinter.messagebox

    root = tkinter.Tk()
    root.withdraw()
    try:
        tkinter.messagebox.showerror("NeuroFlag — Błąd konfiguracji", message)
    finally:
        root.destroy()


def _run_validate_norms_cli(path_str: str) -> int:
    path = Path(path_str)
    try:
        config = load(path)
    except NormsLoadError as exc:
        print(f"BŁĄD: {exc}", file=sys.stderr)
        return 1
    print(
        f"OK: norms.json jest poprawny "
        f"(version={config.version}, {len(config.norms)} norm)"
    )
    return 0


def _parse_debug_slow_analysis(argv: list[str]) -> float:
    """Opcjonalna pauza między krokami pipeline — tylko do QA anulowania."""
    delay = 0.0
    for arg in argv:
        if arg == "--debug-slow-analysis":
            delay = max(delay, 2.0)
        elif arg.startswith("--debug-slow-analysis="):
            try:
                delay = max(delay, float(arg.split("=", 1)[1]))
            except ValueError:
                bad = arg.split("=", 1)[1]
                print(
                    f"BŁĄD: nieprawidłowa wartość dla --debug-slow-analysis: {bad}",
                    file=sys.stderr,
                )
    return delay


def _parse_debug_crash_gui(argv: list[str]) -> bool:
    """Wymusza RuntimeError po kliknięciu „Informacje” — QA modalu błędu GUI."""
    return "--debug-crash-gui" in argv


def should_prompt_unlock() -> bool:
    return is_password_enabled()


def main() -> None:
    argv = sys.argv[1:]

    if "--validate-norms" in argv:
        idx = argv.index("--validate-norms")
        if idx + 1 >= len(argv):
            print("BŁĄD: brak ścieżki po --validate-norms", file=sys.stderr)
            sys.exit(2)
        sys.exit(_run_validate_norms_cli(argv[idx + 1]))

    smoke_test = "--smoke-test" in argv
    analysis_step_delay_s = _parse_debug_slow_analysis(argv)
    debug_crash_gui = _parse_debug_crash_gui(argv)
    try:
        _config = norms.load()
    except NormsLoadError as exc:
        _show_norms_error(format_norms_error_message(exc))
        sys.exit(1)
    if smoke_test:
        sys.exit(0)
    if should_prompt_unlock():
        from app.ui.unlock_dialog import prompt_unlock

        if not prompt_unlock():
            sys.exit(0)
    if debug_crash_gui:
        print(
            "[dev] --debug-crash-gui: kliknij „Informacje”, aby wywołać modal błędu GUI.",
            file=sys.stderr,
        )
    app = AppWindow(
        norms_config=_config,
        analysis_step_delay_s=analysis_step_delay_s,
        debug_crash_gui=debug_crash_gui,
    )
    from app.ui.exception_hooks import install_gui_exception_hooks

    install_gui_exception_hooks(app)
    app.show_view(MetadataFormView)
    app.mainloop()


if __name__ == "__main__":
    main()
