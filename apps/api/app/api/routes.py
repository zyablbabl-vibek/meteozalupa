from datetime import date
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request

from app.config.models import METRICS, MODELS
from app.config.settings import settings
from app.services.forecast import (
    daily_model_aggregates,
    daily_summary,
    get_records,
    hourly,
    period_summary,
    point_summaries,
    points,
    refresh_lock,
)
from app.services.horizons import Horizon, filter_dates, horizon_dates, select_date

router = APIRouter(prefix="/api")
HorizonQuery = Annotated[str, Query(description="today, 3d или 7d")]
DateQuery = Annotated[date | None, Query()]


def context(horizon_value: str, requested: date | None) -> tuple[Horizon, list[date], date]:
    if horizon_value not in {"today", "3d", "7d"}:
        raise HTTPException(422, "Неизвестный horizon. Допустимые значения: today, 3d, 7d")
    horizon: Horizon = horizon_value  # type: ignore[assignment]
    dates = horizon_dates(horizon)
    try:
        selected = select_date(horizon, requested)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return horizon, dates, selected


def validate_metric(metric: str) -> None:
    if metric not in METRICS:
        raise HTTPException(422, f"Неизвестный показатель: {metric}")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "data_mode": settings.data_mode}


@router.get("/points")
async def list_points() -> dict:
    return {"region": "Амурская область", "timezone": "Asia/Yakutsk", "points": points()}


@router.get("/forecast")
async def forecast(
    horizon: HorizonQuery = "today",
    date: DateQuery = None,
    metric: str = "temperature_2m",
) -> dict:
    selected_horizon, dates, selected_date = context(horizon, date)
    validate_metric(metric)
    all_records, warnings = await get_records()
    selected_records = filter_dates(all_records, [selected_date])
    return {
        "horizon": selected_horizon,
        "period_start": dates[0],
        "period_end": dates[-1],
        "selected_date": selected_date,
        "available_dates": dates,
        "metric": metric,
        "data_mode": settings.data_mode,
        "models": [model.label for model in MODELS.values()],
        "warnings": warnings,
        "last_updated": max((record.fetched_at for record in all_records), default=None),
        "points": point_summaries(selected_records),
        "hourly": hourly(selected_records, metric),
        "daily_summaries": [daily_summary(all_records, day) for day in dates],
        "period_summary": period_summary(all_records, dates),
    }


@router.get("/forecast/{point_id}")
async def point_forecast(
    point_id: str,
    horizon: HorizonQuery = "today",
    date: DateQuery = None,
) -> dict:
    selected_horizon, dates, selected_date = context(horizon, date)
    point = next((item for item in points() if item.id == point_id), None)
    if point is None:
        raise HTTPException(404, "Контрольная точка не найдена")
    all_records, warnings = await get_records()
    period_records = [
        record for record in filter_dates(all_records, dates) if record.point_id == point_id
    ]
    selected_records = filter_dates(period_records, [selected_date])
    daily = daily_model_aggregates(period_records)
    return {
        "point": point,
        "horizon": selected_horizon,
        "period_start": dates[0],
        "period_end": dates[-1],
        "selected_date": selected_date,
        "available_dates": dates,
        "warnings": warnings,
        "series": {metric: hourly(selected_records, metric) for metric in METRICS},
        "selected_day_aggregates": [row for row in daily if row["date"] == selected_date],
        "daily_aggregates": daily,
        "period_summary": period_summary(period_records, dates),
    }


@router.get("/summary")
async def summary(
    horizon: HorizonQuery = "today",
    date: DateQuery = None,
) -> dict:
    selected_horizon, dates, selected_date = context(horizon, date)
    records, warnings = await get_records()
    selected_records = filter_dates(records, [selected_date])
    selected_points = point_summaries(selected_records)
    if not selected_points:
        raise HTTPException(503, "Недостаточно модельных данных для сводки")
    return {
        "selected_horizon": selected_horizon,
        "period_start": dates[0],
        "period_end": dates[-1],
        "selected_date": selected_date,
        "daily_summaries": [daily_summary(records, day) for day in dates],
        "selected_day_summary": daily_summary(records, selected_date),
        "period_summary": period_summary(records, dates),
        "model_availability": {
            model.label: any(record.model == model.label for record in records)
            for model in MODELS.values()
        },
        "warnings": warnings,
    }


@router.post("/refresh")
async def refresh() -> dict:
    if refresh_lock.locked():
        raise HTTPException(409, "Обновление уже выполняется")
    async with refresh_lock:
        records, warnings = await get_records(force=True)
    dates = sorted({record.forecast_time_local.date() for record in records})
    return {
        "status": "updated",
        "records": len(records),
        "period_start": dates[0] if dates else None,
        "period_end": dates[-1] if dates else None,
        "warnings": warnings,
    }


@router.get("/request-info")
async def request_info(request: Request) -> dict:
    return {"request_id": getattr(request.state, "request_id", str(uuid4()))}
