from __future__ import annotations

import pytest

mne = pytest.importorskip("mne")

from app.domain.channels import (
    apply_channel_overrides,
    get_missing_canonical,
    normalize_channel_names,
    require_channels,
)
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


# --- apply_channel_overrides ---


def test_apply_overrides_renames_source_to_canonical() -> None:
    raw = _raw_with_channels(["EEG 4", "EEG 7"])
    apply_channel_overrides(raw, {"C3": "EEG 4", "O1": "EEG 7"})
    assert "C3" in raw.ch_names
    assert "O1" in raw.ch_names
    assert "EEG 4" not in raw.ch_names
    assert "EEG 7" not in raw.ch_names


def test_apply_overrides_empty_is_noop() -> None:
    raw = _raw_with_channels(["EEG 4", "EEG 7"])
    apply_channel_overrides(raw, {})
    assert raw.ch_names == ["EEG 4", "EEG 7"]


def test_apply_overrides_skips_missing_source() -> None:
    raw = _raw_with_channels(["EEG 4"])
    apply_channel_overrides(raw, {"C3": "EEG 99"})
    assert raw.ch_names == ["EEG 4"]


def test_apply_overrides_skips_already_canonical() -> None:
    raw = _raw_with_channels(["C3", "O1"])
    apply_channel_overrides(raw, {"C3": "C3"})
    assert raw.ch_names == ["C3", "O1"]


def test_apply_overrides_partial() -> None:
    raw = _raw_with_channels(["EEG 4", "O1"])
    apply_channel_overrides(raw, {"C3": "EEG 4"})
    assert "C3" in raw.ch_names
    assert "O1" in raw.ch_names


# --- get_missing_canonical ---


def test_get_missing_canonical_all_present_via_aliases() -> None:
    missing = get_missing_canonical(["EEG C3", "O1-A1"])
    assert missing == []


def test_get_missing_canonical_all_missing() -> None:
    missing = get_missing_canonical(["Fp1", "Fp2", "EOG"])
    assert set(missing) == {"C3", "O1"}


def test_get_missing_canonical_only_c3_missing() -> None:
    missing = get_missing_canonical(["O1", "Fp1"])
    assert missing == ["C3"]


def test_get_missing_canonical_empty_list() -> None:
    missing = get_missing_canonical([])
    assert set(missing) == {"C3", "O1"}


def test_get_missing_canonical_canonical_names_present() -> None:
    missing = get_missing_canonical(["C3", "O1", "EOG"])
    assert missing == []
