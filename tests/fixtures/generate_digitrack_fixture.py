"""Jednorazowy skrypt generujący anonimizowaną fixture z pliku Kuczyński.EEG.

Uruchom ręcznie (NIE w CI):
    python tests/fixtures/generate_digitrack_fixture.py

Wynikowy plik: tests/fixtures/sample_digitrack.eeg (~137 KB)
- Pierwsze 2500 próbek (10 s przy 250 Hz)
- PII wyzerowane (offset 0x00C4–0x0143)
- Pole total_blocks zaktualizowane do 2500
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

SOURCE = Path("D:/CVGOSI/NF dane/Testowe/Kuczyński.EEG")
OUT = Path(__file__).parent / "sample_digitrack.eeg"

TARGET_BLOCKS = 2500
PII_START = 0x00C4
PII_END = 0x0143 + 1  # włącznie

# Próg kalibracji — kanały EEG mają kal. <= 1.0 µV/LSB (patrz eeg_file.py)
_EEG_CAL_THRESHOLD = 1.0


def main() -> None:
    if not SOURCE.exists():
        print(f"[BŁĄD] Nie znaleziono pliku źródłowego: {SOURCE}", file=sys.stderr)
        sys.exit(1)

    with open(SOURCE, "rb") as fh:
        data = bytearray(fh.read())

    # Odczytaj n_ch_data (kanały EEG, kal <= 1.0)
    n_ch_data = 0
    for i in range(32):
        base = 0x0480 + i * 0x40
        raw_name = bytes(data[base : base + 16])
        name = raw_name.split(b"\x00")[0].decode("ascii", errors="replace").strip()
        if not name or name == "Default" or ord(name[0]) < 0x20:
            break
        cal: float = struct.unpack_from("<f", data, base + 0x18)[0]
        if cal <= _EEG_CAL_THRESHOLD:
            n_ch_data += 1

    if n_ch_data < 1:
        print("[BŁĄD] Nie wykryto kanałów EEG w nagłówku.", file=sys.stderr)
        sys.exit(1)

    print(f"Wykryto {n_ch_data} kanałów EEG w strumieniu danych.")

    # Oblicz pozycję danych oryginalnych (pierwsze 2500 bloków)
    orig_total_blocks: int = struct.unpack_from("<I", data, 0x0010)[0]
    orig_data_start = len(data) - orig_total_blocks * n_ch_data * 2
    data_bytes_needed = TARGET_BLOCKS * n_ch_data * 2

    print(f"Oryginalne total_blocks={orig_total_blocks}, data_start=0x{orig_data_start:X}")
    print(f"Wycinamy {TARGET_BLOCKS} bloków = {data_bytes_needed} B danych.")

    # Nowy bufor: nagłówek + pierwsze TARGET_BLOCKS bloków danych
    header = data[:orig_data_start]
    data_section = data[orig_data_start : orig_data_start + data_bytes_needed]

    output = bytearray(header) + bytearray(data_section)

    # Zaktualizuj total_blocks w nagłówku
    struct.pack_into("<I", output, 0x0010, TARGET_BLOCKS)

    # Wyzeruj PII (imię, data urodzenia, PESEL)
    for i in range(PII_START, PII_END):
        output[i] = 0x00

    OUT.write_bytes(bytes(output))
    size_kb = OUT.stat().st_size / 1024
    print(f"Zapisano: {OUT}  ({size_kb:.1f} KB)")
    if size_kb > 200:
        print("[OSTRZEŻENIE] Plik przekracza 200 KB — rozważ zmniejszenie TARGET_BLOCKS.")


if __name__ == "__main__":
    main()
