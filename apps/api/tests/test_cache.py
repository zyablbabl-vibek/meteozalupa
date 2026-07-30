from datetime import UTC, date, datetime

from app.db.database import load_fresh, save
from app.schemas.forecast import ForecastRecord
from app.services import forecast


def test_ttl_cache_returns_fresh_and_rejects_expired():
    day = date(2099, 1, 1)
    record = ForecastRecord(
        model="ECMWF IFS",
        point_id="cache-test",
        point_name="Cache test",
        latitude=50,
        longitude=127,
        forecast_time_utc=datetime(2099, 1, 1, tzinfo=UTC),
        forecast_time_local=datetime(2099, 1, 1, tzinfo=UTC),
        fetched_at=datetime.now(UTC),
    )
    save(day, [record], {"ECMWF IFS": [{"test": True}]})
    assert len(load_fresh(day, 3600)) == 1
    assert load_fresh(day, -1) == []


async def test_horizon_switch_reuses_single_seven_day_cache(monkeypatch):
    calls = 0
    original = forecast.mock_records

    def counted(start, end=None):
        nonlocal calls
        calls += 1
        return original(start, end)

    monkeypatch.setattr(forecast, "mock_records", counted)
    refreshed, _ = await forecast.get_records(force=True)
    cached, _ = await forecast.get_records()
    assert len({record.forecast_time_local.date() for record in refreshed}) == 7
    assert len(cached) == len(refreshed)
    assert calls == 1
