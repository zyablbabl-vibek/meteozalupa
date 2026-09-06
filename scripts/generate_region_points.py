"""Build regional control-point fixtures from the GeoNames Russia dump.

Usage:
    python scripts/generate_region_points.py /path/to/RU.txt
    python scripts/generate_region_points.py /path/to/RU.txt siberian

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
VERIFIED_AT = date.today().isoformat()
SOURCE_URL = "https://download.geonames.org/export/dump/RU.zip"
FAR_EAST_DISTRICT = "Дальневосточный федеральный округ"
SIBERIAN_DISTRICT = "Сибирский федеральный округ"
CENTER_NAMES = {
    "Anadyr": "Анадырь",
    "Birobidzhan": "Биробиджан",
    "Blagoveshchensk": "Благовещенск",
    "Chita": "Чита",
    "Khabarovsk": "Хабаровск",
    "Kemerovo": "Кемерово",
    "Krasnoyarsk": "Красноярск",
    "Kyzyl": "Кызыл",
    "Magadan": "Магадан",
    "Novosibirsk": "Новосибирск",
    "Omsk": "Омск",
    "Petropavlovsk-Kamchatsky": "Петропавловск-Камчатский",
    "Ulan-Ude": "Улан-Удэ",
    "Vladivostok": "Владивосток",
    "Yakutsk": "Якутск",
    "Yuzhno-Sakhalinsk": "Южно-Сахалинск",
    "Abakan": "Абакан",
    "Barnaul": "Барнаул",
    "Gorno-Altaysk": "Горно-Алтайск",
    "Irkutsk": "Иркутск",
    "Tomsk": "Томск",
}
KNOWN_NAMES = {
    "Novokuznetsk": "Новокузнецк",
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
    center: tuple[float, float] | None
    zoom: float
    federal_district: str = FAR_EAST_DISTRICT


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
    Region(
        "altai-republic",
        "Республика Алтай",
        "Республике Алтай",
        "Республики Алтай",
        "03",
        "Gorno-Altaysk",
        "Asia/Barnaul",
        16,
        None,
        6,
        SIBERIAN_DISTRICT,
    ),
    Region(
        "altai-krai",
        "Алтайский край",
        "Алтайском крае",
        "Алтайского края",
        "04",
        "Barnaul",
        "Asia/Barnaul",
        22,
        None,
        5.5,
        SIBERIAN_DISTRICT,
    ),
    Region(
        "tyva-republic",
        "Республика Тыва",
        "Республике Тыва",
        "Республики Тыва",
        "79",
        "Kyzyl",
        "Asia/Krasnoyarsk",
        18,
        None,
        5.5,
        SIBERIAN_DISTRICT,
    ),
    Region(
        "khakassia-republic",
        "Республика Хакасия",
        "Республике Хакасия",
        "Республики Хакасия",
        "31",
        "Abakan",
        "Asia/Krasnoyarsk",
        15,
        None,
        6,
        SIBERIAN_DISTRICT,
    ),
    Region(
        "krasnoyarsk-krai",
        "Красноярский край",
        "Красноярском крае",
        "Красноярского края",
        "91",
        "Krasnoyarsk",
        "Asia/Krasnoyarsk",
        35,
        None,
        3.5,
        SIBERIAN_DISTRICT,
    ),
    Region(
        "irkutsk-oblast",
        "Иркутская область",
        "Иркутской области",
        "Иркутской области",
        "20",
        "Irkutsk",
        "Asia/Irkutsk",
        25,
        None,
        4.5,
        SIBERIAN_DISTRICT,
    ),
    Region(
        "kemerovo-oblast-kuzbass",
        "Кемеровская область — Кузбасс",
        "Кемеровской области — Кузбассе",
        "Кемеровской области — Кузбасса",
        "29",
        "Kemerovo",
        "Asia/Novokuznetsk",
        20,
        None,
        6,
        SIBERIAN_DISTRICT,
    ),
    Region(
        "novosibirsk-oblast",
        "Новосибирская область",
        "Новосибирской области",
        "Новосибирской области",
        "53",
        "Novosibirsk",
        "Asia/Novosibirsk",
        20,
        None,
        5.5,
        SIBERIAN_DISTRICT,
    ),
    Region(
        "omsk-oblast",
        "Омская область",
        "Омской области",
        "Омской области",
        "54",
        "Omsk",
        "Asia/Omsk",
        20,
        None,
        5.5,
        SIBERIAN_DISTRICT,
    ),
    Region(
        "tomsk-oblast",
        "Томская область",
        "Томской области",
        "Томской области",
        "75",
        "Tomsk",
        "Asia/Tomsk",
        20,
        None,
        5,
        SIBERIAN_DISTRICT,
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
        value for value in alternatives.split(",") if re.fullmatch(r"[А-Яа-яЁё .()'’\\-]+", value)
    ]
    if not candidates:
        return ascii_name
    target = normalized(ascii_name)
    return max(
        candidates,
        key=lambda value: SequenceMatcher(None, target, normalized(transliterate(value))).ratio(),
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
    unique_coordinates = {(item["latitude"], item["longitude"]): item for item in candidates}
    pool = list(unique_coordinates.values())
    pool.sort(key=lambda item: item["population"], reverse=True)
    center = next(
        item for item in pool if normalized(item["ascii_name"]) == normalized(region.center_ascii)
    )
    selected = [center]

    def add(item: dict) -> None:
        is_near_existing = any(
            abs(item["latitude"] - existing["latitude"]) < 0.02
            and abs(item["longitude"] - existing["longitude"]) < 0.02
            for existing in selected
        )
        if item not in selected and not is_near_existing:
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


def main(source: Path, district: str | None = None) -> None:
    by_admin = load(source)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    selected_regions = [
        region
        for region in REGIONS
        if district is None
        or (district == "siberian" and region.federal_district == SIBERIAN_DISTRICT)
        or (district == "far-east" and region.federal_district == FAR_EAST_DISTRICT)
    ]
    if not selected_regions:
        raise SystemExit(f"Unknown or empty district selector: {district}")

    registry_path = OUTPUT / "regions.json"
    existing_registry = (
        json.loads(registry_path.read_text(encoding="utf-8"))["regions"]
        if registry_path.exists() and district is not None
        else []
    )
    selected_ids = {region.id for region in selected_regions}
    registry = [item for item in existing_registry if item["id"] not in selected_ids]
    used_ids: set[str] = set()
    for item in registry:
        payload = json.loads((OUTPUT / f"{item['id']}.json").read_text(encoding="utf-8"))
        used_ids.update(point["id"] for point in payload["points"])

    for region in selected_regions:
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
                        else KNOWN_NAMES.get(item["ascii_name"], item["name"])
                    ),
                    "latitude": item["latitude"],
                    "longitude": item["longitude"],
                    "timezone": item["timezone"],
                    "point_type": (
                        "city"
                        if item["feature_code"] in {"PPLA", "PPLA2", "PPLC"}
                        else "settlement"
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
        map_center = region.center or (
            (min(item["latitude"] for item in chosen) + max(item["latitude"] for item in chosen))
            / 2,
            (min(item["longitude"] for item in chosen) + max(item["longitude"] for item in chosen))
            / 2,
        )
        registry.append(
            {
                "id": region.id,
                "name": region.name,
                "short_name": region.name,
                "name_prepositional": region.name_prepositional,
                "name_genitive": region.name_genitive,
                "federal_district": region.federal_district,
                "primary_timezone": region.primary_timezone,
                "default_point_id": default_point_id,
                "map_center": {
                    "latitude": round(map_center[0], 4),
                    "longitude": round(map_center[1], 4),
                },
                "map_zoom": region.zoom,
                "data_status": "partially_verified",
            }
        )
    registry.sort(key=lambda item: item["name"])
    registry_path.write_text(
        json.dumps({"regions": registry}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    if len(sys.argv) not in {2, 3}:
        raise SystemExit("Expected path to GeoNames RU.txt and optional district selector")
    main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) == 3 else None)
