import json
from pathlib import Path

from app.config.settings import settings
from app.regions.registry import list_regions, load_points, validate_timezone


def validate_region_data() -> list[str]:
    errors: list[str] = []
    regions = list(list_regions())
    ids = [region.id for region in regions]
    if len(regions) != 11:
        errors.append(f"Registry must contain 11 regions, got {len(regions)}")
    if len(ids) != len(set(ids)):
        errors.append("Region ids are not unique")

    global_point_ids: set[str] = set()
    for region in regions:
        points = list(load_points(region.id))
        point_ids = [point.id for point in points]
        if region.default_point_id not in point_ids:
            errors.append(f"{region.id}: default point is missing")
        if len(point_ids) != len(set(point_ids)):
            errors.append(f"{region.id}: duplicate point ids")
        if not any(point.is_regional_center for point in points):
            errors.append(f"{region.id}: regional center is missing")
        for point in points:
            if point.region_id != region.id:
                errors.append(f"{region.id}/{point.id}: mismatched region id")
            if point.id in global_point_ids:
                errors.append(f"{point.id}: point id is reused by another region")
            global_point_ids.add(point.id)
            if not validate_timezone(point.timezone):
                errors.append(f"{region.id}/{point.id}: invalid timezone {point.timezone}")

        geojson_path = Path(settings.regions_geojson_dir) / f"{region.id}.geojson"
        if not geojson_path.exists():
            continue
        try:
            payload = json.loads(geojson_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{region.id}: invalid GeoJSON: {exc}")
            continue
        if payload.get("type") not in {"Feature", "FeatureCollection"}:
            errors.append(f"{region.id}: unsupported GeoJSON root type")
        declared_id = payload.get("properties", {}).get("region_id")
        if declared_id is not None and declared_id != region.id:
            errors.append(f"{region.id}: GeoJSON region id mismatch")
    return errors
