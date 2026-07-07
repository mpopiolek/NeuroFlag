from __future__ import annotations

import struct
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.domain.eeg_file import (
    EEGFileError,
    _DIGITRACK_SIGNATURE,
    _parse_digitrack_patient_field,
    _parse_short_date_text,
    get_channel_names,
    read_patient_header_info,
    read_raw_digitrack,
    read_recording_date,
    resolve_brainvision_companions,
    validate_eeg_header,
    validate_extension,
)

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_digitrack.eeg"


def _minimal_digitrack_header() -> bytes:
    """Buduje minimalny nagłówek pliku EEGDigiTrack z jednym kanałem EEG."""
    buf = bytearray(0x0480 + 0x40)  # nagłówek + jeden rekord kanału
    # Sygnatura na offset 0x014C
    buf[0x014C : 0x014C + len(_DIGITRACK_SIGNATURE)] = _DIGITRACK_SIGNATURE
    # sfreq = 250 Hz na offset 0x0004 (uint16 LE)
    struct.pack_into("<H", buf, 0x0004, 250)
    # total_blocks = 0 (brak danych — używane tylko do data_start)
    struct.pack_into("<I", buf, 0x0010, 0)
    # Rekord kanału 0: nazwa "C3", kalibracja 0.179266 µV/LSB
    buf[0x0480 : 0x0480 + 2] = b"C3"
    struct.pack_into("<f", buf, 0x0480 + 0x18, 0.179266)
    return bytes(buf)


def _digitrack_header_with_patient(patient_field: str) -> bytes:
    header = bytearray(_minimal_digitrack_header())
    pii = b"\x00".join(
        [
            b"03.04.25",
            b"5",
            b"13.39.54",
            patient_field.encode("ascii"),
        ]
    )
    header[0x00C4 : 0x00C4 + len(pii)] = pii
    return bytes(header)


# ---------------------------------------------------------------------------
# validate_extension
# ---------------------------------------------------------------------------


def test_validate_extension_rejects_unsupported() -> None:
    with pytest.raises(EEGFileError, match=r"Nieobsługiwane rozszerzenie: \.txt"):
        validate_extension(Path("sample.txt"))


def test_validate_extension_accepts_edf() -> None:
    validate_extension(Path("recording.edf"))


def test_validate_extension_accepts_vhdr() -> None:
    validate_extension(Path("recording.vhdr"))


def test_validate_extension_accepts_eeg_digitrack() -> None:
    # .eeg jest teraz obsługiwanym rozszerzeniem — samo rozszerzenie wystarczy
    validate_extension(Path("session.eeg"))


# ---------------------------------------------------------------------------
# validate_eeg_header — gałąź .eeg
# ---------------------------------------------------------------------------


def test_validate_eeg_header_rejects_eeg_without_digitrack_signature(tmp_path: Path) -> None:
    eeg = tmp_path / "session.eeg"
    eeg.write_bytes(b"NOT_A_DIGITRACK_FILE\x00" * 30)
    with pytest.raises(EEGFileError, match=r"Brak sygnatury EEGDigiTrack"):
        validate_eeg_header(eeg)


# ---------------------------------------------------------------------------
# resolve_brainvision_companions
# ---------------------------------------------------------------------------


def test_resolve_brainvision_companions_missing_vmrk(tmp_path: Path) -> None:
    vhdr = tmp_path / "session.vhdr"
    vhdr.touch()
    (tmp_path / "session.eeg").touch()
    with pytest.raises(EEGFileError, match=r"Brak pliku \.vmrk"):
        resolve_brainvision_companions(vhdr)


def test_resolve_brainvision_companions_missing_eeg(tmp_path: Path) -> None:
    vhdr = tmp_path / "session.vhdr"
    vhdr.touch()
    (tmp_path / "session.vmrk").touch()
    with pytest.raises(EEGFileError, match=r"Brak pliku \.eeg"):
        resolve_brainvision_companions(vhdr)


