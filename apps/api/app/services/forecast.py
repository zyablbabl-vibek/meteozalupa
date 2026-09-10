import asyncio
import logging
import math
import statistics
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from app.config.models import MODELS
from app.config.settings import settings
from app.db.database import load_cached, prune_past, save, storage_backend
from app.providers.ecmwf import EcmwfProvider
from app.providers.gfs import GfsProvider
from app.providers.icon import IconProvider
from app.regions.registry import get_region, load_points
from app.schemas.forecast import FIELD_BY_METRIC, ForecastRecord, Point
from app.services.horizons import current_local_date, filter_dates
from app.statistics.core import agreement, circular_mean, numeric_consensus
from app.statistics.events import (
    angular_distance,
    direction_label,
    event_periods,
    maximum_angular_disagreement,
    relative_spread,
)

MODEL_LABELS = tuple(model.label for model in MODELS.values())
refresh_lock = asyncio.Lock()
region_load_locks: dict[str, asyncio.Lock] = {}
region_refresh_tasks: dict[str, asyncio.Task[None]] = {}
region_refresh_attempts: dict[str, datetime] = {}
region_pruned_dates: dict[str, date] = {}
CacheMetadata = dict[str, object]
logger = logging.getLogger(__name__)


def _region_load_lock(region_id: str) -> asyncio.Lock:
    lock = region_load_locks.get(region_id)
    if lock is None:
        lock = asyncio.Lock()
        region_load_locks[region_id] = lock
    return lock


def _model_has_complete_coverage(
    records: list[ForecastRecord], model: str, region_id: str, start: date, end: date
) -> bool:
    expected_dates = {start + timedelta(days=offset) for offset in range((end - start).days + 1)}
    expected = {(point.id, day) for point in points(region_id) for day in expected_dates}
    actual = {(record.point_id, record.local_date) for record in records if record.model == model}
    return expected <= actual


def _complete_cache(
    records: list[ForecastRecord], region_id: str, start: date, end: date
) -> list[ForecastRecord] | None:
    if all(
        _model_has_complete_coverage(records, model, region_id, start, end)
        for model in MODEL_LABELS
    ):
        return records
    return None


def _model_is_fresh(records: list[ForecastRecord], model: str, cutoff: datetime) -> bool:
    model_records = [record for record in records if record.model == model]
    return bool(model_records) and min(record.fetched_at for record in model_records) >= cutoff


def _needed_ranges(
    records: list[ForecastRecord], region_id: str, start: date, end: date, force: bool = False
) -> dict[str, tuple[date, date]]:
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.forecast_cache_ttl_seconds)
    result: dict[str, tuple[date, date]] = {}
    region_point_ids = {point.id for point in points(region_id)}
    for model in MODEL_LABELS:
        if force:
            result[model] = (start, end)
            continue
        model_records = [record for record in records if record.model == model]
        covered_dates = {
            day
            for day in (start + timedelta(days=offset) for offset in range((end - start).days + 1))
            if region_point_ids
            <= {record.point_id for record in model_records if record.local_date == day}
        }
        expected_dates = {
            start + timedelta(days=offset) for offset in range((end - start).days + 1)
        }
        missing_dates = expected_dates - covered_dates
        if missing_dates:
            result[model] = (min(missing_dates), max(missing_dates))
        elif not _model_is_fresh(records, model, cutoff):
            # Existing forecast values can change after a new model run, so stale
            # future data is refreshed even when every date is already present.
            result[model] = (start, end)
    return result


def _cache_metadata(
    records: list[ForecastRecord], status: str, served_from: str, revalidating: bool
) -> CacheMetadata:
    last_updated = max((record.fetched_at for record in records), default=None)
    oldest_update = min((record.fetched_at for record in records), default=None)
    expires_at = (
        oldest_update + timedelta(seconds=settings.forecast_cache_ttl_seconds)
        if oldest_update
        else None
    )
    return {
        "status": status,
        "served_from": served_from,
        "storage": storage_backend(),
        "persistent": storage_backend() == "postgresql",
        "revalidating": revalidating,
        "last_updated": last_updated,
        "expires_at": expires_at,
    }


