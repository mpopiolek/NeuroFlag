from __future__ import annotations

import pytest

from app.domain.norms import load, resolve_norms_path
from app.domain.types import NormsConfig


@pytest.fixture(scope="session")
def real_norms_config() -> NormsConfig:
    return load(resolve_norms_path())
