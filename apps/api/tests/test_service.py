from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.schemas.forecast import ForecastRecord
from app.services.forecast import daily_model_aggregates, hourly
from app.statistics.core import daily_precipitation, numeric_consensus


def record(model: str, hour: int, rain: float) -> ForecastRecord:
    local = datetime(2026, 8, 1, hour, tzinfo=ZoneInfo("Asia/Yakutsk"))
    return ForecastRecord(
        model=model,
        point_id="x",
        point_name="X",
        latitude=50,
        longitude=127,
        forecast_time_utc=local.astimezone(UTC),
        forecast_time_local=local,
        fetched_at=datetime.now(UTC),
        temperature_2m_c=float(hour),
        precipitation_mm=rain,
    )


def test_daily_precipitation_sums_per_model_before_consensus():
    records = [record("A", 0, 1), record("A", 1, 2), record("B", 0, 3), record("B", 1, 4)]
    totals = daily_precipitation(records, ["A", "B"])
    assert totals == {"A": 3, "B": 7}
    assert numeric_consensus(totals)["mean"] == 5


def test_alignment_is_by_point_and_timestamp():
    records = [record("A", 0, 1), record("B", 0, 1), record("A", 1, 1), record("B", 1, 1)]
    aligned = hourly(records, "temperature_2m")
    assert len(aligned) == 2
    assert all(row["statistics"]["count"] == 2 for row in aligned)


def test_daily_aggregates_are_calculated_per_model_first():
    records = [
        record("A", 0, 1),
        record("A", 1, 2),
        record("B", 0, 3),
        record("B", 1, 4),
    ]
    aggregates = daily_model_aggregates(records)
    by_model = {row["model"]: row for row in aggregates}
    assert by_model["A"]["temperature_min"] == 0
    assert by_model["A"]["temperature_max"] == 1
    assert by_model["A"]["temperature_mean"] == 0.5
    assert by_model["A"]["precipitation_sum"] == 3
    assert by_model["B"]["precipitation_sum"] == 7