def points(region_id: str) -> list[Point]:
    return list(load_points(region_id))


def mock_records(
    region_id: str, start_day: date, end_day: date | None = None
) -> list[ForecastRecord]:
    end = end_day or start_day
    result: list[ForecastRecord] = []
    fetched = datetime.now(UTC)
    total_days = (end - start_day).days + 1
    region_points = points(region_id)
    region_bias = (sum(ord(char) for char in region_id) % 17 - 8) * 0.7
    for day_offset in range(total_days):
        day = start_day + timedelta(days=day_offset)
        for p_index, point in enumerate(region_points):
            for model_index, model in enumerate(MODEL_LABELS):
                if (
                    (point.id == "seryshevo" or region_id == "magadan-oblast")
                    and model == "DWD ICON"
                    and p_index % 4 == 0
                ):
                    continue
                for hour in range(24):
                    local = datetime.combine(
                        day, datetime.min.time(), ZoneInfo(point.timezone)
                    ).replace(hour=hour)
                    phase = math.sin((hour - 7) * math.pi / 12)
                    day_wave = math.sin(day_offset * math.pi / 3) * 2.2
                    deviation = (model_index - 1) * (
                        4.5
                        if (point.id == "tynda" or region_id == "sakha-yakutia") and day_offset == 2
                        else 0.7
                    )
                    rain = (
                        2.4 + day_offset * 0.15
                        if (
                            point.id == "ekimchan"
                            or (region_id == "kamchatka-krai" and p_index == 0)
                        )
                        and 11 <= hour <= 15
                        else max(0, math.sin(hour + day_offset) * 0.15)
                    )
                    if region_id == "jewish-autonomous-oblast":
                        rain = min(rain, 0.05)
                    direction = (
                        [350, 10, 2][model_index]
                        if point.id == "blagoveshchensk"
                        else (210 + p_index * 4 + model_index * 8 + day_offset * 3) % 360
                    )
                    result.append(
                        ForecastRecord(
                            region_id=region_id,
                            provider="Mock",
                            model=model,
                            point_id=point.id,
                            point_name=point.name,
                            point_timezone=point.timezone,
                            latitude=point.latitude,
                            longitude=point.longitude,
                            forecast_time_utc=local.astimezone(UTC),
                            forecast_time_local=local,
                            local_date=day,
                            fetched_at=fetched,
                            temperature_2m_c=(
                                15 + region_bias + phase * 9 + day_wave - p_index * 0.18 + deviation
                            ),
                            relative_humidity_2m_pct=65 - phase * 18 + model_index * 2,
                            pressure_msl_hpa=1008 + math.sin(hour / 4) * 3 + model_index,
                            precipitation_mm=rain * (0.8 + model_index * 0.2),
                            cloud_cover_pct=min(100, max(0, 45 - phase * 25 + model_index * 7)),
                            wind_speed_10m_ms=(
                                2.5 + p_index * 0.08 + model_index * 0.35 + day_offset * 0.1
                            ),
                            wind_direction_10m_deg=direction,
                            wind_gusts_10m_ms=(
                                24
                                if (
                                    point.id == "skovorodino"
                                    or region_id == "chukotka-autonomous-okrug"
                                )
                                and model_index == 2
                                and hour == 16
                                and day_offset == 4
                                else 5 + p_index * 0.15 + model_index + day_offset * 0.2
                            ),
                        )
                    )
    return result


