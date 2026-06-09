from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.domain.types import (
    BandRange,
    CategoryDescriptions,
    NormEntry,
    NormsConfig,
    ObservationCategory,
    ObservationChecklist,
    RecommendationRules,
)

REQUIRED_NORM_COUNT = 10

_DEFAULT_RECOMMENDATION_RULES = RecommendationRules(
    indication_min_red=5,
    indication_max_green=3,
    no_indication_min_green=4,
    no_indication_max_red=3,
)

_DEFAULT_OBSERVATION_CHECKLIST = ObservationChecklist(
    title="Co obserwować — wskazówki dla pedagoga i rodzica",
    intro=(
        "Poniższe obszary funkcjonowania warto śledzić niezależnie od wyniku"
        " badania przesiewowego. Trudności w kilku kategoriach jednocześnie"
        " mogą uzasadniać konsultację ze specjalistą."
    ),
    categories=(
        ObservationCategory(
            title="Uwaga i koncentracja",
            items=(
                "Trudności z utrzymaniem uwagi na zadaniu przez 15–20 minut",
                "Łatwe rozpraszanie przez bodźce w otoczeniu (dźwięki, ruch)",
                "Potrzeba wielokrotnego powtarzania poleceń",
                "Kłopoty z powróceniem do przerwanego zadania",
            ),
        ),
        ObservationCategory(
            title="Pamięć robocza",
            items=(
                "Trudności z zapamiętaniem instrukcji złożonych z kilku kroków",
                "Szybkie zapominanie materiału omówionego na lekcji",
                "Kłopoty z liczeniem w pamięci bez pomocy palców lub kartki",
                "Konieczność wielokrotnego czytania tego samego fragmentu",
            ),
        ),
        ObservationCategory(
            title="Przetwarzanie wzrokowo-przestrzenne",
            items=(
                "Mylenie podobnych liter lub cyfr (np. b/d, p/q, 6/9)",
                "Trudności z orientacją na kartce — gubienie miejsca w tekście",
                "Wolne tempo przepisywania z tablicy lub z książki",
                "Kłopoty z zadaniami geometrycznymi, mapami i schematami",
            ),
        ),
        ObservationCategory(
            title="Tempo pracy i zmęczenie poznawcze",
            items=(
                "Wolniejsze tempo wykonywania zadań niż rówieśnicy",
                "Szybkie zmęczenie podczas intensywnej pracy umysłowej",
                "Trudności z nadążaniem podczas dyktanda lub szybkich instrukcji",
                "Wahania jakości pracy w ciągu dnia szkolnego",
            ),
        ),
    ),
)

_DEFAULT_CATEGORY_DESCRIPTIONS = CategoryDescriptions(
    wskazanie=(
        "Profil EEG dziecka wykazuje istotne odchylenia od norm grupy kontrolnej"
        " w wielu analizowanych kombinacjach lokalizacja–zadanie–pasmo."
        " Zaleca się konsultację ze specjalistą (neurologiem dziecięcym lub"
        " neuropsychologiem) w celu pogłębionej diagnostyki."
    ),
    obserwacja=(
        "Profil EEG dziecka wykazuje odchylenia od norm w części analizowanych"
        " kombinacji. Zaleca się uważną obserwację funkcjonowania dziecka oraz"
        " ponowne badanie przesiewowe po 3–6 miesiącach lub wcześniej w przypadku"
        " zauważalnych trudności."
    ),
    brak=(
        "Profil EEG dziecka pozostaje w granicach normy grupy kontrolnej"
        " w przeważającej liczbie analizowanych kombinacji. Na podstawie tego"
        " badania przesiewowego brak aktualnych wskazań do dalszej diagnostyki"
        " neurologicznej."
    ),
)

_REQUIRED_TOP_LEVEL_KEYS = frozenset(
    {"version", "power_line_frequency", "band_ranges", "norms"}
)
_NORM_ENTRY_KEYS = frozenset({"id", "channel", "task", "band", "mean_z", "mean_k"})


class NormsLoadError(Exception):
    pass


