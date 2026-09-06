from collections import Counter
from datetime import date
from zoneinfo import ZoneInfo

from app.regions.registry import get_region, list_regions, load_points
from app.regions.validator import validate_region_data
from app.services.forecast import mock_records, point_summaries


def test_registry_contains_all_far_eastern_and_siberian_regions():
    regions = list(list_regions())
    assert len(regions) == 21
    assert len({region.id for region in regions}) == 21
    assert [region.name for region in regions] == sorted(region.name for region in regions)
    assert Counter(region.federal_district for region in regions) == {
        "Дальневосточный федеральный округ": 11,
        "Сибирский федеральный округ": 10,
    }


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


def test_siberian_regions_have_expected_centers_and_timezones():
    expected = {
        "altai-republic": ("gorno-altaysk", "Asia/Barnaul"),
        "altai-krai": ("barnaul", "Asia/Barnaul"),
        "tyva-republic": ("kyzyl", "Asia/Krasnoyarsk"),
        "khakassia-republic": ("abakan", "Asia/Krasnoyarsk"),
        "krasnoyarsk-krai": ("krasnoyarsk", "Asia/Krasnoyarsk"),
        "irkutsk-oblast": ("irkutsk", "Asia/Irkutsk"),
        "kemerovo-oblast-kuzbass": ("kemerovo", "Asia/Novokuznetsk"),
        "novosibirsk-oblast": ("novosibirsk", "Asia/Novosibirsk"),
        "omsk-oblast": ("omsk", "Asia/Omsk"),
        "tomsk-oblast": ("tomsk", "Asia/Tomsk"),
    }
    for region_id, (center_id, timezone) in expected.items():
        region = get_region(region_id)
        assert region.federal_district == "Сибирский федеральный округ"
        assert region.default_point_id == center_id
        assert region.primary_timezone == timezone
        points = load_points(region_id)
        assert len(points) >= 15
        assert all(point.source == "GeoNames" for point in points)
        assert all(point.source_id for point in points)
        assert all(point.source_url for point in points)
        assert all(point.verified_at == date(2026, 9, 6) for point in points)


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
