import json
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config.settings import settings
from app.regions.schemas import ForecastPoint, RegionDefinition, RegionMetadata

DEFAULT_REGION_ID = "amur-oblast"


class RegionNotFoundError(LookupError):
    pass


@lru_cache
def _definitions() -> tuple[RegionDefinition, ...]:
    payload = json.loads(Path(settings.regions_registry_file).read_text(encoding="utf-8"))
    return tuple(RegionDefinition.model_validate(item) for item in payload["regions"])


@lru_cache
def load_points(region_id: str) -> tuple[ForecastPoint, ...]:
    get_region_definition(region_id)
    path = Path(settings.regions_data_dir) / f"{region_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["region"]["id"] != region_id:
        raise ValueError(f"Region id in {path.name} does not match registry")
    return tuple(ForecastPoint.model_validate(item) for item in payload["points"])


def get_region_definition(region_id: str) -> RegionDefinition:
    region = next((item for item in _definitions() if item.id == region_id), None)
    if region is None:
        raise RegionNotFoundError(f"Неизвестный регион: {region_id}")
    return region


def get_region(region_id: str) -> RegionMetadata:
    definition = get_region_definition(region_id)
    points = load_points(region_id)
    timezones = {point.timezone for point in points}
    geojson = Path(settings.regions_geojson_dir) / f"{region_id}.geojson"
    return RegionMetadata(
        id=definition.id,
        name=definition.name,
        short_name=definition.short_name,
        name_prepositional=definition.name_prepositional,
        name_genitive=definition.name_genitive,
        federal_district=definition.federal_district,
        primary_timezone=definition.primary_timezone,
        has_multiple_timezones=len(timezones) > 1,
        default_point_id=definition.default_point_id,
        map_center_latitude=definition.map_center.latitude,
        map_center_longitude=definition.map_center.longitude,
        map_zoom=definition.map_zoom,
        data_status=definition.data_status,
        point_count=len(points),
        geojson_available=geojson.is_file(),
    )


def list_regions() -> tuple[RegionMetadata, ...]:
    return tuple(get_region(item.id) for item in _definitions())


def reset_registry_cache() -> None:
    _definitions.cache_clear()
    load_points.cache_clear()


def validate_timezone(value: str) -> bool:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return False
    return True

