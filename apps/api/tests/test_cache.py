import asyncio
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from app.db.database import load_cached, prune_past, save
from app.schemas.forecast import ForecastRecord
from app.services import forecast


def test_cache_is_scoped_by_source_region_and_period():
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
    assert len(load_cached("amur-oblast", day, day, "live")) == 1
    assert load_cached("amur-oblast", day, day, "mock") == []
    assert load_cached("primorsky-krai", day, day, "live") == []


def test_cache_prunes_days_before_region_today():
    old_day = date(2000, 1, 1)
    record = ForecastRecord(
        region_id="amur-oblast",
        model="ECMWF IFS",
        point_id="old-cache-test",
        point_name="Old cache test",
        point_timezone="Asia/Yakutsk",
        latitude=50,
        longitude=127,
        forecast_time_utc=datetime(2000, 1, 1, tzinfo=UTC),
        forecast_time_local=datetime(2000, 1, 1, tzinfo=UTC),
        local_date=old_day,
        fetched_at=datetime.now(UTC),
    )
    save("amur-oblast", old_day, [record], {}, "Asia/Yakutsk", "live")

    assert prune_past("amur-oblast", date(2000, 1, 2)) >= 1
    assert load_cached("amur-oblast", old_day, old_day, "live") == []


def test_saving_one_model_keeps_other_models_in_same_period():
    day = date(2098, 1, 1)

    def record(model: str) -> ForecastRecord:
        timestamp = datetime(2098, 1, 1, tzinfo=UTC)
        return ForecastRecord(
            region_id="amur-oblast",
            model=model,
            point_id="merge-cache-test",
            point_name="Merge cache test",
            point_timezone="Asia/Yakutsk",
            latitude=50,
            longitude=127,
            forecast_time_utc=timestamp,
            forecast_time_local=timestamp,
            local_date=day,
            fetched_at=datetime.now(UTC),
        )

    save("amur-oblast", day, [record("ECMWF IFS")], {}, "Asia/Yakutsk", "live")
    save("amur-oblast", day, [record("NOAA GFS")], {}, "Asia/Yakutsk", "live")

    cached = load_cached("amur-oblast", day, day, "live")
    assert {item.model for item in cached if item.point_id == "merge-cache-test"} == {
        "ECMWF IFS",
        "NOAA GFS",
    }


def test_partial_provider_response_keeps_unreturned_points():
    day = date(2096, 1, 1)

    def record(point_id: str, temperature: float) -> ForecastRecord:
        timestamp = datetime(2096, 1, 1, tzinfo=UTC)
        return ForecastRecord(
            region_id="amur-oblast",
            model="ECMWF IFS",
            point_id=point_id,
            point_name=point_id,
            point_timezone="Asia/Yakutsk",
            latitude=50,
            longitude=127,
            forecast_time_utc=timestamp,
            forecast_time_local=timestamp,
            local_date=day,
            fetched_at=datetime.now(UTC),
            temperature_2m_c=temperature,
        )

    save(
        "amur-oblast",
        day,
        [record("kept-point", 1), record("updated-point", 2)],
        {},
        "Asia/Yakutsk",
        "live",
    )
    save(
        "amur-oblast",
        day,
        [record("updated-point", 3)],
        {},
        "Asia/Yakutsk",
        "live",
    )

    cached = load_cached("amur-oblast", day, day, "live")
    values = {
        item.point_id: item.temperature_2m_c
        for item in cached
        if item.point_id in {"kept-point", "updated-point"}
    }
    assert values == {"kept-point": 1, "updated-point": 3}


def test_only_missing_edge_day_is_requested():
    start = date(2097, 1, 1)
    end = start + timedelta(days=6)
    records = forecast.mock_records("amur-oblast", start, end)
    records = [
        record
        for record in records
        if not (record.model == "DWD ICON" and record.local_date == end)
    ]

    assert forecast._needed_ranges(records, "amur-oblast", start, end) == {"DWD ICON": (end, end)}


async def test_horizon_switch_reuses_single_seven_day_cache(monkeypatch):
    monkeypatch.setattr(forecast.settings, "data_mode", "mock")
    calls = 0
    original = forecast.mock_records

    def counted(region_id, start, end=None):
        nonlocal calls
        calls += 1
        return original(region_id, start, end)

    monkeypatch.setattr(forecast, "mock_records", counted)
    refreshed, _, refreshed_cache = await forecast.get_records("amur-oblast", force=True)
    cached, _, cached_cache = await forecast.get_records("amur-oblast")
    assert len({record.local_date for record in refreshed}) == 7
    assert len(cached) == len(refreshed)
    assert calls == 1
    assert refreshed_cache["served_from"] == "generated"
    assert cached_cache["served_from"] == "cache"


async def test_concurrent_cache_misses_fetch_each_model_once(monkeypatch):
    monkeypatch.setattr(forecast.settings, "data_mode", "live")
    stored: list[ForecastRecord] = []
    fetch_calls = 0

    def fake_load_cached(*_args):
        return list(stored)

    def fake_save(_region_id, _day, records, *_args):
        stored[:] = records

    class FakeProvider:
        def __init__(self, _client, label: str):
            self.config = SimpleNamespace(label=label)

        async def fetch(self, requested_points, fetch_start, _fetch_end):
            nonlocal fetch_calls
            fetch_calls += 1
            await asyncio.sleep(0.01)
            start = fetch_start + timedelta(days=1)
            records = []
            for offset in range(7):
                day = start + timedelta(days=offset)
                for point in requested_points:
                    timestamp = datetime.combine(day, datetime.min.time(), UTC)
                    records.append(
                        ForecastRecord(
                            region_id="amur-oblast",
                            model=self.config.label,
                            point_id=point.id,
                            point_name=point.name,
                            point_timezone=point.timezone,
                            latitude=point.latitude,
                            longitude=point.longitude,
                            forecast_time_utc=timestamp,
                            forecast_time_local=timestamp,
                            local_date=day,
                            fetched_at=datetime.now(UTC),
                            temperature_2m_c=10,
                        )
                    )
            return records, [{"model": self.config.label}]

    monkeypatch.setattr(forecast, "load_cached", fake_load_cached)
    monkeypatch.setattr(forecast, "prune_past", lambda *_args: 0)
    monkeypatch.setattr(forecast, "save", fake_save)
    monkeypatch.setattr(forecast, "EcmwfProvider", lambda client: FakeProvider(client, "ECMWF IFS"))
    monkeypatch.setattr(forecast, "GfsProvider", lambda client: FakeProvider(client, "NOAA GFS"))
    monkeypatch.setattr(forecast, "IconProvider", lambda client: FakeProvider(client, "DWD ICON"))

    first, second = await asyncio.gather(
        forecast.get_records("amur-oblast"),
        forecast.get_records("amur-oblast"),
    )

    assert fetch_calls == 3
    expected = len(forecast.points("amur-oblast")) * 7 * 3
    assert len(first[0]) == expected
    assert len(second[0]) == expected
    assert first[1] == second[1] == []
    assert first[2]["served_from"] == "open_meteo"
    assert second[2]["served_from"] == "cache"