async def _fetch_ranges(region_id: str, ranges: dict[str, tuple[date, date]]) -> list[str]:
    if not ranges:
        return []
    region = get_region(region_id)
    fetched_records: list[ForecastRecord] = []
    raw: dict[str, list[dict]] = {}
    errors: list[str] = []
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=settings.open_meteo_max_concurrency)
    ) as client:
        providers = [EcmwfProvider(client), GfsProvider(client), IconProvider(client)]
        selected = [provider for provider in providers if provider.config.label in ranges]
        results = await asyncio.gather(
            *(
                provider.fetch(
                    points(region_id),
                    ranges[provider.config.label][0] - timedelta(days=1),
                    ranges[provider.config.label][1] + timedelta(days=1),
                )
                for provider in selected
            ),
            return_exceptions=True,
        )
        for provider, result in zip(selected, results, strict=True):
            if isinstance(result, BaseException):
                errors.append(f"{provider.config.label}: {result}")
                continue
            provider_records, provider_raw = result
            range_start, range_end = ranges[provider.config.label]
            fetched_records.extend(
                record
                for record in provider_records
                if range_start <= record.local_date <= range_end
            )
            raw[provider.config.label] = provider_raw
    if fetched_records:
        save(
            region_id,
            min(start for start, _ in ranges.values()),
            fetched_records,
            raw,
            region.primary_timezone,
            "live",
        )
    return errors


async def _refresh_region(region_id: str, start: date, end: date) -> None:
    async with _region_load_lock(region_id):
        cached = load_cached(region_id, start, end, settings.data_mode)
        await _fetch_ranges(region_id, _needed_ranges(cached, region_id, start, end))


def _schedule_refresh(region_id: str, start: date, end: date) -> bool:
    running = region_refresh_tasks.get(region_id)
    if running is not None and not running.done():
        return True
    last_attempt = region_refresh_attempts.get(region_id)
    cooldown = timedelta(seconds=60)
    if last_attempt is not None and datetime.now(UTC) - last_attempt < cooldown:
        return False
    region_refresh_attempts[region_id] = datetime.now(UTC)
    task = asyncio.create_task(_refresh_region(region_id, start, end))
    region_refresh_tasks[region_id] = task

    def discard(completed: asyncio.Task[None]) -> None:
        if region_refresh_tasks.get(region_id) is completed:
            region_refresh_tasks.pop(region_id, None)
        try:
            completed.result()
        except Exception:
            logger.exception("Background forecast refresh failed for region %s", region_id)

    task.add_done_callback(discard)
    return True


def _prune_region_once_per_day(region_id: str, today: date) -> None:
    if region_pruned_dates.get(region_id) == today:
        return
    region_pruned_dates[region_id] = today
    prune_past(region_id, today, settings.forecast_retention_past_days)


async def get_records(
    region_id: str, force: bool = False
) -> tuple[list[ForecastRecord], list[str], CacheMetadata]:
    region = get_region(region_id)
    start = current_local_date(region.primary_timezone)
    end = start + timedelta(days=6)
    _prune_region_once_per_day(region_id, start)
    cached = load_cached(region_id, start, end, settings.data_mode)

    if not force and cached:
        needed = _needed_ranges(cached, region_id, start, end)
        if not needed:
            return cached, [], _cache_metadata(cached, "fresh", "cache", False)
        revalidating = _schedule_refresh(region_id, start, end)
        status = (
            "stale" if _complete_cache(cached, region_id, start, end) is not None else "partial"
        )
        return cached, [], _cache_metadata(cached, status, "cache", revalidating)

    async with _region_load_lock(region_id):
        cached = load_cached(region_id, start, end, settings.data_mode)
        if not force and cached:
            needed = _needed_ranges(cached, region_id, start, end)
            if not needed:
                return cached, [], _cache_metadata(cached, "fresh", "cache", False)
            revalidating = _schedule_refresh(region_id, start, end)
            status = (
                "stale" if _complete_cache(cached, region_id, start, end) is not None else "partial"
            )
            return cached, [], _cache_metadata(cached, status, "cache", revalidating)

        if settings.data_mode == "mock":
            mock_data = mock_records(region_id, start, end)
            save(
                region_id,
                start,
                mock_data,
                {"mock": [{"deterministic": True, "days": 7, "region_id": region_id}]},
                region.primary_timezone,
                "mock",
            )
            return mock_data, [], _cache_metadata(mock_data, "refreshed", "generated", False)

        ranges = _needed_ranges(cached, region_id, start, end, force=force)
        errors = await _fetch_ranges(region_id, ranges)
        records = load_cached(region_id, start, end, settings.data_mode)
        still_needed = _needed_ranges(records, region_id, start, end)
        complete = _complete_cache(records, region_id, start, end) is not None
        status = "refreshed" if complete and not still_needed else "partial"
        revalidating = bool(records and still_needed and _schedule_refresh(region_id, start, end))
        return records, errors, _cache_metadata(records, status, "open_meteo", revalidating)


