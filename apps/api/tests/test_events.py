from datetime import datetime, timedelta

from app.statistics.events import (
    angular_distance,
    direction_label,
    event_periods,
    maximum_angular_disagreement,
    relative_spread,
)


def test_event_periods_ignore_low_values_and_split_events():
    start = datetime(2026, 7, 31)
    timeline = [
        (start + timedelta(hours=index), value)
        for index, value in enumerate([0.05, 0.2, 0.3, 0, 0.4, 0.5, 0.6])
    ]
    periods = event_periods(timeline, 0.1)
    assert len(periods) == 2
    assert periods[0]["duration_hours"] == 2
    assert periods[1]["duration_hours"] == 3
    assert periods[1]["peak"] == 0.6


def test_angular_distance_wraps_north():
    assert angular_distance(350, 10) == 20
    result = maximum_angular_disagreement({"ECMWF": 350, "GFS": 10, "ICON": 180})
    assert result["value"] == 170
    assert result["models"] in (["ECMWF", "ICON"], ["GFS", "ICON"])


def test_direction_uses_sixteen_sectors():
    assert direction_label(0) == "С"
    assert direction_label(22.5) == "ССВ"
    assert direction_label(90) == "В"
    assert direction_label(315) == "СЗ"


def test_relative_precipitation_spread_hidden_near_zero():
    assert relative_spread(0.4, 2) is None
    assert relative_spread(10, 5) == 50
