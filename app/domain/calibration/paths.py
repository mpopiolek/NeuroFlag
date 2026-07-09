from __future__ import annotations

import os
from pathlib import Path

DEFAULT_EXPERT_CSV = Path(
    os.environ.get(
        "NEUROFLAG_EXPERT_CSV",
        r"D:\CVGOSI\NF dane\analiza eeg\wyniki_indywidualne.csv",
    )
)

DEFAULT_EDF_DIR = Path(
    os.environ.get(
        "NEUROFLAG_EDF_DIR",
        r"D:\CVGOSI\NF dane\Testowe",
    )
)
