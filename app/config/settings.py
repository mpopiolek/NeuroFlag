from __future__ import annotations

import hashlib
import json
import secrets
import sys
from pathlib import Path

_PBKDF2_ITERATIONS = 200_000
_HASH_NAME = "sha256"
_SALT_BYTES = 16
_DERIVED_KEY_BYTES = 32

_PASSWORD_HASH_KEY = "password_hash"
_SALT_KEY = "salt"
_ITERATIONS_KEY = "iterations"


def resolve_settings_path() -> Path:
    """Zwraca ścieżkę do settings.json — obok .exe w dystrybucji, w root projektu w dev."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "settings.json"
    return Path(__file__).parent.parent.parent / "settings.json"


def _effective_path(path: Path | None) -> Path:
    return path if path is not None else resolve_settings_path()


def _load_raw(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return raw


def _password_fields(raw: dict[str, object]) -> tuple[str, str, int] | None:
    password_hash = raw.get(_PASSWORD_HASH_KEY)
    salt = raw.get(_SALT_KEY)
    iterations = raw.get(_ITERATIONS_KEY)
    if not isinstance(password_hash, str) or not password_hash:
        return None
    if not isinstance(salt, str) or not salt:
        return None
    if not isinstance(iterations, int) or iterations <= 0:
        return None
    return password_hash, salt, iterations


def _derive_hash(password: str, salt_hex: str, iterations: int) -> str:
    salt_bytes = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac(
        _HASH_NAME,
        password.encode("utf-8"),
        salt_bytes,
        iterations,
        dklen=_DERIVED_KEY_BYTES,
    )
    return derived.hex()


def is_password_enabled(path: Path | None = None) -> bool:
    raw = _load_raw(_effective_path(path))
    if raw is None:
        return False
    return _password_fields(raw) is not None


def set_password(password: str, path: Path | None = None) -> None:
    target = _effective_path(path)
    salt_hex = secrets.token_hex(_SALT_BYTES)
    password_hash = _derive_hash(password, salt_hex, _PBKDF2_ITERATIONS)
    payload = {
        _PASSWORD_HASH_KEY: password_hash,
        _SALT_KEY: salt_hex,
        _ITERATIONS_KEY: _PBKDF2_ITERATIONS,
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def verify_password(password: str, path: Path | None = None) -> bool:
    raw = _load_raw(_effective_path(path))
    if raw is None:
        return False
    fields = _password_fields(raw)
    if fields is None:
        return False
    stored_hash, salt_hex, iterations = fields
    candidate = _derive_hash(password, salt_hex, iterations)
    return secrets.compare_digest(candidate, stored_hash)


def clear_password(path: Path | None = None) -> None:
    target = _effective_path(path)
    if target.is_file():
        target.unlink()
