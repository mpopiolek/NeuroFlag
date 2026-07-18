from __future__ import annotations


class PipelineError(Exception):
    """Błąd domenowy pipeline EEG — komunikat dla UI po polsku."""

    def __init__(self, code: str, user_message_pl: str) -> None:
        self.code = code
        self.user_message_pl = user_message_pl
        super().__init__(user_message_pl)


class AnalysisCancelledError(PipelineError):
    """Analiza przerwana na żądanie użytkownika (cooperative cancel)."""

    def __init__(self) -> None:
        super().__init__(
            "analysis_cancelled",
            "Analiza została anulowana.",
        )
