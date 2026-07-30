"""Build regional control-point fixtures from the GeoNames Russia dump.

Usage:
    python scripts/generate_region_points.py /path/to/RU.txt

The generated files intentionally contain only published populated-place
coordinates. Selection combines the largest settlements with geographic
extremes so that large regions are not represented by their capital alone.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "regions"
VERIFIED_AT = date(2026, 7, 31).isoformat()
SOURCE_URL = "https://download.geonames.org/export/dump/RU.zip"
CENTER_NAMES = {
    "Anadyr": "Анадырь",
    "Birobidzhan": "Биробиджан",
    "Blagoveshchensk": "Благовещенск",
    "Chita": "Чита",
    "Khabarovsk": "Хабаровск",
    "Magadan": "Магадан",
    "Petropavlovsk-Kamchatsky": "Петропавловск-Камчатский",
    "Ulan-Ude": "Улан-Удэ",
    "Vladivostok": "Владивосток",
    "Yakutsk": "Якутск",
    "Yuzhno-Sakhalinsk": "Южно-Сахалинск",
}


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    name_prepositional: str
    name_genitive: str
    admin_code: str
    center_ascii: str
    primary_timezone: str
    count: int
    center: tuple[float, float]
    zoom: float


REGIONS = (
    Region(
        "amur-oblast",
        "Амурская область",
        "Амурской области",
        "Амурской области",
        "05",
        "Blagoveshchensk",
        "Asia/Yakutsk",
        20,
        (53.5, 127.8),
        5,
    ),
    Region(
        "jewish-autonomous-oblast",
        "Еврейская автономная область",
        "Еврейской автономной области",
        "Еврейской автономной области",
        "89",
        "Birobidzhan",
        "Asia/Vladivostok",
        10,
        (48.6, 132.9),
        7,
    ),
    Region(
        "zabaykalsky-krai",
        "Забайкальский край",
        "Забайкальском крае",
        "Забайкальского края",
        "93",
        "Chita",
        "Asia/Chita",
        22,
        (53.8, 116.2),
        5,
    ),
    Region(
        "kamchatka-krai",
        "Камчатский край",
        "Камчатском крае",
        "Камчатского края",
        "92",
        "Petropavlovsk-Kamchatsky",
        "Asia/Kamchatka",
        22,
        (57.2, 160.2),
        5,
    ),
    Region(
        "magadan-oblast",
        "Магаданская область",
        "Магаданской области",
        "Магаданской области",
        "44",
        "Magadan",
        "Asia/Magadan",
        18,
        (62.8, 153.4),
        5,
    ),
    Region(
        "primorsky-krai",
        "Приморский край",
        "Приморском крае",
        "Приморского края",
        "59",
        "Vladivostok",
        "Asia/Vladivostok",
        20,
        (44.2, 134.0),
        6,
    ),
    Region(
        "buryatia",
        "Республика Бурятия",
        "Республике Бурятия",
        "Республики Бурятия",
        "11",
        "Ulan-Ude",
        "Asia/Irkutsk",
        20,
        (53.5, 109.5),
        5,
    ),
    Region(
        "sakha-yakutia",
        "Республика Саха (Якутия)",
        "Республике Саха (Якутия)",
        "Республики Саха (Якутия)",
        "63",
        "Yakutsk",
        "Asia/Yakutsk",
        40,
        (66.4, 129.2),
        3.4,
    ),
    Region(
        "sakhalin-oblast",
        "Сахалинская область",
        "Сахалинской области",
        "Сахалинской области",
        "64",
        "Yuzhno-Sakhalinsk",
        "Asia/Sakhalin",
        20,
        (50.4, 143.2),
        5,
    ),
    Region(
        "khabarovsk-krai",
        "Хабаровский край",
        "Хабаровском крае",
        "Хабаровского края",
        "30",
        "Khabarovsk",
        "Asia/Vladivostok",
        27,
        (55.0, 136.0),
        4,
    ),
    Region(
        "chukotka-autonomous-okrug",
        "Чукотский автономный округ",
        "Чукотском автономном округе",
        "Чукотского автономного округа",
        "15",
        "Anadyr",
        "Asia/Anadyr",
        18,
        (66.8, 172.0),
        4,
    ),
)

RUSSIAN_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "j",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def transliterate(value: str) -> str:
    return "".join(RUSSIAN_TO_LATIN.get(char, char) for char in value.lower())


def russian_name(ascii_name: str, alternatives: str) -> str:
    candidates = [
        value
        for value in alternatives.split(",")
        if re.fullmatch(r"[А-Яа-яЁё .()'’\\-]+", value)
    ]
    if not candidates:
        return ascii_name
    target = normalized(ascii_name)
    return max(
        candidates,
        key=lambda value: SequenceMatcher(
            None, target, normalized(transliterate(value))
        ).ratio(),
    )


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "point"


def load(path: Path) -> dict[str, list[dict]]:
    by_admin: dict[str, list[dict]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        columns = line.split("\t")
        if len(columns) < 19 or columns[6] != "P" or columns[8] != "RU":
            continue
        admin_code = columns[10]
        if admin_code not in {region.admin_code for region in REGIONS}:
            continue
        if not columns[17] or columns[7] in {"PPLX", "PPLQ"}:
            continue
        population = int(columns[14] or 0)
        by_admin.setdefault(admin_code, []).append(
            {
                "geonames_id": columns[0],
                "ascii_name": columns[2],
                "name": russian_name(columns[2], columns[3]),
                "latitude": float(columns[4]),
                "longitude": float(columns[5]),
                "population": population,
                "timezone": columns[17],
                "feature_code": columns[7],
            }
        )
    return by_admin


def choose(candidates: list[dict], region: Region) -> list[dict]:
    unique_coordinates = {
        (item["latitude"], item["longitude"]): item for item in candidates
    }
    pool = list(unique_coordinates.values())
    pool.sort(key=lambda item: item["population"], reverse=True)
    center = next(
        item
        for item in pool
        if normalized(item["ascii_name"]) == normalized(region.center_ascii)
    )
    selected = [center]

    def add(item: dict) -> None:
        if item not in selected:
            selected.append(item)

    # Reserve roughly one third of the fixture for geographic coverage.
    coverage_pool = [item for item in pool if item["population"] >= 100]
    for key in ("latitude", "longitude"):
        for item in sorted(coverage_pool, key=lambda candidate: candidate[key])[:3]:
            add(item)
        for item in sorted(coverage_pool, key=lambda candidate: candidate[key], reverse=True)[:3]:
            add(item)
    for item in pool:
        if len(selected) >= region.count:
            break
        add(item)
    return selected[: region.count]


def main(source: Path) -> None:
    by_admin = load(source)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    registry = []
    used_ids: set[str] = set()
    for region in REGIONS:
        chosen = choose(by_admin[region.admin_code], region)
        points = []
        for item in chosen:
            point_id = slug(item["ascii_name"])
            if point_id in used_ids:
                point_id = f"{point_id}-{region.id}"
            used_ids.add(point_id)
            points.append(
                {
                    "id": point_id,
                    "region_id": region.id,
                    "name": (
                        CENTER_NAMES[region.center_ascii]
                        if item is chosen[0]
                        else item["name"]
                    ),
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "timezone": item["timezone"],
                    "point_type": (
                        "city" if item["feature_code"] in {"PPLA", "PPLA2", "PPLC"} else "settlement"
                    ),
                    "is_regional_center": item is chosen[0],
                    "weight": 1.0,
                    "source": "GeoNames",
                    "source_url": SOURCE_URL,
                    "source_id": item["geonames_id"],
                    "verified_at": VERIFIED_AT,
                }
            )
        default_point_id = points[0]["id"]
        payload = {
            "region": {"id": region.id, "name": region.name},
            "data_status": "partially_verified",
            "points": points,
        }
        (OUTPUT / f"{region.id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        registry.append(
            {
                "id": region.id,
                "name": region.name,
                "short_name": region.name,
                "name_prepositional": region.name_prepositional,
                "name_genitive": region.name_genitive,
                "federal_district": "Дальневосточный федеральный округ",
                "primary_timezone": region.primary_timezone,
                "default_point_id": default_point_id,
                "map_center": {
                    "latitude": region.center[0],
                    "longitude": region.center[1],
                },
                "map_zoom": region.zoom,
                "data_status": "partially_verified",
            }
        )
    (OUTPUT / "regions.json").write_text(
        json.dumps({"regions": registry}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Expected path to GeoNames RU.txt")
    main(Path(sys.argv[1]))