def test_resolve_brainvision_companions_returns_paths(tmp_path: Path) -> None:
    vhdr = tmp_path / "session.vhdr"
    vhdr.touch()
    vmrk = tmp_path / "session.vmrk"
    eeg = tmp_path / "session.eeg"
    vmrk.touch()
    eeg.touch()
    assert resolve_brainvision_companions(vhdr) == (vmrk, eeg)


# ---------------------------------------------------------------------------
# validate_eeg_header — EDF
# ---------------------------------------------------------------------------


@patch("mne.io.read_raw_edf")
def test_validate_eeg_header_edf_mne_raises(mock_read: MagicMock, tmp_path: Path) -> None:
    edf = tmp_path / "recording.edf"
    edf.touch()
    mock_read.side_effect = RuntimeError("corrupt header")
    with pytest.raises(EEGFileError, match=r"Nie można odczytać pliku"):
        validate_eeg_header(edf)


@patch("mne.io.read_raw_edf")
def test_validate_eeg_header_edf_ok(mock_read: MagicMock, tmp_path: Path) -> None:
    edf = tmp_path / "recording.edf"
    edf.touch()
    validate_eeg_header(edf)
    mock_read.assert_called_once_with(edf, preload=False, verbose=False)


@patch("mne.io.read_raw_brainvision")
def test_validate_eeg_header_vhdr_ok(mock_read: MagicMock, tmp_path: Path) -> None:
    vhdr = tmp_path / "session.vhdr"
    vhdr.touch()
    (tmp_path / "session.vmrk").touch()
    (tmp_path / "session.eeg").touch()
    validate_eeg_header(vhdr)
    mock_read.assert_called_once_with(vhdr, preload=False, verbose=False)


# ---------------------------------------------------------------------------
# read_raw_digitrack — testy z realną fixture
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _FIXTURE.exists(), reason="Brak fixture sample_digitrack.eeg")
def test_read_raw_digitrack_channel_count() -> None:
    raw = read_raw_digitrack(_FIXTURE)
    assert len(raw.ch_names) == 19


@pytest.mark.skipif(not _FIXTURE.exists(), reason="Brak fixture sample_digitrack.eeg")
def test_read_raw_digitrack_sfreq() -> None:
    raw = read_raw_digitrack(_FIXTURE)
    assert raw.info["sfreq"] == 250.0


@pytest.mark.skipif(not _FIXTURE.exists(), reason="Brak fixture sample_digitrack.eeg")
def test_read_raw_digitrack_data_shape() -> None:
    raw = read_raw_digitrack(_FIXTURE)
    n_times = raw.get_data().shape[1]
    assert raw.get_data().shape[0] == 19
    assert n_times >= 120_000


@pytest.mark.skipif(not _FIXTURE.exists(), reason="Brak fixture sample_digitrack.eeg")
def test_get_channel_names_digitrack() -> None:
    names = get_channel_names(_FIXTURE)
    assert "C3" in names


# ---------------------------------------------------------------------------
# read_raw_digitrack — testy błędów (syntetyczne nagłówki)
# ---------------------------------------------------------------------------


def test_read_raw_digitrack_no_signature_raises(tmp_path: Path) -> None:
    eeg = tmp_path / "fake.eeg"
    eeg.write_bytes(b"\x00" * 512)
    with pytest.raises(EEGFileError, match=r"Brak sygnatury EEGDigiTrack"):
        read_raw_digitrack(eeg)


def test_read_raw_digitrack_corrupt_total_blocks_raises(tmp_path: Path) -> None:
    header = bytearray(_minimal_digitrack_header())
    # total_blocks=0xFFFFFF wymaga ~32 MB danych — plik jest ~2 KB, data_start < 0
    struct.pack_into("<I", header, 0x0010, 0xFFFFFF)
    eeg = tmp_path / "corrupt.eeg"
    eeg.write_bytes(bytes(header))
    with pytest.raises(EEGFileError, match=r"data_start < 0"):
        read_raw_digitrack(eeg)


