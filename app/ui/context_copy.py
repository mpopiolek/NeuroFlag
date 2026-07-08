from __future__ import annotations

CONTEXT_METADATA = (
    "Analiza odbywa się wyłącznie na tym komputerze. "
    "Aplikacja nie wysyła żadnych danych do internetu. "
    "Opcjonalne diagnozy, inicjały i rok urodzenia są zapisywane lokalnie "
    "w historii badań i raporcie PDF; nie wpływają na wynik przesiewowy. "
    "Identyfikatory pacjenta z nagłówka pliku EEG nie są wyświetlane ani zapisywane."
)

CONTEXT_FILE_IMPORT = (
    "Obsługiwane formaty: pliki EDF (.edf) oraz BrainVision (.vhdr z plikiem .eeg).\n\n"
    "Wymagane kanały: C3 i O1 (układ 10–20). Nagranie powinno trwać co najmniej 8 minut "
    "i zawierać segmenty OO → OZ → ZP (lub zostanie zastosowany podział 3×3 min).\n\n"
    "Plik jest wczytywany i analizowany wyłącznie na tym komputerze — "
    "aplikacja nie łączy się z internetem."
)