def hourly(records: list[ForecastRecord], metric: str) -> list[dict]:
    grouped: dict[tuple[str, datetime], list[ForecastRecord]] = defaultdict(list)
    field = FIELD_BY_METRIC[metric]
    for record in records:
        grouped[(record.point_id, record.forecast_time_utc)].append(record)
    result = []
    for (point_id, timestamp), group in grouped.items():
        values = {record.model: getattr(record, field) for record in group}
        stats = numeric_consensus(values)
        if metric == "wind_direction_10m" and stats.get("consensus_available"):
            stats["mean"] = circular_mean(v for v in values.values() if v is not None)
            stats["median"] = None
            stats["median_note"] = "Для направления ветра медиана не рассчитывается"
        result.append(
            {
                "point_id": point_id,
                "region_id": group[0].region_id,
                "point_name": group[0].point_name,
                "point_timezone": group[0].point_timezone,
                "latitude": group[0].latitude,
                "longitude": group[0].longitude,
                "forecast_time_utc": timestamp,
                "forecast_time_local": group[0].forecast_time_local,
                "models": values,
                "statistics": stats,
                "agreement": agreement(metric, stats.get("range")),
            }
        )
    return sorted(result, key=lambda item: (item["point_id"], item["forecast_time_utc"]))


def _aggregate(values: list[float], operation: str) -> float | None:
    if not values:
        return None
    if operation == "min":
        return min(values)
    if operation == "max":
        return max(values)
    if operation == "sum":
        return sum(values)
    if operation == "circular":
        return circular_mean(values)
    return statistics.fmean(values)


DAILY_OPERATIONS = {
    "temperature_min": ("temperature_2m_c", "min"),
    "temperature_max": ("temperature_2m_c", "max"),
    "temperature_mean": ("temperature_2m_c", "mean"),
    "precipitation_sum": ("precipitation_mm", "sum"),
    "humidity_mean": ("relative_humidity_2m_pct", "mean"),
    "pressure_mean": ("pressure_msl_hpa", "mean"),
    "cloud_cover_mean": ("cloud_cover_pct", "mean"),
    "wind_speed_mean": ("wind_speed_10m_ms", "mean"),
    "wind_speed_max": ("wind_speed_10m_ms", "max"),
    "wind_gust_max": ("wind_gusts_10m_ms", "max"),
    "wind_direction_circular_mean": ("wind_direction_10m_deg", "circular"),
}
AGREEMENT_METRIC_BY_DAILY = {
    "temperature_min": "temperature_2m",
    "temperature_max": "temperature_2m",
    "temperature_mean": "temperature_2m",
    "precipitation_sum": "precipitation",
    "humidity_mean": "relative_humidity_2m",
    "pressure_mean": "pressure_msl",
    "cloud_cover_mean": "cloud_cover",
    "wind_speed_mean": "wind_speed_10m",
    "wind_speed_max": "wind_speed_10m",
    "wind_gust_max": "wind_gusts_10m",
    "wind_direction_circular_mean": "wind_direction_10m",
}


def daily_model_aggregates(records: list[ForecastRecord]) -> list[dict]:
    grouped: dict[tuple[str, date, str], list[ForecastRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.point_id, record.local_date, record.model)].append(record)
    result = []
    for (point_id, day, model), group in grouped.items():
        values: dict[str, float | None] = {}
        for name, (field, operation) in DAILY_OPERATIONS.items():
            available = [
                getattr(record, field) for record in group if getattr(record, field) is not None
            ]
            values[name] = _aggregate(available, operation)
        result.append(
            {
                "date": day,
                "point_id": point_id,
                "region_id": group[0].region_id,
                "point_name": group[0].point_name,
                "point_timezone": group[0].point_timezone,
                "model": model,
                **values,
            }
        )
    return sorted(result, key=lambda item: (item["date"], item["point_id"], item["model"]))


