SEVERITY_PRIORITY = {"notable": 30, "attention": 20, "info": 10}
REASON_PRIORITY = {
    "PRECIP_DAILY_TOTAL": 8,
    "PRECIP_HOURLY_INTENSITY": 7,
    "PRECIP_LONG_DURATION": 6,
    "PRECIP_REGIONAL_MAXIMUM": 5,
    "PRECIP_MODEL_DISAGREEMENT": 4,
    "PRECIP_SINGLE_MODEL_ONLY": 3,
    "PRECIP_MULTI_DAY_ACCUMULATION": 7,
    "WIND_HIGH_GUST": 8,
    "WIND_HIGH_SPEED": 7,
    "WIND_LONG_DURATION": 6,
    "WIND_REGIONAL_MAXIMUM": 5,
    "WIND_GUST_DISAGREEMENT": 4,
    "WIND_DIRECTION_DISAGREEMENT": 4,
    "WIND_SINGLE_MODEL_ONLY": 3,
    "WIND_MULTI_DAY_EVENT": 7,
}


def rank(items: list[dict], limit: int = 5) -> list[dict]:
    unique: dict[tuple, dict] = {}
    for item in items:
        key = (item["reason_code"], item.get("point_id"), item.get("period_start"))
        unique[key] = item
    return sorted(
        unique.values(),
        key=lambda item: (
            SEVERITY_PRIORITY[item["severity"]],
            len(item.get("models", [])),
            REASON_PRIORITY.get(item["reason_code"], 0),
        ),
        reverse=True,
    )[:limit]
