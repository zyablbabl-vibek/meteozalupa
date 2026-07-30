from datetime import UTC, date, datetime

import httpx
import pytest

from app.providers.ecmwf import EcmwfProvider
from app.providers.gfs import GfsProvider
from app.providers.icon import IconProvider
from app.schemas.forecast import Point


def response():
    return {
        "hourly": {
            "time": ["2026-08-01T00:00"],
            "temperature_2m": [12.5],
            "relative_humidity_2m": [70],
            "pressure_msl": [1005],
            "precipitation": [0.2],
            "cloud_cover": [60],
            "wind_speed_10m": [3.1],
            "wind_direction_10m": [350],
            "wind_gusts_10m": [6.2],
        }
    }


def test_all_providers_normalize_to_same_schema():
    point = Point(id="x", name="X", latitude=50, longitude=127)
    for provider_type in (EcmwfProvider, GfsProvider, IconProvider):
        provider = provider_type(httpx.AsyncClient())
        records = provider.normalize(response(), point, datetime.now(UTC))
        assert records[0].temperature_2m_c == 12.5
        assert records[0].model == provider.config.label


@pytest.mark.asyncio
async def test_provider_fetch_uses_mocked_http_batch():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["models"] == "gfs_global"
        assert "," in request.url.params["latitude"]
        return httpx.Response(200, json=[response(), response()])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = GfsProvider(client)
        records, raw = await provider.fetch(
            [
                Point(id="a", name="A", latitude=50, longitude=127),
                Point(id="b", name="B", latitude=51, longitude=128),
            ],
            date(2026, 8, 1),
        )
    assert len(records) == 2
    assert len(raw) == 2
