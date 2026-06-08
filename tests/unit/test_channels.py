from __future__ import annotations

import pytest

mne = pytest.importorskip("mne")

from app.domain.channels import normalize_channel_names, require_channels
from app.domain.errors import PipelineError


def _raw_with_channels(names: list[str]) -> mne.io.BaseRaw:
    info = mne.create_info(names, sfreq=250.0, ch_types=["eeg"] * len(names))
    data = mne.io.RawArray([[0.0] * 100] * len(names), info)
    return data


def test_normalize_renames_aliases() -> None:
    raw = _raw_with_channels(["EEG C3", "O1-A1", "EOG"])
    normalize_channel_names(raw)
    assert raw.ch_names == ["C3", "O1", "EOG"]


def test_normalize_idempotent_for_canonical() -> None:
    raw = _raw_with_channels(["C3", "O1"])
    normalize_channel_names(raw)
    assert raw.ch_names == ["C3", "O1"]


def test_require_channels_ok() -> None:
    raw = _raw_with_channels(["C3", "O1"])
    require_channels(raw, ("C3", "O1"))


def test_require_channels_missing_raises_polish_message() -> None:
    raw = _raw_with_channels(["Fp1", "Fp2"])
    with pytest.raises(PipelineError) as exc_info:
        require_channels(raw, ("C3", "O1"))
    err = exc_info.value
    assert err.code == "missing_channels"
    assert "C3" in err.user_message_pl
    assert "Fp1" in err.user_message_pl