def precipitation_analysis(records: list[ForecastRecord], daily_total: dict) -> dict:
    hourly_rows = hourly(records, "precipitation")
    peak_record = max(
        (record for record in records if record.precipitation_mm is not None),
        key=lambda record: (
            record.precipitation_mm if record.precipitation_mm is not None else -math.inf
        ),
        default=None,
    )
    peak_row = next(
        (
            row
            for row in hourly_rows
            if peak_record is not None and row["forecast_time_utc"] == peak_record.forecast_time_utc
        ),
        None,
    )
    timeline = [(row["forecast_time_local"], row["statistics"].get("mean")) for row in hourly_rows]
    periods = event_periods(timeline, settings.precipitation_event_threshold_mm)
    longest = max(periods, key=lambda item: item["duration_hours"], default=None)
    starts_by_model = {}
    for model in MODEL_LABELS:
        first = next(
            (
                record.forecast_time_local
                for record in sorted(records, key=lambda item: item.forecast_time_local)
                if record.model == model
                and record.precipitation_mm is not None
                and record.precipitation_mm >= settings.precipitation_event_threshold_mm
            ),
            None,
        )
        starts_by_model[model] = first
    valid_starts = [value for value in starts_by_model.values() if value is not None]
    start_disagreement = (
        (max(valid_starts) - min(valid_starts)).total_seconds() / 3600
        if len(valid_starts) >= 2
        else None
    )
    return {
        "daily_total": daily_total,
        "relative_spread_pct": relative_spread(daily_total.get("mean"), daily_total.get("range")),
        "hourly_peak": peak_row["statistics"] if peak_row else {},
        "peak_time": peak_record.forecast_time_local if peak_record else None,
        "peak_model": peak_record.model if peak_record else None,
        "peak_value": peak_record.precipitation_mm if peak_record else None,
        "event_start": longest["start"] if longest else None,
        "event_end": longest["end"] if longest else None,
        "duration_hours": longest["duration_hours"] if longest else 0,
        "event_count": len(periods),
        "hours_above_threshold": sum(
            1
            for _, value in timeline
            if value is not None and value >= settings.precipitation_event_threshold_mm
        ),
        "confirming_models": sum(
            1
            for value in daily_total_model_values(daily_total).values()
            if value is not None and value >= settings.precipitation_event_threshold_mm
        ),
        "starts_by_model": starts_by_model,
        "start_time_disagreement_hours": start_disagreement,
    }


def daily_total_model_values(stats: dict) -> dict[str, float | None]:
    return stats.get("model_values", {})


def wind_analysis(records: list[ForecastRecord], rows: list[dict], by_metric: dict) -> dict:
    directions = {
        model: next(
            (row["wind_direction_circular_mean"] for row in rows if row["model"] == model),
            None,
        )
        for model in MODEL_LABELS
    }
    circular = circular_mean(value for value in directions.values() if value is not None)
    disagreement = maximum_angular_disagreement(directions)
    peak_record = max(
        (record for record in records if record.wind_gusts_10m_ms is not None),
        key=lambda record: (
            record.wind_gusts_10m_ms if record.wind_gusts_10m_ms is not None else -math.inf
        ),
        default=None,
    )
    speed_rows = hourly(records, "wind_speed_10m")
    timeline = [(row["forecast_time_local"], row["statistics"].get("mean")) for row in speed_rows]
    periods = event_periods(timeline, settings.wind_speed_attention_ms)
    longest = max(periods, key=lambda item: item["duration_hours"], default=None)
    direction_rows = hourly(records, "wind_direction_10m")
    hourly_directions = [
        (row["forecast_time_local"], row["statistics"].get("mean"))
        for row in direction_rows
        if row["statistics"].get("mean") is not None
    ]
    direction_changes = [
        {
            "value": angular_distance(previous[1], current[1]),
            "start": previous[0],
            "end": current[0],
        }
        for previous, current in zip(hourly_directions, hourly_directions[1:], strict=False)
    ]
    largest_change = max(direction_changes, key=lambda item: item["value"], default=None)
    return {
        "mean_speed": by_metric["wind_speed_mean"],
        "maximum_speed": by_metric["wind_speed_max"],
        "maximum_gust": by_metric["wind_gust_max"],
        "maximum_gust_time": peak_record.forecast_time_local if peak_record else None,
        "maximum_gust_model": peak_record.model if peak_record else None,
        "maximum_gust_value": peak_record.wind_gusts_10m_ms if peak_record else None,
        "circular_mean_direction_deg": circular,
        "direction_label": direction_label(circular),
        "directions_by_model": directions,
        "direction_labels_by_model": {
            model: direction_label(value) for model, value in directions.items()
        },
        "maximum_direction_disagreement_deg": disagreement["value"],
        "direction_disagreement_models": disagreement["models"],
        "direction_agreement": agreement("wind_direction_10m", disagreement["value"]),
        "maximum_direction_change_deg": (largest_change["value"] if largest_change else None),
        "direction_change_start": largest_change["start"] if largest_change else None,
        "direction_change_end": largest_change["end"] if largest_change else None,
        "strong_wind_start": longest["start"] if longest else None,
        "strong_wind_end": longest["end"] if longest else None,
        "strong_wind_duration_hours": longest["duration_hours"] if longest else 0,
        "strong_wind_event_count": len(periods),
    }


