from __future__ import annotations

from collections.abc import Sequence

from app.domain.types import CellResult

TASK_DISPLAY_ORDER: tuple[str, ...] = ("OO", "OZ", "ZP")
CHANNEL_DISPLAY_ORDER: tuple[str, ...] = ("C3", "O1")
BAND_DISPLAY_ORDER: tuple[str, ...] = ("Theta", "Beta2", "Beta1", "Delta")


def _band_sort_key(cell: CellResult) -> int:
    try:
        return BAND_DISPLAY_ORDER.index(cell.band)
    except ValueError:
        return len(BAND_DISPLAY_ORDER)


def cells_for_task_channel(
    cells: Sequence[CellResult],
    task: str,
    channel: str,
) -> list[CellResult]:
    return sorted(
        (c for c in cells if c.task == task and c.channel == channel),
        key=_band_sort_key,
    )
