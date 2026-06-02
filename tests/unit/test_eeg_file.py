from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.domain.eeg_file import (
    EEGFileError,
    resolve_brainvision_companions,
    validate_eeg_header,
    validate_extension,
)


def test_validate_extension_rejects_unsupported() -> None:
    with pytest.raises(EEGFileError, match=r"Nieobsługiwane rozszerzenie: \.txt"):
        validate_extension(Path("sample.txt"))


def test_validate_extension_accepts_edf() -> None:
    validate_extension(Path("recording.edf"))


def test_validate_extension_accepts_vhdr() -> None:
    validate_extension(Path("recording.vhdr"))


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
