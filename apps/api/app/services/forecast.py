import asyncio
import json
import math
import statistics
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from app.config.models import MODELS
from app.config.settings import settings
from app.db.database import load_fresh, save
from app.providers.ecmwf import EcmwfProvider
from app.providers.gfs import GfsProvider
from app.providers.icon import IconProvider
from app.schemas.forecast import FIELD_BY_METRIC, ForecastRecord, Point
from app.services.horizons import current_local_date, filter_dates
from app.statistics.core import agreement, circular_mean, numeric_consensus

LOCAL_TZ = ZoneInfo("Asia/Yakutsk")
MODEL_LABELS = tuple(model.label for model in MODELS.values())
refresh_lock = asyncio.Lock()


def points() -> list[Point]:
    payload = json.loads(Path(settings.points_file).read_text())
    return [Point.model_validate(item) for item in payload["points"]]


def mock_records(start_day: date, end_day: date | None = None) -> list[ForecastRecord]:
    end = end_day or start_day
    result: list[ForecastRecord] = []
    fetched = datetime.now(UTC)
    total_days = (end - start_day).days + 1
    for day_offset in range(total_days):
        day = start_day + timedelta(days=day_offset)
        for p_index, point in enumerate(points()):
            for model_index, model in enumerate(MODEL_LABELS):
                if point.id == "seryshevo" and model == "DWD ICON":
                    continue
                for hour in range(24):
                    local = datetime.combine(day, datetime.min.time(), LOCAL_TZ).replace(hour=hour)
                    phase = math.sin((hour - 7) * math.pi / 12)
                    day_wave = math.sin(day_offset * math.pi / 3) * 2.2
                    deviation = (model_index - 1) * (
                        4.5 if point.id == "tynda" and day_offset == 2 else 0.7
                    )
                    rain = (
                        2.4 + day_offset * 0.15
                        if point.id == "ekimchan" and 11 <= hour <= 15
                        else max(0, math.sin(hour + day_offset) * 0.15)
                    )
                    direction = (
                        [350, 10, 2][model_index]
                        if point.id == "blagoveshchensk"
                        else (210 + p_index * 4 + model_index * 8 + day_offset * 3) % 360
                    )
                    result.append(
                        ForecastRecord(
                            model=model,
                            point_id=point.id,
                            point_name=point.name,
                            latitude=point.latitude,
                            longitude=point.longitude,
                            forecast_time_utc=local.astimezone(UTC),
                            forecast_time_local=local,
                            fetched_at=fetched,
                            temperature_2m_c=(
                                15 + phase * 9 + day_wave - p_index * 0.35 + deviation
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
                                15
                                if point.id == "skovorodino"
                                and model_index == 2
                                and hour == 16
                                and day_offset == 4
                                else 5 + p_index * 0.15 + model_index + day_offset * 0.2
                            ),
                        )
                    )
    return result


async def get_records(force: bool = False) -> tuple[list[ForecastRecord], list[str]]:
    start = current_local_date()
    end = start + timedelta(days=6)
    if not force:
        cached = load_fresh(start, settings.forecast_cache_ttl_seconds)
        cached_days = {record.forecast_time_local.date() for record in cached}
        if len(cached_days) == 7:
            return cached, []
    if settings.data_mode == "mock":
        mock_data = mock_records(start, end)
        save(start, mock_data, {"mock": [{"deterministic": True, "days": 7}]})
        return mock_data, []
    errors: list[str] = []
    records: list[ForecastRecord] = []
    raw: dict[str, list[dict]] = {}
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=3)) as client:
        providers = [EcmwfProvider(client), GfsProvider(client), IconProvider(client)]
        results = await asyncio.gather(
            *(provider.fetch(points(), start, end) for provider in providers),
            return_exceptions=True,
        )
        for provider, result in zip(providers, results, strict=True):
            if isinstance(result, BaseException):
                errors.append(f"{provider.config.label}: {result}")
            else:
                provider_records, provider_raw = result
                records.extend(provider_records)
                raw[provider.config.label] = provider_raw
    if records:
        save(start, records, raw)
    return records, errors


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
                "point_name": group[0].point_name,
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


