from __future__ import annotations

import struct
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import mne

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".edf", ".vhdr", ".eeg"})

# Sygnatura w nagłówku binarnym pliku EEGDigiTrack (Elmiko Medical)
_DIGITRACK_SIGNATURE: bytes = b"EEGDigiTrack"

# Próg kalibracji oddzielający kanały EEG od kanałów pomocniczych (ECG, EMG).
# Kanały EEG Elmiko EEG-1042 mają kalibrację ~0.179 µV/LSB — zdecydowanie poniżej progu.
# ECG ma kalibrację 2.5 µV/LSB — powyżej progu.
# Jeśli przyszły model Elmiko używa innego wzmocnienia, próg wymaga rewizji.
_EEG_CAL_THRESHOLD: float = 1.0  # µV/LSB


class EEGFileError(Exception):
    pass


def _is_digitrack(path: Path) -> bool:
    """Zwraca True jeśli plik ma nagłówek EEGDigiTrack (Elmiko)."""
    try:
        with open(path, "rb") as fh:
            header = fh.read(512)
        return _DIGITRACK_SIGNATURE in header
    except OSError:
        return False


def validate_extension(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise EEGFileError(
            f"Nieobsługiwane rozszerzenie: {suffix}. "
            "Obsługiwane formaty: .edf, .vhdr (BrainVision), .eeg (EEGDigiTrack)."
        )


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


def read_raw_digitrack(path: Path) -> mne.io.RawArray:
    """Wczytuje plik EEGDigiTrack (Elmiko) do mne.io.RawArray.

    Rzuca EEGFileError gdy:
    - sygnatura EEGDigiTrack nieobecna,
    - n_ch_data < 1,
    - kalibracja któregokolwiek kanału EEG <= 0.0,
    - obliczony data_start < 0.

    Kanały pomocnicze (ECG, kalibracja > _EEG_CAL_THRESHOLD) są wykluczane —
    nie wchodzą do strumienia danych i nie są przekazywane do mne.create_info.
    """
    mne = _load_mne()

    _MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB — pliki DigiTrack to max ~15 MB
    try:
        file_size = path.stat().st_size
        if file_size > _MAX_FILE_BYTES:
            raise EEGFileError(
                f"Plik zbyt duży ({file_size // 1_048_576} MB). "
                "Maksymalny rozmiar dla formatu DigiTrack: 200 MB."
            )
        with open(path, "rb") as fh:
            data = fh.read()
    except EEGFileError:
        raise
    except OSError as exc:
        raise EEGFileError(
            "Plik niedostępny — sprawdź czy plik istnieje i nie jest zablokowany."
        ) from exc

    if _DIGITRACK_SIGNATURE not in data[:512]:
        raise EEGFileError("Brak sygnatury EEGDigiTrack w pliku.")

    try:
        sfreq: float = float(struct.unpack_from("<H", data, 0x0004)[0])
        if sfreq <= 0:
            raise EEGFileError(
                "Uszkodzony nagłówek: nieprawidłowa częstotliwość próbkowania"
                f" ({int(sfreq)} Hz)."
            )
        total_blocks: int = struct.unpack_from("<I", data, 0x0010)[0]

        ch_names_all: list[str] = []
        ch_cal_all: list[float] = []
        for i in range(32):
            base = 0x0480 + i * 0x40
            raw_name = data[base : base + 16]
            try:
                name = raw_name.split(b"\x00")[0].decode("ascii").strip()
            except UnicodeDecodeError:
                break
            if not name or name == "Default" or ord(name[0]) < 0x20:
                break
            cal: float = struct.unpack_from("<f", data, base + 0x18)[0]
            ch_names_all.append(name)
            ch_cal_all.append(cal)
    except EEGFileError:
        raise
    except struct.error as exc:
        raise EEGFileError("Uszkodzony nagłówek: zbyt krótki plik.") from exc

    ch_names_data = [n for n, c in zip(ch_names_all, ch_cal_all) if c <= _EEG_CAL_THRESHOLD]
    ch_cal_data = [c for c in ch_cal_all if c <= _EEG_CAL_THRESHOLD]
    n_ch_data = len(ch_names_data)

    if n_ch_data < 1:
        raise EEGFileError(
            "Uszkodzony nagłówek: brak kanałów EEG (kalibracja ≤ 1.0 µV/LSB)."
        )

    for ch_name, ch_cal in zip(ch_names_data, ch_cal_data):
        if ch_cal <= 0.0:
            raise EEGFileError(
                f"Uszkodzony nagłówek: kalibracja kanału {ch_name} = 0"
            )

    if total_blocks == 0:
        raise EEGFileError("Uszkodzony nagłówek: total_blocks = 0 — brak danych w pliku.")

    data_start = len(data) - total_blocks * n_ch_data * 2
    if data_start < 0:
        raise EEGFileError(
            "Uszkodzony nagłówek: obliczony data_start < 0 — plik skrócony lub n_ch błędne."
        )

    raw_int16 = (
        np.frombuffer(data[data_start:], dtype="<i2")
        .reshape(total_blocks, n_ch_data)
        .T
    )
    data_uv = raw_int16.astype(np.float64) * np.array(ch_cal_data, dtype=np.float64)[:, None]
    data_v = data_uv * 1e-6

    info = mne.create_info(ch_names=ch_names_data, sfreq=sfreq, ch_types="eeg")
    info["subject_info"] = {}
    return mne.io.RawArray(data_v, info, verbose=False)


def read_patient_header_info(path: Path) -> tuple[str | None, str | None]:
    """Czyta inicjały i rok urodzenia z nagłówka pliku EDF.

    Zwraca (initials, birth_year) lub (None, None) przy braku danych.
    Obsługuje wyłącznie .edf — BrainVision i DigiTrack nie mają
    strukturalnych danych pacjenta w nagłówku.
    Wszystkie wyjątki są przechwytywane — nie blokuje wczytywania pliku.
    """
    if path.suffix.lower() != ".edf":
        return None, None
    try:
        mne = _load_mne()
        raw = mne.io.read_raw_edf(path, preload=False, verbose=False)
        subj: dict[str, object] = raw.info.get("subject_info") or {}

        first = str(subj.get("first_name") or "").strip()
        last = str(subj.get("last_name") or "").strip()
        initials: str | None = None
        if first or last:
            initials = "".join(n[0].upper() for n in (first, last) if n) or None

        birthday = subj.get("birthday")
        birth_year: str | None = None
        if birthday is not None:
            birth_year = str(getattr(birthday, "year", ""))  # date.year
            if not birth_year:
                birth_year = None

        return initials, birth_year
    except Exception:
        return None, None


def get_channel_names(path: Path) -> list[str]:
    """Zwraca listę kanałów z nagłówka pliku EEG bez wczytywania danych.

    Zwraca pustą listę przy błędzie (używane tylko informacyjnie w UI).
    """
    validate_extension(path)
    suffix = path.suffix.lower()
    mne = _load_mne()
    try:
        if suffix == ".edf":
            raw = mne.io.read_raw_edf(path, preload=False, verbose=False)
        elif suffix == ".vhdr":
            raw = mne.io.read_raw_brainvision(path, preload=False, verbose=False)
        elif suffix == ".eeg":
            raw = read_raw_digitrack(path)
        else:
            return []
        return list(raw.ch_names)
    except Exception:
        return []


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
        elif suffix == ".eeg":
            read_raw_digitrack(path)  # rzuca EEGFileError gdy sygnatura nieobecna
    except EEGFileError:
        raise
    except OSError as exc:
        raise EEGFileError(
            "Plik niedostępny — sprawdź czy plik istnieje i nie jest zablokowany."
        ) from exc
    except Exception as exc:
        raise EEGFileError(
            "Nie można odczytać pliku — "
            "plik może być uszkodzony lub w nieobsługiwanym formacie."
        ) from exc