def test_read_raw_digitrack_calibration_zero_raises(tmp_path: Path) -> None:
    header = bytearray(_minimal_digitrack_header())
    # Ustaw kalibrację pierwszego kanału na 0.0
    struct.pack_into("<f", header, 0x0480 + 0x18, 0.0)
    # total_blocks = 0 → data_start = len(data) → brak danych (OK dla błędu kalibracji)
    struct.pack_into("<I", header, 0x0010, 0)
    eeg = tmp_path / "zero_cal.eeg"
    eeg.write_bytes(bytes(header))
    with pytest.raises(EEGFileError, match=r"kalibracja kanału"):
        read_raw_digitrack(eeg)


# ---------------------------------------------------------------------------
# read_patient_header_info — DigiTrack
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("patient_field", "expected_initials", "expected_birth_year"),
    [
        ("X M 06-JUL-1996 Michal_KUCZYNSKI", "MK", "1996"),
        ("X M 24-DEC-1989 Barnaba_KOBRYN", "BK", "1989"),
    ],
)
def test_parse_digitrack_patient_field(
    patient_field: str,
    expected_initials: str,
    expected_birth_year: str,
) -> None:
    initials, birth_year = _parse_digitrack_patient_field(patient_field)
    assert initials == expected_initials
    assert birth_year == expected_birth_year


def test_read_patient_header_info_digitrack(tmp_path: Path) -> None:
    eeg = tmp_path / "patient.eeg"
    eeg.write_bytes(_digitrack_header_with_patient("X M 24-DEC-1989 Barnaba_KOBRYN"))
    initials, birth_year = read_patient_header_info(eeg)
    assert initials == "BK"
    assert birth_year == "1989"


def test_read_patient_header_info_digitrack_no_pii(tmp_path: Path) -> None:
    eeg = tmp_path / "anon.eeg"
    eeg.write_bytes(_minimal_digitrack_header())
    initials, birth_year = read_patient_header_info(eeg)
    assert initials is None
    assert birth_year is None


def test_read_patient_header_info_brainvision_eeg_returns_none(tmp_path: Path) -> None:
    eeg = tmp_path / "brainvision.eeg"
    eeg.write_bytes(b"NOT_A_DIGITRACK_FILE\x00" * 30)
    initials, birth_year = read_patient_header_info(eeg)
    assert initials is None
    assert birth_year is None


@pytest.mark.skipif(not _FIXTURE.exists(), reason="Brak fixture sample_digitrack.eeg")
def test_read_patient_header_info_fixture_has_no_pii() -> None:
    initials, birth_year = read_patient_header_info(_FIXTURE)
    assert initials is None
    assert birth_year is None


# ---------------------------------------------------------------------------
# read_recording_date
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("03.04.25", "2025-04-03"),
        ("18.12.25", "2025-12-18"),
        ("16.01.2026", "2026-01-16"),
        ("", None),
        ("invalid", None),
    ],
)
def test_parse_short_date_text(text: str, expected: str | None) -> None:
    parsed = _parse_short_date_text(text)
    if expected is None:
        assert parsed is None
    else:
        assert parsed is not None
        assert parsed.isoformat() == expected


def test_read_recording_date_digitrack(tmp_path: Path) -> None:
    eeg = tmp_path / "session.eeg"
    eeg.write_bytes(_digitrack_header_with_patient("X M 24-DEC-1989 Barnaba_KOBRYN"))
    assert read_recording_date(eeg) == date(2025, 4, 3)


def test_read_recording_date_digitrack_no_pii(tmp_path: Path) -> None:
    eeg = tmp_path / "anon.eeg"
    eeg.write_bytes(_minimal_digitrack_header())
    assert read_recording_date(eeg) is None