def point_summaries(records: list[ForecastRecord]) -> list[dict]:
    aggregates = daily_model_aggregates(records)
    output = []
    region_id = records[0].region_id if records else None
    for point in points(region_id) if region_id else []:
        point_records = [record for record in records if record.point_id == point.id]
        rows = [row for row in aggregates if row["point_id"] == point.id]
        if not rows:
            continue
        by_metric = {}
        for metric in DAILY_OPERATIONS:
            model_values = {
                model: next((row[metric] for row in rows if row["model"] == model), None)
                for model in MODEL_LABELS
            }
            by_metric[metric] = {
                **numeric_consensus(model_values),
                "model_values": model_values,
            }
            by_metric[metric]["agreement"] = agreement(
                AGREEMENT_METRIC_BY_DAILY[metric],
                by_metric[metric].get("range"),
            )
        temp_mean = by_metric["temperature_mean"]
        temp_min = by_metric["temperature_min"]
        temp_max = by_metric["temperature_max"]
        if not temp_mean.get("consensus_available"):
            continue
        spread_values = [
            by_metric[key]["range"]
            for key in ("temperature_min", "temperature_max", "temperature_mean")
            if by_metric[key].get("range") is not None
        ]
        if not spread_values:
            continue
        spread = max(spread_values)
        output.append(
            {
                "point": point.model_dump(),
                "mean_temperature": temp_mean["mean"],
                "models": {
                    model: next(
                        (row["temperature_mean"] for row in rows if row["model"] == model),
                        None,
                    )
                    for model in MODEL_LABELS
                },
                "minimum": temp_min.get("minimum"),
                "minimum_source": temp_min.get("minimum_source"),
                "maximum": temp_max.get("maximum"),
                "maximum_source": temp_max.get("maximum_source"),
                "spread": spread,
                "agreement": agreement("temperature_2m", spread),
                "precipitation": by_metric["precipitation_sum"],
                "wind_speed": by_metric["wind_speed_mean"],
                "humidity": by_metric["humidity_mean"],
                "pressure": by_metric["pressure_mean"],
                "max_gust": by_metric["wind_gust_max"].get("maximum"),
                "max_gust_source": by_metric["wind_gust_max"].get("maximum_source"),
                "precipitation_analysis": precipitation_analysis(
                    point_records, by_metric["precipitation_sum"]
                ),
                "wind_analysis": wind_analysis(point_records, rows, by_metric),
                "daily_aggregates": by_metric,
                "incomplete": any(not stats.get("complete", False) for stats in by_metric.values()),
            }
        )
    return sorted(output, key=lambda item: item["spread"], reverse=True)


