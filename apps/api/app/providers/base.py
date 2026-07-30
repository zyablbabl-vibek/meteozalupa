import asyncio
from abc import ABC
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import httpx

from app.config.models import METRICS, ModelConfig
from app.config.settings import settings
from app.schemas.forecast import ForecastRecord, Point


class ProviderError(RuntimeError):
    pass


class OpenMeteoProvider(ABC):
    config: ModelConfig

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.chunk_size = settings.open_meteo_batch_size

    async def fetch(
        self, points: list[Point], start_day: date, end_day: date | None = None
    ) -> tuple[list[ForecastRecord], list[dict]]:
        records: list[ForecastRecord] = []
        raw: list[dict] = []
        for offset in range(0, len(points), self.chunk_size):
            chunk = points[offset : offset + self.chunk_size]
            payload = await self._request(chunk, start_day, end_day or start_day)
            responses = payload if isinstance(payload, list) else [payload]
            if len(responses) != len(chunk):
                raise ProviderError(f"{self.config.label}: unexpected batch response size")
            fetched_at = datetime.now(UTC)
            for point, response in zip(chunk, responses, strict=True):
                raw.append(response)
                records.extend(self.normalize(response, point, fetched_at))
        return records, raw

    async def _request(
        self, points: list[Point], start_day: date, end_day: date
    ) -> dict | list[dict]:
        params = {
            "latitude": ",".join(str(p.latitude) for p in points),
            "longitude": ",".join(str(p.longitude) for p in points),
            "hourly": ",".join(METRICS),
            "models": self.config.identifier,
            "start_date": start_day.isoformat(),
            "end_date": end_day.isoformat(),
            "timezone": "GMT",
            "temperature_unit": "celsius",
            "wind_speed_unit": "ms",
            "precipitation_unit": "mm",
        }
        for attempt in range(3):
            try:
                response = await self.client.get(self.config.endpoint, params=params, timeout=20)
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                temporary = (
                    not isinstance(exc, httpx.HTTPStatusError) or exc.response.status_code >= 500
                )
                if not temporary or attempt == 2:
                    raise ProviderError(f"{self.config.label}: {exc}") from exc
                await asyncio.sleep(0.25 * 2**attempt)
        raise AssertionError("unreachable")

    def normalize(self, response: dict, point: Point, fetched_at: datetime) -> list[ForecastRecord]:
        hourly = response.get("hourly", {})
        times = hourly.get("time", [])
        records: list[ForecastRecord] = []
        for index, time_text in enumerate(times):
            utc_time = datetime.fromisoformat(time_text).replace(tzinfo=UTC)

            def value(metric: str, position: int = index) -> float | None:
                series = hourly.get(metric, [])
                return series[position] if position < len(series) else None

            records.append(
                ForecastRecord(
                    region_id=point.region_id,
                    model=self.config.label,
                    point_id=point.id,
                    point_name=point.name,
                    point_timezone=point.timezone,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    forecast_time_utc=utc_time,
                    forecast_time_local=utc_time.astimezone(ZoneInfo(point.timezone)),
                    local_date=utc_time.astimezone(ZoneInfo(point.timezone)).date(),
                    fetched_at=fetched_at,
                    temperature_2m_c=value("temperature_2m"),
                    relative_humidity_2m_pct=value("relative_humidity_2m"),
                    pressure_msl_hpa=value("pressure_msl"),
                    precipitation_mm=value("precipitation"),
                    cloud_cover_pct=value("cloud_cover"),
                    wind_speed_10m_ms=value("wind_speed_10m"),
                    wind_direction_10m_deg=value("wind_direction_10m"),
                    wind_gusts_10m_ms=value("wind_gusts_10m"),
                )
            )
        return records
