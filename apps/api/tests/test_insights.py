from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.insights.precipitation import precipitation_insights
from app.services.insights.ranking import rank
from app.services.insights.wind import wind_insights

TZ = ZoneInfo("Asia/Yakutsk")


def point_data():
    return {
        "point": {"id": "x", "name": "Тестовая точка"},
        "precipitation": {
            "mean": 18,
            "minimum": 11,
            "maximum": 26,
            "range": 15,
            "model_values": {"ECMWF IFS": 18, "NOAA GFS": 26, "DWD ICON": 11},
        },
        "precipitation_analysis": {
            "daily_total": {
                "mean": 18,
                "minimum": 11,
                "maximum": 26,
                "range": 15,
                "model_values": {
                    "ECMWF IFS": 18,
                    "NOAA GFS": 26,
                    "DWD ICON": 11,
                },
            },
            "peak_value": 4,
            "peak_model": "NOAA GFS",
            "event_start": datetime(2026, 7, 31, 12, tzinfo=TZ),
            "event_end": datetime(2026, 7, 31, 19, tzinfo=TZ),
            "duration_hours": 8,
        },
        "wind_analysis": {
            "maximum_speed": {"mean": 9, "model_values": {}},
            "maximum_gust": {
                "maximum": 18,
                "maximum_source": "NOAA GFS",
                "range": 9,
                "model_values": {"ECMWF IFS": 15, "NOAA GFS": 18, "DWD ICON": 9},
            },
            "strong_wind_start": datetime(2026, 7, 31, 10, tzinfo=TZ),
            "strong_wind_end": datetime(2026, 7, 31, 18, tzinfo=TZ),
            "strong_wind_duration_hours": 9,
            "maximum_direction_disagreement_deg": 120,
        },
    }


def test_precipitation_cards_are_explainable_and_limited():
    now = datetime(2026, 7, 31, tzinfo=TZ)
    items = precipitation_insights([point_data()], now, now)
    assert len(items) <= 5
    assert "PRECIP_DAILY_TOTAL" in {item["reason_code"] for item in items}
    assert all(item["explanation"] for item in items)


def test_wind_cards_are_explainable_and_limited():
    now = datetime(2026, 7, 31, tzinfo=TZ)
    items = wind_insights([point_data()], now, now)
    assert len(items) <= 5
    codes = {item["reason_code"] for item in items}
    assert "WIND_HIGH_GUST" in codes
    assert "WIND_DIRECTION_DISAGREEMENT" in codes


def test_ranking_prioritizes_notable_and_enforces_limit():
    items = [
        {
            "severity": "info",
            "reason_code": f"INFO_{index}",
            "point_id": str(index),
            "period_start": None,
            "models": [],
        }
        for index in range(8)
    ]
    items.append(
        {
            "severity": "notable",
            "reason_code": "PRECIP_DAILY_TOTAL",
            "point_id": "top",
            "period_start": None,
            "models": ["A", "B", "C"],
        }
    )
    result = rank(items, 5)
    assert len(result) == 5
    assert result[0]["point_id"] == "top"
