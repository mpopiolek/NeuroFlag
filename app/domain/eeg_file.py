from __future__ import annotations

from pathlib import Path
from types import ModuleType

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".edf", ".vhdr"})


class EEGFileError(Exception):
    pass


def validate_extension(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise EEGFileError(f"Nieobsługiwane rozszerzenie: {suffix}")


def resolve_brainvision_companions(vhdr_path: Path) -> tuple[Path, Path]:
    vmrk_path = vhdr_path.with_name(f"{vhdr_path.stem}.vmrk")
    eeg_path = vhdr_path.with_name(f"{vhdr_path.stem}.eeg")
    if not vmrk_path.is_file():
        raise EEGFileError(f"Brak pliku .vmrk obok wybranego {vhdr_path.name}")
    if not eeg_path.is_file():
        raise EEGFileError(f"Brak pliku .eeg obok wybranego {vhdr_path.name}")
    return vmrk_path, eeg_path


def _load_mne() -> ModuleType:
    try:
        import mne
    except ImportError as exc:
        raise EEGFileError(
            "Brak biblioteki MNE-Python. Zainstaluj zależności projektu: pip install -e ."
        ) from exc
    return mne  # type: ignore[no-any-return]


def validate_eeg_header(path: Path) -> None:
    validate_extension(path)
    suffix = path.suffix.lower()
    mne = _load_mne()
    try:
        if suffix == ".edf":
            mne.io.read_raw_edf(path, preload=False, verbose=False)
        elif suffix == ".vhdr":
            resolve_brainvision_companions(path)
            mne.io.read_raw_brainvision(path, preload=False, verbose=False)
    except EEGFileError:
        raise
    except OSError as exc:
        raise EEGFileError(f"Plik niedostępny: {exc}") from exc
    except Exception as exc:
        raise EEGFileError(f"Nie można odczytać pliku: {exc}") from exc
