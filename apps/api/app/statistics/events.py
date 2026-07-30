def event_periods(timeline: list[tuple[object, float | None]], threshold: float) -> list[dict]:
    periods: list[dict] = []
    current: list[tuple[object, float]] = []
    for timestamp, value in timeline:
        if value is not None and value >= threshold:
            current.append((timestamp, value))
        elif current:
            periods.append(_period(current))
            current = []
    if current:
        periods.append(_period(current))
    return periods


def _period(values: list[tuple[object, float]]) -> dict:
    peak_time, peak = max(values, key=lambda item: item[1])
    return {
        "start": values[0][0],
        "end": values[-1][0],
        "duration_hours": len(values),
        "peak": peak,
        "peak_time": peak_time,
    }


def angular_distance(first: float, second: float) -> float:
    return abs((first - second + 180) % 360 - 180)


def maximum_angular_disagreement(values: dict[str, float | None]) -> dict:
    available = [(model, value) for model, value in values.items() if value is not None]
    if len(available) < 2:
        return {"value": None, "models": []}
    pairs = [
        (angular_distance(a_value, b_value), [a_model, b_model])
        for index, (a_model, a_value) in enumerate(available)
        for b_model, b_value in available[index + 1 :]
    ]
    value, models = max(pairs, key=lambda item: item[0])
    return {"value": value, "models": models}


DIRECTION_LABELS = (
    "С",
    "ССВ",
    "СВ",
    "ВСВ",
    "В",
    "ВЮВ",
    "ЮВ",
    "ЮЮВ",
    "Ю",
    "ЮЮЗ",
    "ЮЗ",
    "ЗЮЗ",
    "З",
    "ЗСЗ",
    "СЗ",
    "ССЗ",
)


def direction_label(value: float | None) -> str | None:
    if value is None:
        return None
    return DIRECTION_LABELS[round(value / 22.5) % 16]


def relative_spread(
    mean: float | None, spread: float | None, epsilon: float = 1e-6
) -> float | None:
    if mean is None or spread is None or mean < 0.5:
        return None
    return spread / max(mean, epsilon) * 100