def _as_float(value: object, label: str) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError) as exc:
        raise NormsLoadError(f"'{label}' must be a number, got {value!r}") from exc


def _as_int(value: object, label: str) -> int:
    try:
        f = float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError) as exc:
        raise NormsLoadError(f"'{label}' must be an integer, got {value!r}") from exc
    if f != int(f):
        raise NormsLoadError(f"'{label}' must be an integer, got {value!r}")
    return int(f)


def resolve_norms_path() -> Path:
    if getattr(sys, "frozen", False):
        exe_norms = Path(sys.executable).parent / "norms.json"
        if exe_norms.is_file():
            return exe_norms
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is None:
            raise NormsLoadError(
                "Nie znaleziono norms.json obok neuroflag.exe ani w paczce aplikacji."
            )
        return Path(str(meipass)) / "norms.json"
    return Path(__file__).parent.parent.parent / "norms.json"


def _parse_band_ranges(raw: Any) -> dict[str, BandRange]:
    if not isinstance(raw, dict):
        raise NormsLoadError("'band_ranges' must be a JSON object")
    result: dict[str, BandRange] = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            raise NormsLoadError(f"band_ranges['{name}'] must be a JSON object")
        for key in ("l_freq", "h_freq"):
            if key not in entry:
                raise NormsLoadError(f"band_ranges['{name}'] missing key '{key}'")
        result[name] = BandRange(
            l_freq=_as_float(entry["l_freq"], f"band_ranges.{name}.l_freq"),
            h_freq=_as_float(entry["h_freq"], f"band_ranges.{name}.h_freq"),
        )
    return result


def _parse_norm_entry(raw: Any, index: int) -> NormEntry:
    if not isinstance(raw, dict):
        raise NormsLoadError(f"norms[{index}] must be a JSON object")
    for key in _NORM_ENTRY_KEYS:
        if key not in raw:
            raise NormsLoadError(f"norms[{index}] missing key '{key}'")
    band = raw["band"]
    return NormEntry(
        norm_id=_as_int(raw["id"], f"norms[{index}].id"),
        channel=str(raw["channel"]),
        task=str(raw["task"]),
        band=str(band),
        mean_z=_as_float(raw["mean_z"], f"norms[{index}].mean_z"),
        mean_k=_as_float(raw["mean_k"], f"norms[{index}].mean_k"),
    )


def _parse_recommendation_rules(raw: Any) -> RecommendationRules:
    if not isinstance(raw, dict):
        raise NormsLoadError("'recommendation_rules' must be a JSON object")
    fields = (
        "indication_min_red",
        "indication_max_green",
        "no_indication_min_green",
        "no_indication_max_red",
    )
    for field in fields:
        if field not in raw:
            raise NormsLoadError(f"recommendation_rules missing key '{field}'")
    values = {f: _as_int(raw[f], f"recommendation_rules.{f}") for f in fields}
    for f, v in values.items():
        if v < 0:
            raise NormsLoadError(
                f"recommendation_rules.{f} must be >= 0, got {v}"
            )
    return RecommendationRules(
        indication_min_red=values["indication_min_red"],
        indication_max_green=values["indication_max_green"],
        no_indication_min_green=values["no_indication_min_green"],
        no_indication_max_red=values["no_indication_max_red"],
    )


def _parse_observation_checklist(raw: Any) -> ObservationChecklist:
    if not isinstance(raw, dict):
        raise NormsLoadError("'observation_checklist' must be a JSON object")
    for key in ("title", "intro", "categories"):
        if key not in raw:
            raise NormsLoadError(f"observation_checklist missing key '{key}'")
    if not isinstance(raw["title"], str) or not raw["title"].strip():
        raise NormsLoadError("observation_checklist.title must be a non-empty string")
    if not isinstance(raw["intro"], str) or not raw["intro"].strip():
        raise NormsLoadError("observation_checklist.intro must be a non-empty string")
    cats_raw = raw["categories"]
    if not isinstance(cats_raw, list) or len(cats_raw) == 0:
        raise NormsLoadError("observation_checklist.categories must be a non-empty array")
    categories: list[ObservationCategory] = []
    for idx, cat in enumerate(cats_raw):
        if not isinstance(cat, dict):
            raise NormsLoadError(f"observation_checklist.categories[{idx}] must be an object")
        for key in ("title", "items"):
            if key not in cat:
                raise NormsLoadError(
                    f"observation_checklist.categories[{idx}] missing key '{key}'"
                )
        items_raw = cat["items"]
        if not isinstance(items_raw, list) or len(items_raw) == 0:
            raise NormsLoadError(
                f"observation_checklist.categories[{idx}].items must be a non-empty array"
            )
        items = tuple(str(item) for item in items_raw)
        categories.append(ObservationCategory(title=str(cat["title"]), items=items))
    return ObservationChecklist(
        title=str(raw["title"]),
        intro=str(raw["intro"]),
        categories=tuple(categories),
    )


