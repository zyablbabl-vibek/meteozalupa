import asyncio
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

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


async def test_concurrent_cache_misses_fetch_each_model_once(monkeypatch):
    monkeypatch.setattr(forecast.settings, "data_mode", "live")
    stored: list[ForecastRecord] = []
    fetch_calls = 0

    def fake_load_fresh(*_args):
        return list(stored)

    def fake_save(_region_id, _day, records, *_args):
        stored[:] = records

    class FakeProvider:
        def __init__(self, _client, label: str):
            self.config = SimpleNamespace(label=label)

        async def fetch(self, _points, fetch_start, _fetch_end):
            nonlocal fetch_calls
            fetch_calls += 1
            await asyncio.sleep(0.01)
            start = fetch_start + timedelta(days=1)
            records = []
            for offset in range(7):
                day = start + timedelta(days=offset)
                timestamp = datetime.combine(day, datetime.min.time(), UTC)
                records.append(
                    ForecastRecord(
                        region_id="amur-oblast",
                        model=self.config.label,
                        point_id="blagoveshchensk",
                        point_name="Благовещенск",
                        point_timezone="Asia/Yakutsk",
                        latitude=50.29,
                        longitude=127.53,
                        forecast_time_utc=timestamp,
                        forecast_time_local=timestamp,
                        local_date=day,
                        fetched_at=datetime.now(UTC),
                        temperature_2m_c=10,
                    )
                )
            return records, [{"model": self.config.label}]

    monkeypatch.setattr(forecast, "load_fresh", fake_load_fresh)
    monkeypatch.setattr(forecast, "save", fake_save)
    monkeypatch.setattr(
        forecast, "EcmwfProvider", lambda client: FakeProvider(client, "ECMWF IFS")
    )
    monkeypatch.setattr(
        forecast, "GfsProvider", lambda client: FakeProvider(client, "NOAA GFS")
    )
    monkeypatch.setattr(
        forecast, "IconProvider", lambda client: FakeProvider(client, "DWD ICON")
    )

    first, second = await asyncio.gather(
        forecast.get_records("amur-oblast"),
        forecast.get_records("amur-oblast"),
    )

    assert fetch_calls == 3
    assert len(first[0]) == 21
    assert len(second[0]) == 21
    assert first[1] == second[1] == []
