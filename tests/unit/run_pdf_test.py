# run_pdf_test.py  (tymczasowy, do usunięcia po weryfikacji)
from datetime import datetime
from pathlib import Path
from app.domain.types import (
    AnalysisResult, CellColor, CellResult, PatientMetadata, Sex,
)
from app.domain.norms import load
from app.reports.pdf_generator import generate_report

metadata = PatientMetadata(age=8, sex=Sex.Z)
cells = tuple(
    CellResult(i, ch, task, band, color)
    for i, (ch, task, band, color) in enumerate([
        ("C3", "OO", "Theta", CellColor.RED),
        ("C3", "OO", "Beta1", CellColor.GREEN),
        ("C3", "OZ", "Theta", CellColor.YELLOW),
        ("C3", "OZ", "Beta1", CellColor.GREEN),
        ("C3", "ZP", "Theta", CellColor.RED),
        ("O1", "OO", "Theta", CellColor.GREEN),
        ("O1", "OO", "Beta1", CellColor.YELLOW),
        ("O1", "OZ", "Theta", CellColor.RED),
        ("O1", "OZ", "Beta1", CellColor.GREEN),
        ("O1", "ZP", "Theta", CellColor.YELLOW),
    ])
)
result = AnalysisResult(
    cells=cells,
    category=__import__('app.domain.types', fromlist=['ScreeningCategory']).ScreeningCategory.OBSERWACJA,
    description="Wyniki wymagają uważnej obserwacji.",
    analyzed_at=datetime.now(),
)
config = load(Path("norms.json"))
pdf = generate_report(metadata, result, config)
Path("test_output.pdf").write_bytes(pdf)
print("Zapisano test_output.pdf")