def daily_model_aggregates(records: list[ForecastRecord]) -> list[dict]:
    grouped: dict[tuple[str, date, str], list[ForecastRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.point_id, record.forecast_time_local.date(), record.model)].append(record)
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
                "point_name": group[0].point_name,
                "model": model,
                **values,
            }
        )
    return sorted(result, key=lambda item: (item["date"], item["point_id"], item["model"]))


def point_summaries(records: list[ForecastRecord]) -> list[dict]:
    aggregates = daily_model_aggregates(records)
    output = []
    for point in points():
        rows = [row for row in aggregates if row["point_id"] == point.id]
        if not rows:
            continue
        by_metric = {
            metric: numeric_consensus(
                {
                    model: next((row[metric] for row in rows if row["model"] == model), None)
                    for model in MODEL_LABELS
                }
            )
            for metric in DAILY_OPERATIONS
        }
        temp_mean = by_metric["temperature_mean"]
        temp_min = by_metric["temperature_min"]
        temp_max = by_metric["temperature_max"]
        if not temp_mean.get("consensus_available"):
            continue
        spread = max(
            by_metric[key].get("range", 0)
            for key in ("temperature_min", "temperature_max", "temperature_mean")
        )
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
        "value": getattr(record, field),
        "unit": unit,
        "date": record.forecast_time_local.date(),
        "forecast_time": record.forecast_time_local,
        "point_id": record.point_id,
        "point_name": record.point_name,
        "model": record.model,
    }


def daily_summary(records: list[ForecastRecord], day: date) -> dict:
    day_records = filter_dates(records, [day])
    point_data = point_summaries(day_records)
    if not point_data:
        return {"date": day, "available": False}
    model_rows = daily_model_aggregates(day_records)
    models: dict[str, dict[str, float] | None] = {}
    for model in MODEL_LABELS:
        rows = [row for row in model_rows if row["model"] == model]
        if not rows:
            models[model] = None
            continue
        models[model] = {
            "temperature_min": min(row["temperature_min"] for row in rows),
            "temperature_max": max(row["temperature_max"] for row in rows),
            "temperature_mean": statistics.fmean(row["temperature_mean"] for row in rows),
            "precipitation_sum": statistics.fmean(row["precipitation_sum"] for row in rows),
            "wind_speed_mean": statistics.fmean(row["wind_speed_mean"] for row in rows),
            "wind_gust_max": max(row["wind_gust_max"] for row in rows),
        }
    spreads = [item["spread"] for item in point_data]
    return {
        "date": day,
        "available": True,
        "mean_temperature": statistics.fmean(item["mean_temperature"] for item in point_data),
        "minimum_temperature": min(item["minimum"] for item in point_data),
        "maximum_temperature": max(item["maximum"] for item in point_data),
        "precipitation_sum": statistics.fmean(
            item["precipitation"].get("mean", 0) for item in point_data
        ),
        "mean_wind_speed": statistics.fmean(
            item["wind_speed"].get("mean", 0) for item in point_data
        ),
        "max_gust": max(item["max_gust"] or 0 for item in point_data),
        "mean_humidity": statistics.fmean(item["humidity"].get("mean", 0) for item in point_data),
        "mean_pressure": statistics.fmean(item["pressure"].get("mean", 0) for item in point_data),
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
    for point in points():
        values = {
            model: (
                sum(
                    row["precipitation_sum"] or 0
                    for row in aggregates
                    if row["model"] == model and row["point_id"] == point.id
                )
                if any(row["model"] == model and row["point_id"] == point.id for row in aggregates)
                else None
            )
            for model in MODEL_LABELS
        }
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
