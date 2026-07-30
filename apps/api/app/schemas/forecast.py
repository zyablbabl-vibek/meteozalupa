from datetime import date, datetime

from pydantic import BaseModel

from app.regions.schemas import ForecastPoint

# Compatibility alias for provider and statistics code. The universal domain
# name is ForecastPoint.
Point = ForecastPoint


class ForecastRecord(BaseModel):
    region_id: str
    provider: str = "Open-Meteo"
    model: str
    point_id: str
    point_name: str
    point_timezone: str
    latitude: float
    longitude: float
    forecast_time_utc: datetime
    forecast_time_local: datetime
    local_date: date
    fetched_at: datetime
    model_run: datetime | None = None
    temperature_2m_c: float | None = None
    relative_humidity_2m_pct: float | None = None
    pressure_msl_hpa: float | None = None
    precipitation_mm: float | None = None
    cloud_cover_pct: float | None = None
    wind_speed_10m_ms: float | None = None
    wind_direction_10m_deg: float | None = None
    wind_gusts_10m_ms: float | None = None


FIELD_BY_METRIC = {
    "temperature_2m": "temperature_2m_c",
    "relative_humidity_2m": "relative_humidity_2m_pct",
    "pressure_msl": "pressure_msl_hpa",
    "precipitation": "precipitation_mm",
    "cloud_cover": "cloud_cover_pct",
    "wind_speed_10m": "wind_speed_10m_ms",
    "wind_direction_10m": "wind_direction_10m_deg",
    "wind_gusts_10m": "wind_gusts_10m_ms",
}
