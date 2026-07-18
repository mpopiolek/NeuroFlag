from __future__ import annotations

from app.domain.cell_layout import (
    BAND_DISPLAY_ORDER,
    cells_for_task_channel,
)
from app.domain.types import CellColor, CellResult

_CELLS_10: tuple[CellResult, ...] = (
    CellResult(1, "C3", "OZ", "Theta", CellColor.GREEN),
    CellResult(2, "C3", "ZP", "Theta", CellColor.GREEN),
    CellResult(3, "C3", "ZP", "Beta1", CellColor.YELLOW),
    CellResult(4, "C3", "OO", "Beta2", CellColor.RED),
    CellResult(5, "O1", "OO", "Delta", CellColor.GREEN),
    CellResult(6, "O1", "OO", "Theta", CellColor.RED),
    CellResult(7, "O1", "OZ", "Theta", CellColor.YELLOW),
    CellResult(8, "O1", "ZP", "Theta", CellColor.GREEN),
    CellResult(9, "O1", "OO", "Beta2", CellColor.RED),
    CellResult(10, "O1", "ZP", "Beta2", CellColor.GREEN),
)


def test_cells_for_task_channel_filters_and_sorts_oo_o1() -> None:
    result = cells_for_task_channel(_CELLS_10, "OO", "O1")
    assert [c.band for c in result] == ["Theta", "Beta2", "Delta"]


def test_cells_for_task_channel_filters_oo_c3() -> None:
    result = cells_for_task_channel(_CELLS_10, "OO", "C3")
    assert len(result) == 1
    assert result[0].band == "Beta2"


def test_unknown_band_sorts_to_end() -> None:
    cells = (
        CellResult(1, "C3", "OO", "Gamma", CellColor.GREEN),
        CellResult(2, "C3", "OO", "Theta", CellColor.RED),
        CellResult(3, "C3", "OO", "Beta2", CellColor.YELLOW),
    )
    result = cells_for_task_channel(cells, "OO", "C3")
    assert [c.band for c in result] == ["Theta", "Beta2", "Gamma"]


def test_band_display_order_has_four_entries() -> None:
    assert len(BAND_DISPLAY_ORDER) == 4