def _extreme(
    records: list[ForecastRecord], field: str, mode: str, metric: str, unit: str
) -> dict | None:
    available = [record for record in records if getattr(record, field) is not None]
    if not available:
        return None
    record = (max if mode == "max" else min)(available, key=lambda item: getattr(item, field))
    return {
        "metric": metric,
        "region_id": record.region_id,
        "value": getattr(record, field),
        "unit": unit,
        "date": record.forecast_time_local.date(),
        "forecast_time": record.forecast_time_local,
        "point_id": record.point_id,
        "point_name": record.point_name,
        "point_timezone": record.point_timezone,
        "model": record.model,
    }


def daily_summary(records: list[ForecastRecord], day: date) -> dict:
    day_records = filter_dates(records, [day])
    point_data = point_summaries(day_records)
    if not point_data:
        return {"date": day, "available": False}
    model_rows = daily_model_aggregates(day_records)
    weight_by_point = {point.id: point.weight for point in points(day_records[0].region_id)}

    def available_values(rows: list[dict], field: str) -> list[float]:
        return [row[field] for row in rows if row[field] is not None]

    def weighted_mean(rows: list[dict], field: str) -> float | None:
        weighted = [
            (row[field], weight_by_point[row["point_id"]])
            for row in rows
            if row[field] is not None and row["point_id"] in weight_by_point
        ]
        if not weighted:
            return None
        return sum(value * weight for value, weight in weighted) / sum(
            weight for _, weight in weighted
        )

    models: dict[str, dict[str, float | None] | None] = {}
    for model in MODEL_LABELS:
        rows = [row for row in model_rows if row["model"] == model]
        if not rows:
            models[model] = None
            continue
        temperature_mins = available_values(rows, "temperature_min")
        temperature_maxes = available_values(rows, "temperature_max")
        gusts_by_model = available_values(rows, "wind_gust_max")
        models[model] = {
            "temperature_min": min(temperature_mins) if temperature_mins else None,
            "temperature_max": max(temperature_maxes) if temperature_maxes else None,
            "temperature_mean": weighted_mean(rows, "temperature_mean"),
            # Regional precipitation is a weighted spatial mean. Values from
            # different points are never added together.
            "precipitation_sum": weighted_mean(rows, "precipitation_sum"),
            "wind_speed_mean": weighted_mean(rows, "wind_speed_mean"),
            "wind_gust_max": max(gusts_by_model) if gusts_by_model else None,
        }
    regional_precipitation_daily = numeric_consensus(
        {
            model: values["precipitation_sum"] if values is not None else None
            for model, values in models.items()
        }
    )
    spreads = [item["spread"] for item in point_data]

    def point_mean(metric: str) -> float | None:
        available = [
            item[metric]["mean"] for item in point_data if item[metric].get("mean") is not None
        ]
        return statistics.fmean(available) if available else None

    gusts = [item["max_gust"] for item in point_data if item["max_gust"] is not None]
    return {
        "region_id": day_records[0].region_id,
        "date": day,
        "available": True,
        "mean_temperature": statistics.fmean(item["mean_temperature"] for item in point_data),
        "minimum_temperature": min(item["minimum"] for item in point_data),
        "maximum_temperature": max(item["maximum"] for item in point_data),
        "precipitation_sum": regional_precipitation_daily.get("mean"),
        "mean_wind_speed": point_mean("wind_speed"),
        "max_gust": max(gusts) if gusts else None,
        "mean_humidity": point_mean("humidity"),
        "mean_pressure": point_mean("pressure"),
        "spread": max(spreads),
        "agreement": agreement("temperature_2m", max(spreads)),
        "models": models,
        "extremes": {
            "highest_temperature": _extreme(
                day_records, "temperature_2m_c", "max", "temperature_2m", "°C"
            ),
            "lowest_temperature": _extreme(
                day_records, "temperature_2m_c", "min", "temperature_2m", "°C"
            ),
            "max_gust": _extreme(day_records, "wind_gusts_10m_ms", "max", "wind_gusts_10m", "m/s"),
        },
        "model_availability": {
            model: any(record.model == model for record in day_records) for model in MODEL_LABELS
        },
    }


