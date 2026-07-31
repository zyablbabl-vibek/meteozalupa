from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.schemas.forecast import ForecastRecord
from app.services.forecast import (
    MODEL_LABELS,
    daily_model_aggregates,
    daily_summary,
    hourly,
    mock_records,
    period_summary,
)
from app.statistics.core import daily_precipitation, numeric_consensus


def record(model: str, hour: int, rain: float) -> ForecastRecord:
    local = datetime(2026, 8, 1, hour, tzinfo=ZoneInfo("Asia/Yakutsk"))
    return ForecastRecord(
        region_id="amur-oblast",
        model=model,
        point_id="x",
        point_name="X",
        point_timezone="Asia/Yakutsk",
        latitude=50,
        longitude=127,
        forecast_time_utc=local.astimezone(UTC),
        forecast_time_local=local,
        local_date=local.date(),
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


def test_period_precipitation_sums_each_model_before_consensus():
    start = date(2026, 8, 1)
    dates = [start + timedelta(days=offset) for offset in range(3)]
    records = mock_records("amur-oblast", dates[0], dates[-1])
    summary = period_summary(records, dates)

    expected_by_model = {
        model: sum(
            daily_summary(records, day)["models"][model]["precipitation_sum"]
            for day in dates
        )
        for model in MODEL_LABELS
    }
    regional = summary["regional_precipitation"]

    assert regional["models"] == pytest.approx(expected_by_model)
    assert regional["statistics"]["mean"] == pytest.approx(
        sum(expected_by_model.values()) / len(expected_by_model)
    )
    assert regional["expected_days"] == 3
    assert regional["model_day_counts"] == dict.fromkeys(MODEL_LABELS, 3)
    assert regional["method"] == "weighted_spatial_mean_then_period_sum"
