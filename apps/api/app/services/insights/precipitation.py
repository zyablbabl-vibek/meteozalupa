from datetime import datetime

from app.config.settings import settings
from app.services.insights.ranking import rank


def _fmt(value: float | None) -> str:
    return "нет данных" if value is None else f"{value:.1f}"


def precipitation_insights(
    point_data: list[dict], period_start: datetime, period_end: datetime
) -> list[dict]:
    items: list[dict] = []
    for point in point_data:
        analysis = point["precipitation_analysis"]
        stats = analysis["daily_total"]
        mean = stats.get("mean")
        maximum = stats.get("maximum")
        minimum = stats.get("minimum")
        models = [
            model
            for model, value in stats.get("model_values", {}).items()
            if value is not None and value >= settings.precipitation_event_threshold_mm
        ]
        base = {
            "category": "precipitation",
            "period_start": analysis.get("event_start") or period_start,
            "period_end": analysis.get("event_end") or period_end,
            "point_id": point["point"]["id"],
            "point_name": point["point"]["name"],
            "models": models,
        }
        if mean is not None and mean >= settings.precip_daily_attention_mm:
            notable = mean >= settings.precip_daily_notable_mm
            items.append(
                {
                    **base,
                    "severity": "notable" if notable else "attention",
                    "reason_code": "PRECIP_DAILY_TOTAL",
                    "title": "Значительная суточная сумма осадков",
                    "description": (
                        f"В районе {point['point']['name']} модели в среднем прогнозируют "
                        f"{mean:.1f} мм осадков. Диапазон — от {_fmt(minimum)} мм "
                        f"до {_fmt(maximum)} мм."
                    ),
                    "explanation": (
                        f"Средняя сумма {mean:.1f} мм выше продуктового порога "
                        f"{settings.precip_daily_attention_mm:g} мм. "
                        f"Подтверждают {len(models)} из 3 моделей."
                    ),
                    "values": {
                        "mean_mm": mean,
                        "minimum_mm": minimum,
                        "maximum_mm": maximum,
                        "threshold_mm": settings.precip_daily_attention_mm,
                    },
                }
            )
        peak = analysis.get("peak_value")
        if peak is not None and peak >= settings.precip_hourly_attention_mm:
            items.append(
                {
                    **base,
                    "severity": (
                        "notable" if peak >= settings.precip_hourly_notable_mm else "attention"
                    ),
                    "reason_code": "PRECIP_HOURLY_INTENSITY",
                    "title": "Интенсивный период осадков",
                    "description": (
                        f"Максимальная интенсивность в районе {point['point']['name']} — "
                        f"{peak:.1f} мм/ч по модели {analysis['peak_model']}."
                    ),
                    "explanation": (
                        f"Пиковая интенсивность выше продуктового порога "
                        f"{settings.precip_hourly_attention_mm:g} мм/ч."
                    ),
                    "values": {
                        "peak_mm_h": peak,
                        "threshold_mm_h": settings.precip_hourly_attention_mm,
                    },
                }
            )
        duration = analysis.get("duration_hours") or 0
        if duration >= settings.precip_duration_attention_hours:
            items.append(
                {
                    **base,
                    "severity": "attention",
                    "reason_code": "PRECIP_LONG_DURATION",
                    "title": "Продолжительный период осадков",
                    "description": (
                        f"В районе {point['point']['name']} возможен период осадков "
                        f"продолжительностью около {duration} ч."
                    ),
                    "explanation": (
                        f"Последовательный период выше аналитического порога "
                        f"{settings.precipitation_event_threshold_mm:g} мм/ч длится "
                        f"не менее {settings.precip_duration_attention_hours} ч."
                    ),
                    "values": {
                        "duration_hours": duration,
                        "threshold_hours": settings.precip_duration_attention_hours,
                    },
                }
            )
        spread = stats.get("range")
        if spread is not None and spread >= settings.precip_model_range_attention_mm:
            items.append(
                {
                    **base,
                    "severity": "attention",
                    "reason_code": "PRECIP_MODEL_DISAGREEMENT",
                    "title": "Прогнозы осадков существенно расходятся",
                    "description": (
                        f"В районе {point['point']['name']} диапазон модельных "
                        f"прогнозов составляет {spread:.1f} мм."
                    ),
                    "explanation": (
                        f"Разброс выше продуктового порога "
                        f"{settings.precip_model_range_attention_mm:g} мм."
                    ),
                    "values": {
                        "range_mm": spread,
                        "threshold_mm": settings.precip_model_range_attention_mm,
                    },
                }
            )
        start_difference = analysis.get("start_time_disagreement_hours")
        if (
            start_difference is not None
            and start_difference >= settings.precip_start_time_disagreement_hours
        ):
            items.append(
                {
                    **base,
                    "severity": "info",
                    "reason_code": "PRECIP_START_TIME_DISAGREEMENT",
                    "title": "Модели расходятся по времени начала",
                    "description": (
                        f"В районе {point['point']['name']} прогнозируемое время "
                        f"начала осадков различается примерно на {start_difference:.0f} ч."
                    ),
                    "explanation": (
                        f"Разница выше продуктового порога "
                        f"{settings.precip_start_time_disagreement_hours} ч."
                    ),
                    "values": {"start_difference_hours": start_difference},
                }
            )
        if len(models) == 1:
            items.append(
                {
                    **base,
                    "severity": "info",
                    "reason_code": "PRECIP_SINGLE_MODEL_ONLY",
                    "title": "Осадки показывает одна модель",
                    "description": (
                        f"Заметные осадки в районе {point['point']['name']} показывает "
                        f"только {models[0]}. Рекомендуется проверить обновления прогноза."
                    ),
                    "explanation": (
                        f"Только 1 из 3 моделей превышает продуктовый порог "
                        f"{settings.precipitation_event_threshold_mm:g} мм."
                    ),
                    "values": {"confirming_models": 1},
                }
            )
    if point_data:
        wettest = max(
            point_data,
            key=lambda point: point["precipitation"].get("mean") or 0,
        )
        mean = wettest["precipitation"].get("mean")
        items.append(
            {
                "category": "precipitation",
                "severity": "info",
                "reason_code": "PRECIP_REGIONAL_MAXIMUM",
                "title": "Максимум осадков среди контрольных точек",
                "description": (
                    f"Наибольшая средняя сумма ожидается в районе "
                    f"{wettest['point']['name']} — {_fmt(mean)} мм."
                ),
                "explanation": (
                    "Точка имеет максимальную среднюю модельную сумму в выбранной выборке."
                ),
                "period_start": period_start,
                "period_end": period_end,
                "point_id": wettest["point"]["id"],
                "point_name": wettest["point"]["name"],
                "models": list(wettest["precipitation"].get("model_values", {})),
                "values": {"mean_mm": mean},
            }
        )
    return rank(items)
