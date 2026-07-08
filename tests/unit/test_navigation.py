from __future__ import annotations

from app.ui.navigation import VIEW_STEP
from app.ui.views.analysis import AnalysisView
from app.ui.views.channel_mapping import ChannelMappingView
from app.ui.views.file_import import FileImportView
from app.ui.views.history import HistoryView
from app.ui.views.metadata_form import MetadataFormView
from app.ui.views.results_grid import ResultsGridView


def test_view_step_maps_all_six_views() -> None:
    assert set(VIEW_STEP.keys()) == {
        MetadataFormView,
        FileImportView,
        ChannelMappingView,
        AnalysisView,
        ResultsGridView,
        HistoryView,
    }


def test_view_step_numbers() -> None:
    assert VIEW_STEP[MetadataFormView] == 1
    assert VIEW_STEP[FileImportView] == 2
    assert VIEW_STEP[ChannelMappingView] == 2
    assert VIEW_STEP[AnalysisView] == 3
    assert VIEW_STEP[ResultsGridView] == 4
    assert VIEW_STEP[HistoryView] == 4
