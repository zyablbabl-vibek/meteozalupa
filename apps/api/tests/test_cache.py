from datetime import UTC, date, datetime

from app.db.database import load_fresh, save
from app.schemas.forecast import ForecastRecord
from app.services import forecast


def test_ttl_cache_returns_fresh_and_rejects_expired():
    day = date(2099, 1, 1)
    record = ForecastRecord(
        region_id="amur-oblast",
        model="ECMWF IFS",
        point_id="cache-test",
        point_name="Cache test",
        point_timezone="Asia/Yakutsk",
        latitude=50,
        longitude=127,
        forecast_time_utc=datetime(2099, 1, 1, tzinfo=UTC),
        forecast_time_local=datetime(2099, 1, 1, tzinfo=UTC),
        local_date=day,
        fetched_at=datetime.now(UTC),
    )
    save(
        "amur-oblast",
        day,
        [record],
        {"ECMWF IFS": [{"test": True}]},
        "Asia/Yakutsk",
        "live",
    )
    assert len(load_fresh("amur-oblast", day, 3600, "live")) == 1
    assert load_fresh("amur-oblast", day, 3600, "mock") == []
    assert load_fresh("primorsky-krai", day, 3600, "live") == []
    assert load_fresh("amur-oblast", day, -1, "live") == []


async def test_horizon_switch_reuses_single_seven_day_cache(monkeypatch):
    monkeypatch.setattr(forecast.settings, "data_mode", "mock")
    calls = 0
    original = forecast.mock_records

    def counted(region_id, start, end=None):
        nonlocal calls
        calls += 1
        return original(region_id, start, end)

    monkeypatch.setattr(forecast, "mock_records", counted)
    refreshed, _ = await forecast.get_records("amur-oblast", force=True)
    cached, _ = await forecast.get_records("amur-oblast")
    assert len({record.local_date for record in refreshed}) == 7
    assert len(cached) == len(refreshed)
    assert calls == 1