def period_summary(records: list[ForecastRecord], dates: list[date]) -> dict:
    selected = filter_dates(records, dates)
    summaries = [daily_summary(selected, day) for day in dates]
    available = [item for item in summaries if item.get("available")]
    aggregates = daily_model_aggregates(selected)
    precipitation_points = []
    region_id = selected[0].region_id if selected else None
    for point in points(region_id) if region_id else []:
        values: dict[str, float | None] = {}
        for model in MODEL_LABELS:
            model_rows = [
                row for row in aggregates if row["model"] == model and row["point_id"] == point.id
            ]
            model_totals = [
                row["precipitation_sum"]
                for row in model_rows
                if row["precipitation_sum"] is not None
            ]
            complete_days = {row["date"] for row in model_rows} == set(dates)
            values[model] = (
                sum(model_totals) if complete_days and len(model_totals) == len(dates) else None
            )
        stats = numeric_consensus(values)
        if stats.get("consensus_available"):
            precipitation_points.append(
                {"point": point.model_dump(), "models": values, "statistics": stats}
            )
    wettest_point = max(
        precipitation_points,
        key=lambda item: item["statistics"]["mean"],
        default=None,
    )
    if not available:
        return {"available": False}
    regional_precipitation_by_model: dict[str, float | None] = {}
    regional_model_day_counts: dict[str, int] = {}
    for model in MODEL_LABELS:
        daily_values = [
            item["models"][model]["precipitation_sum"]
            for item in summaries
            if item.get("available")
            and item["models"].get(model) is not None
            and item["models"][model]["precipitation_sum"] is not None
        ]
        regional_model_day_counts[model] = len(daily_values)
        regional_precipitation_by_model[model] = (
            sum(daily_values) if len(daily_values) == len(dates) else None
        )
    regional_precipitation_stats = numeric_consensus(regional_precipitation_by_model)
    warmest = max(available, key=lambda item: item["mean_temperature"])
    coldest = min(available, key=lambda item: item["mean_temperature"])
    wettest = max(available, key=lambda item: item["precipitation_sum"])
    gustiest = max(available, key=lambda item: item["max_gust"])
    divergent = max(available, key=lambda item: item["spread"])
    direction_by_model = [
        circular_mean(
            record.wind_direction_10m_deg
            for record in selected
            if record.model == model and record.wind_direction_10m_deg is not None
        )
        for model in MODEL_LABELS
    ]
    temperature_by_model: dict[str, float | None] = {
        model: statistics.fmean(
            record.temperature_2m_c
            for record in selected
            if record.model == model and record.temperature_2m_c is not None
        )
        for model in MODEL_LABELS
        if any(record.model == model and record.temperature_2m_c is not None for record in selected)
    }
    temperature_stats = numeric_consensus(temperature_by_model)
    return {
        "available": True,
        "region_id": selected[0].region_id,
        "period_start": dates[0],
        "period_end": dates[-1],
        "warmest_day": warmest,
        "coldest_day": coldest,
        "wettest_day": wettest,
        "gustiest_day": gustiest,
        "most_divergent_day": divergent,
        "temperature": {
            "absolute_maximum": _extreme(
                selected, "temperature_2m_c", "max", "temperature_2m", "°C"
            ),
            "absolute_minimum": _extreme(
                selected, "temperature_2m_c", "min", "temperature_2m", "°C"
            ),
            "mean": temperature_stats.get("mean"),
            "mean_by_model": temperature_by_model,
            "mean_statistics": temperature_stats,
        },
        "precipitation": wettest_point,
        "regional_precipitation": {
            "models": regional_precipitation_by_model,
            "statistics": regional_precipitation_stats,
            "expected_days": len(dates),
            "model_day_counts": regional_model_day_counts,
            "method": "weighted_spatial_mean_then_period_sum",
        },
        "wind": {
            "maximum_speed": _extreme(
                selected, "wind_speed_10m_ms", "max", "wind_speed_10m", "m/s"
            ),
            "maximum_gust": _extreme(selected, "wind_gusts_10m_ms", "max", "wind_gusts_10m", "m/s"),
            "circular_mean_direction": circular_mean(
                direction for direction in direction_by_model if direction is not None
            ),
            "direction_by_model": dict(zip(MODEL_LABELS, direction_by_model, strict=True)),
        },
    }