def _parse_category_descriptions(raw: Any) -> CategoryDescriptions:
    if not isinstance(raw, dict):
        raise NormsLoadError("'category_descriptions' must be a JSON object")
    for field in ("wskazanie", "obserwacja", "brak"):
        if field not in raw:
            raise NormsLoadError(f"category_descriptions missing key '{field}'")
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise NormsLoadError(
                f"category_descriptions.{field} must be a non-empty string"
            )
    return CategoryDescriptions(
        wskazanie=str(raw["wskazanie"]),
        obserwacja=str(raw["obserwacja"]),
        brak=str(raw["brak"]),
    )


def load(path: Path | None = None) -> NormsConfig:
    resolved = path if path is not None else resolve_norms_path()
    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise NormsLoadError(f"Cannot read norms file '{resolved}': {exc}") from exc
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NormsLoadError(f"Invalid JSON in '{resolved}': {exc}") from exc

    if not isinstance(data, dict):
        raise NormsLoadError("norms.json root must be a JSON object")

    for key in _REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            raise NormsLoadError(f"norms.json missing required key '{key}'")

    raw_norms: Any = data["norms"]
    if not isinstance(raw_norms, list):
        raise NormsLoadError("'norms' must be a JSON array")
    if len(raw_norms) != REQUIRED_NORM_COUNT:
        raise NormsLoadError(
            f"'norms' must contain exactly {REQUIRED_NORM_COUNT} entries, got {len(raw_norms)}"
        )

    band_ranges = _parse_band_ranges(data["band_ranges"])
    norm_entries = tuple(_parse_norm_entry(entry, i) for i, entry in enumerate(raw_norms))

    for i, entry in enumerate(norm_entries):
        if entry.band not in band_ranges:
            raise NormsLoadError(
                f"norms[{i}] references band '{entry.band}' not defined in band_ranges"
            )
        if entry.mean_z >= entry.mean_k:
            raise NormsLoadError(
                f"norms[{i}]: mean_z ({entry.mean_z}) must be less than mean_k ({entry.mean_k})"
            )

    if "recommendation_rules" in data:
        rec_rules = _parse_recommendation_rules(data["recommendation_rules"])
    elif "recommendation_threshold" in data:
        # Migracja ze starego schematu — mapuj na domyślne progi 5/3/4/3
        rec_rules = _DEFAULT_RECOMMENDATION_RULES
    else:
        raise NormsLoadError(
            "norms.json missing 'recommendation_rules'"
            " (or legacy 'recommendation_threshold' for migration)"
        )

    if "category_descriptions" in data:
        cat_desc = _parse_category_descriptions(data["category_descriptions"])
    else:
        cat_desc = _DEFAULT_CATEGORY_DESCRIPTIONS

    if "observation_checklist" in data:
        obs_checklist = _parse_observation_checklist(data["observation_checklist"])
    else:
        obs_checklist = _DEFAULT_OBSERVATION_CHECKLIST

    return NormsConfig(
        version=_as_int(data["version"], "version"),
        power_line_frequency=_as_float(data["power_line_frequency"], "power_line_frequency"),
        band_ranges=band_ranges,
        norms=norm_entries,
        recommendation_rules=rec_rules,
        category_descriptions=cat_desc,
        observation_checklist=obs_checklist,
    )
