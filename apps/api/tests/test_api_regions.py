from fastapi.testclient import TestClient

from app.main import app
from app.regions.registry import get_region

client = TestClient(app)


def test_region_endpoints_return_registry_and_points():
    response = client.get("/api/regions")
    assert response.status_code == 200
    regions = response.json()["regions"]
    assert len(regions) == 21
    assert [item["name"] for item in regions] == sorted(item["name"] for item in regions)

    detail = client.get("/api/regions/sakha-yakutia")
    assert detail.status_code == 200
    assert detail.json()["has_multiple_timezones"] is True

    points = client.get("/api/regions/primorsky-krai/points")
    assert points.status_code == 200
    assert all(item["region_id"] == "primorsky-krai" for item in points.json()["points"])

    siberian = client.get("/api/regions/krasnoyarsk-krai")
    assert siberian.status_code == 200
    assert siberian.json()["federal_district"] == "Сибирский федеральный округ"


def test_unknown_region_and_cross_region_point_are_rejected():
    assert client.get("/api/regions/not-a-region").status_code == 404
    assert (
        client.get(
            "/api/forecast/blagoveshchensk",
            params={"region_id": "primorsky-krai"},
        ).status_code
        == 404
    )


def test_forecast_summary_and_insights_are_scoped_to_region():
    params = {"region_id": "jewish-autonomous-oblast", "horizon": "today"}
    forecast = client.get("/api/forecast", params=params)
    assert forecast.status_code == 200
    payload = forecast.json()
    assert payload["region_id"] == "jewish-autonomous-oblast"
    assert all(
        point["point"]["region_id"] == "jewish-autonomous-oblast" for point in payload["points"]
    )

    summary = client.get("/api/summary", params=params)
    assert summary.status_code == 200
    assert summary.json()["region_id"] == "jewish-autonomous-oblast"

    insights = client.get("/api/insights", params=params)
    assert insights.status_code == 200
    assert insights.json()["region_id"] == "jewish-autonomous-oblast"


def test_default_region_remains_amur_for_compatible_urls():
    response = client.get("/api/forecast", params={"horizon": "today"})
    assert response.status_code == 200
    assert response.json()["region"]["id"] == get_region("amur-oblast").id
