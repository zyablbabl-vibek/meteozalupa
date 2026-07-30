from datetime import date
from zoneinfo import ZoneInfo

from app.regions.registry import get_region, list_regions, load_points
from app.regions.validator import validate_region_data
from app.services.forecast import mock_records, point_summaries


def test_registry_contains_exactly_eleven_sorted_regions():
    regions = list(list_regions())
    assert len(regions) == 11
    assert len({region.id for region in regions}) == 11
    assert [region.name for region in regions] == sorted(region.name for region in regions)


def test_region_points_are_valid_and_defaults_exist():
    all_point_ids: set[str] = set()
    for region in list_regions():
        points = list(load_points(region.id))
        assert region.default_point_id in {point.id for point in points}
        assert any(point.is_regional_center for point in points)
        for point in points:
            assert point.region_id == region.id
            assert -90 <= point.latitude <= 90
            assert -180 <= point.longitude <= 180
            assert point.weight > 0
            ZoneInfo(point.timezone)
            assert point.id not in all_point_ids
            all_point_ids.add(point.id)


def test_yakutia_has_multiple_timezones_and_missing_geojson_is_supported():
    yakutia = get_region("sakha-yakutia")
    assert yakutia.has_multiple_timezones
    assert len({point.timezone for point in load_points(yakutia.id)}) >= 2
    assert not get_region("amur-oblast").geojson_available


def test_region_fixture_validator_has_no_errors():
    assert validate_region_data() == []


def test_mock_pipeline_produces_scoped_forecast_for_every_region():
    day = date(2026, 8, 1)
    for region in list_regions():
        records = mock_records(region.id, day, day)
        assert records
        assert {record.region_id for record in records} == {region.id}
        assert {record.local_date for record in records} == {day}
        summaries = point_summaries(records)
        assert summaries
        assert all(item["point"]["region_id"] == region.id for item in summaries)
