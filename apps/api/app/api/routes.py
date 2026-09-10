from datetime import date
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.config.models import METRICS, MODELS
from app.config.settings import settings
from app.regions.registry import (
    DEFAULT_REGION_ID,
    RegionNotFoundError,
    get_region,
    list_regions,
    load_points,
)
from app.regions.schemas import RegionMetadata
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
from app.services.insights import build_insights

router = APIRouter(prefix="/api")
HorizonQuery = Annotated[str, Query(description="today, 3d или 7d")]
DateQuery = Annotated[date | None, Query()]
RegionQuery = Annotated[
    str, Query(description="Стабильный id региона поддерживаемых федеральных округов")
]


def resolve_region(region_id: str) -> RegionMetadata:
    try:
        return get_region(region_id)
    except RegionNotFoundError as exc:
        raise HTTPException(
            404,
            f"{exc}. Выберите один из доступных регионов через GET /api/regions",
        ) from exc


def context(
    region_id: str, horizon_value: str, requested: date | None
) -> tuple[RegionMetadata, Horizon, list[date], date]:
    region = resolve_region(region_id)
    if horizon_value not in {"today", "3d", "7d"}:
        raise HTTPException(422, "Неизвестный horizon. Допустимые значения: today, 3d, 7d")
    horizon: Horizon = horizon_value  # type: ignore[assignment]
    dates = horizon_dates(horizon, timezone=region.primary_timezone)
    try:
        selected = select_date(horizon, requested, timezone=region.primary_timezone)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return region, horizon, dates, selected


def validate_metric(metric: str) -> None:
    if metric not in METRICS:
        raise HTTPException(422, f"Неизвестный показатель: {metric}")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "data_mode": settings.data_mode}


@router.get("/regions")
async def regions() -> dict:
    return {"regions": list_regions()}


@router.get("/regions/{region_id}")
async def region_details(region_id: str) -> RegionMetadata:
    return resolve_region(region_id)


@router.get("/regions/{region_id}/points")
async def region_points(region_id: str) -> dict:
    region = resolve_region(region_id)
    return {"region": region, "points": load_points(region_id)}


@router.get("/regions/{region_id}/geojson")
async def region_geojson(region_id: str) -> FileResponse:
    region = resolve_region(region_id)
    path = settings.regions_geojson_dir / f"{region.id}.geojson"
    if not path.is_file():
        raise HTTPException(404, "Проверенная GeoJSON-граница для региона не подключена")
    return FileResponse(path, media_type="application/geo+json")


@router.get("/points")
async def list_points(region_id: RegionQuery = DEFAULT_REGION_ID) -> dict:
    region = resolve_region(region_id)
    return {"region": region, "points": points(region_id)}


@router.get("/forecast")
async def forecast(
    region_id: RegionQuery = DEFAULT_REGION_ID,
    horizon: HorizonQuery = "today",
    date: DateQuery = None,
    metric: str = "temperature_2m",
) -> dict:
    region, selected_horizon, dates, selected_date = context(region_id, horizon, date)
    validate_metric(metric)
    all_records, warnings, cache = await get_records(region_id)
    selected_records = filter_dates(all_records, [selected_date])
    return {
        "region": region,
        "region_id": region.id,
        "region_name": region.name,
        "horizon": selected_horizon,
        "period_start": dates[0],
        "period_end": dates[-1],
        "selected_date": selected_date,
        "available_dates": dates,
        "metric": metric,
        "data_mode": settings.data_mode,
        "models": [model.label for model in MODELS.values()],
        "model_availability": {
            model.label: any(record.model == model.label for record in all_records)
            for model in MODELS.values()
        },
        "warnings": warnings,
        "cache": cache,
        "last_updated": max((record.fetched_at for record in all_records), default=None),
        "points": point_summaries(selected_records),
        "hourly": hourly(selected_records, metric),
        "daily_summaries": [daily_summary(all_records, day) for day in dates],
        "period_summary": period_summary(all_records, dates),
    }


@router.get("/forecast/{point_id}")
async def point_forecast(
    point_id: str,
    region_id: RegionQuery = DEFAULT_REGION_ID,
    horizon: HorizonQuery = "today",
    date: DateQuery = None,
) -> dict:
    region, selected_horizon, dates, selected_date = context(region_id, horizon, date)
    point = next((item for item in points(region_id) if item.id == point_id), None)
    if point is None:
        raise HTTPException(404, "Контрольная точка не принадлежит выбранному региону")
    all_records, warnings, _ = await get_records(region_id)
    period_records = [
        record for record in filter_dates(all_records, dates) if record.point_id == point_id
    ]
    selected_records = filter_dates(period_records, [selected_date])
    daily = daily_model_aggregates(period_records)
    return {
        "region": region,
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
    region_id: RegionQuery = DEFAULT_REGION_ID,
    horizon: HorizonQuery = "today",
    date: DateQuery = None,
) -> dict:
    region, selected_horizon, dates, selected_date = context(region_id, horizon, date)
    records, warnings, _ = await get_records(region_id)
    selected_records = filter_dates(records, [selected_date])
    selected_points = point_summaries(selected_records)
    if not selected_points:
        raise HTTPException(503, "Недостаточно модельных данных для сводки")
    return {
        "region": region,
        "region_id": region.id,
        "region_name": region.name,
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


@router.get("/insights")
async def insights(
    region_id: RegionQuery = DEFAULT_REGION_ID,
    horizon: HorizonQuery = "today",
    date: DateQuery = None,
    category: str = "all",
) -> dict:
    region, selected_horizon, dates, selected_date = context(region_id, horizon, date)
    if category not in {"all", "precipitation", "wind"}:
        raise HTTPException(
            422, "Неизвестная category. Допустимые значения: all, precipitation, wind"
        )
    records, _, _ = await get_records(region_id)
    result = build_insights(records, dates, selected_date, region.primary_timezone)
    empty = {"items": [], "total": 0}
    return {
        "region": region,
        "region_id": region.id,
        "region_name": region.name,
        "horizon": selected_horizon,
        "period_start": dates[0],
        "period_end": dates[-1],
        "selected_date": selected_date,
        "disclaimer": result["disclaimer"],
        "precipitation": (
            result["precipitation"] if category in {"all", "precipitation"} else empty
        ),
        "wind": result["wind"] if category in {"all", "wind"} else empty,
    }


@router.post("/refresh")
async def refresh(region_id: RegionQuery = DEFAULT_REGION_ID) -> dict:
    region = resolve_region(region_id)
    if refresh_lock.locked():
        raise HTTPException(409, "Обновление уже выполняется")
    async with refresh_lock:
        records, warnings, cache = await get_records(region_id, force=True)
    dates = sorted({record.local_date for record in records})
    return {
        "status": "updated",
        "region": region,
        "records": len(records),
        "period_start": dates[0] if dates else None,
        "period_end": dates[-1] if dates else None,
        "warnings": warnings,
        "cache": cache,
    }


@router.get("/request-info")
async def request_info(request: Request) -> dict:
    return {"request_id": getattr(request.state, "request_id", str(uuid4()))}
