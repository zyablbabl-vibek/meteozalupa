import math
import statistics
from collections.abc import Iterable

from app.config.models import AGREEMENT_THRESHOLDS


def numeric_consensus(values: dict[str, float | None]) -> dict:
    available = [(model, value) for model, value in values.items() if value is not None]
    if len(available) < 2:
        return {"count": len(available), "complete": False, "consensus_available": False}
    raw = [value for _, value in available]
    minimum = min(raw)
    maximum = max(raw)
    return {
        "count": len(raw),
        "complete": len(raw) == 3,
        "consensus_available": True,
        "mean": statistics.fmean(raw),
        "median": statistics.median(raw),
        "minimum": minimum,
        "minimum_source": next(model for model, value in available if value == minimum),
        "maximum": maximum,
        "maximum_source": next(model for model, value in available if value == maximum),
        "range": maximum - minimum,
        "standard_deviation": statistics.pstdev(raw),
    }


def circular_mean(values: Iterable[float]) -> float | None:
    values = list(values)
    if not values:
        return None
    x = statistics.fmean(math.cos(math.radians(v)) for v in values)
    y = statistics.fmean(math.sin(math.radians(v)) for v in values)
    if math.hypot(x, y) < 1e-9:
        return None
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def agreement(metric: str, spread: float | None) -> str:
    if spread is None:
        return "недостаточно данных"
    high, medium = AGREEMENT_THRESHOLDS[metric]
    return "высокое" if spread <= high else "среднее" if spread <= medium else "низкое"


def daily_precipitation(records: list, models: Iterable[str]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for model in models:
        values = [r.precipitation_mm for r in records if r.model == model]
        result[model] = (
            sum(v for v in values if v is not None) if any(v is not None for v in values) else None
        )
    return result
