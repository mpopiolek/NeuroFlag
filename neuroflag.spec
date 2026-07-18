# -*- mode: python ; coding: utf-8 -*-
#
# neuroflag.spec — PyInstaller build descriptor
# Build:   pyinstaller neuroflag.spec --clean
# Output:  dist/neuroflag/neuroflag.exe  (--onedir)
#
# Wymaga: PyInstaller >= 6.0
# Cel:    Windows 10/11 64-bit, Python 3.11

import sys
from pathlib import Path

ROOT = Path(SPECPATH)

# ---------------------------------------------------------------------------
# Hidden imports
# MNE-Python i SciPy używają leniwego ładowania — PyInstaller ich nie widzi.
# ---------------------------------------------------------------------------
hidden_imports = [
    # MNE-Python core
    "mne",
    "mne.io",
    "mne.io.edf",
    "mne.io.brainvision",
    "mne.preprocessing",
    "mne.filter",
    # SciPy
    "scipy.signal",
    "scipy.linalg",
    "scipy.fft",
    "scipy.sparse",
    "scipy.sparse.csgraph",
    "scipy.sparse.linalg",
    "scipy.integrate",
    "scipy.interpolate",
    # NumPy
    "numpy.core._multiarray_umath",
    "numpy.core._multiarray_tests",
    # ReportLab
    "reportlab",
    "reportlab.graphics",
    "reportlab.graphics.renderPDF",
    "reportlab.pdfgen",
    "reportlab.lib",
    "reportlab.lib.styles",
    "reportlab.platypus",
    # CustomTkinter
    "customtkinter",
    "customtkinter.windows",
    "customtkinter.windows.widgets",
    # scikit-learn (zależność pośrednia MNE dla ICA)
    "sklearn",
    "sklearn.utils._cython_blas",
    "sklearn.neighbors._partition_nodes",
    # Encoding
    "encodings",
    "encodings.utf_8",
    "encodings.cp1250",
]

# ---------------------------------------------------------------------------
# Datas — pliki niezbędne w dist/ obok .exe
# ---------------------------------------------------------------------------
datas = [
    # Baza norm — nadpisywalna przez użytkownika
    (str(ROOT / "norms.json"), "."),
    (str(ROOT / "norms.json.template"), "."),
    (str(ROOT / "docs" / "README-norms.md"), "docs"),
    (str(ROOT / "app" / "ui" / "assets"), "app/ui/assets"),
    # Moduły CustomTkinter zawierają zasoby (motywy, czcionki)
    # Lokalizacja zależy od wirtualnego środowiska — PyInstaller wykrywa je
    # automatycznie przez collect_data_files; poniższa linia jest fallbackiem.
    # (str(ROOT / ".venv" / "Lib" / "site-packages" / "customtkinter"), "customtkinter"),
]

# ---------------------------------------------------------------------------
# Excludes — redukują rozmiar dist/ przez wykluczenie zbędnych modułów
# ---------------------------------------------------------------------------
excludes = [
    "tkinter.test",
    # unittest — NIE wykluczać: numpy.testing (importowany przez scipy) wymaga unittest
    # email — NIE wykluczać: pyi_rth_pkgres → pkg_resources wymaga email przy starcie .exe
    "http",
    # urllib / xml — NIE wykluczać: pyi_rth_pkgres → pkg_resources → plistlib
    # wymaga xml; pathlib importuje urllib.parse — brak powoduje crash przy starcie .exe
    "xmlrpc",
    # pydoc — NIE wykluczać: scipy._lib._docscrape wymaga pydoc
    # doctest — NIE wykluczać: łańcuch scipy/stats może go importować
    # difflib — NIE wykluczać: unittest.case (numpy.testing → scipy) wymaga difflib
    "ftplib",
    "imaplib",
    "smtplib",
    "telnetlib",
    "nntplib",
    "poplib",
    "turtle",
    "antigravity",
    "this",
    "test",
    "tests",
    "IPython",
    "jupyter",
    "notebook",
    "matplotlib",  # MNE sugeruje matplotlib, ale GUI nie używa — wyklucz dla rozmiaru
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="neuroflag",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX może powodować false-positive w antywirusach
    console=False,      # brak okna konsoli — tylko GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(ROOT / "app" / "ui" / "assets" / "neuroflag.ico"),  # odkomentuj gdy ikona gotowa
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="neuroflag",
)
