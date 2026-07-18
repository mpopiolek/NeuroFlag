from __future__ import annotations

import customtkinter as ctk

from app.ui.views.analysis import AnalysisView
from app.ui.views.channel_mapping import ChannelMappingView
from app.ui.views.file_import import FileImportView
from app.ui.views.history import HistoryView
from app.ui.views.metadata_form import MetadataFormView
from app.ui.views.results_grid import ResultsGridView

VIEW_STEP: dict[type[ctk.CTkFrame], int] = {
    MetadataFormView: 1,
    FileImportView: 2,
    ChannelMappingView: 2,
    AnalysisView: 3,
    ResultsGridView: 4,
    HistoryView: 4,
}


def back_label_for(view_class: type[ctk.CTkFrame]) -> str:
    """Etykieta przycisku Wstecz w stopce dla widoków pomocniczych."""
    from app.ui.views.info_view import InfoView

    labels: dict[type[ctk.CTkFrame], str] = {
        MetadataFormView: "← Wróć do danych",
        FileImportView: "← Wróć do importu",
        ChannelMappingView: "← Wróć do mapowania",
        AnalysisView: "← Wróć do analizy",
        ResultsGridView: "← Wróć do wyników",
        InfoView: "← Wróć do informacji",
        HistoryView: "← Wróć do historii",
    }
    return labels.get(view_class, "← Wstecz")
