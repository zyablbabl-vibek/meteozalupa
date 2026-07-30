from datetime import datetime

from app.config.settings import settings
from app.services.insights.ranking import rank


def wind_insights(
    point_data: list[dict], period_start: datetime, period_end: datetime
) -> list[dict]:
    items: list[dict] = []
    for point in point_data:
        analysis = point["wind_analysis"]
        gust = analysis["maximum_gust"]
        speed = analysis["maximum_speed"]
        gust_value = gust.get("maximum")
        speed_value = speed.get("mean")
        models = [
            model
            for model, value in gust.get("model_values", {}).items()
            if value is not None and value >= settings.wind_gust_attention_ms
        ]
        base = {
            "category": "wind",
            "period_start": analysis.get("strong_wind_start") or period_start,
            "period_end": analysis.get("strong_wind_end") or period_end,
            "point_id": point["point"]["id"],
            "point_name": point["point"]["name"],
            "models": models,
        }
        if speed_value is not None and speed_value >= settings.wind_speed_attention_ms:
            items.append(
                {
                    **base,
                    "severity": (
                        "notable" if speed_value >= settings.wind_speed_notable_ms else "attention"
                    ),
                    "reason_code": "WIND_HIGH_SPEED",
                    "title": "Усиленный ветер",
                    "description": (
                        f"В районе {point['point']['name']} модели прогнозируют "
                        f"максимальную среднюю скорость около {speed_value:.1f} м/с."
                    ),
                    "explanation": (
                        f"Значение выше продуктового порога "
                        f"{settings.wind_speed_attention_ms:g} м/с."
                    ),
                    "values": {
                        "speed_ms": speed_value,
                        "threshold_ms": settings.wind_speed_attention_ms,
                    },
                }
            )
        if gust_value is not None and gust_value >= settings.wind_gust_attention_ms:
            items.append(
                {
                    **base,
                    "severity": (
                        "notable" if gust_value >= settings.wind_gust_notable_ms else "attention"
                    ),
                    "reason_code": "WIND_HIGH_GUST",
                    "title": "Сильные порывы",
                    "description": (
                        f"Максимальные порывы в районе {point['point']['name']} — "
                        f"до {gust_value:.1f} м/с по модели {gust.get('maximum_source')}."
                    ),
                    "explanation": (
                        f"Порыв выше продуктового порога "
                        f"{settings.wind_gust_attention_ms:g} м/с. "
                        f"Подтверждают {len(models)} из 3 моделей."
                    ),
                    "values": {
                        "gust_ms": gust_value,
                        "threshold_ms": settings.wind_gust_attention_ms,
                    },
                }
            )
        duration = analysis.get("strong_wind_duration_hours") or 0
        if duration >= settings.wind_duration_attention_hours:
            items.append(
                {
                    **base,
                    "severity": "attention",
                    "reason_code": "WIND_LONG_DURATION",
                    "title": "Продолжительный период усиления",
                    "description": (
                        f"В районе {point['point']['name']} ветер выше выбранного "
                        f"порога может сохраняться около {duration} ч."
                    ),
                    "explanation": (
                        f"Период выше {settings.wind_speed_attention_ms:g} м/с длится "
                        f"не менее {settings.wind_duration_attention_hours} ч."
                    ),
                    "values": {"duration_hours": duration},
                }
            )
        gust_range = gust.get("range")
        if gust_range is not None and gust_range >= settings.wind_gust_range_attention_ms:
            items.append(
                {
                    **base,
                    "severity": "attention",
                    "reason_code": "WIND_GUST_DISAGREEMENT",
                    "title": "Прогнозы порывов расходятся",
                    "description": (
                        f"В районе {point['point']['name']} диапазон прогнозов "
                        f"порывов составляет {gust_range:.1f} м/с."
                    ),
                    "explanation": (
                        f"Разброс выше продуктового порога "
                        f"{settings.wind_gust_range_attention_ms:g} м/с."
                    ),
                    "values": {"range_ms": gust_range},
                }
            )
        speed_range = speed.get("range")
        if speed_range is not None and speed_range >= settings.wind_model_range_attention_ms:
            items.append(
                {
                    **base,
                    "severity": "attention",
                    "reason_code": "WIND_SPEED_DISAGREEMENT",
                    "title": "Прогнозы скорости ветра расходятся",
                    "description": (
                        f"В районе {point['point']['name']} диапазон прогнозов "
                        f"скорости составляет {speed_range:.1f} м/с."
                    ),
                    "explanation": (
                        f"Разброс выше продуктового порога "
                        f"{settings.wind_model_range_attention_ms:g} м/с."
                    ),
                    "values": {"range_ms": speed_range},
                }
            )
        direction_spread = analysis.get("maximum_direction_disagreement_deg")
        if (
            direction_spread is not None
            and direction_spread >= settings.wind_direction_disagreement_deg
        ):
            items.append(
                {
                    **base,
                    "severity": "attention",
                    "reason_code": "WIND_DIRECTION_DISAGREEMENT",
                    "title": "Направления моделей существенно расходятся",
                    "description": (
                        f"Максимальное угловое расхождение в районе "
                        f"{point['point']['name']} — {direction_spread:.0f}°."
                    ),
                    "explanation": (
                        f"Угловое расхождение выше продуктового порога "
                        f"{settings.wind_direction_disagreement_deg:g}°."
                    ),
                    "values": {"disagreement_deg": direction_spread},
                }
            )
        direction_change = analysis.get("maximum_direction_change_deg")
        if (
            direction_change is not None
            and direction_change >= settings.wind_direction_change_attention_deg
        ):
            items.append(
                {
                    **base,
                    "severity": "info",
                    "reason_code": "WIND_DIRECTION_CHANGE",
                    "title": "Возможна заметная смена направления",
                    "description": (
                        f"В районе {point['point']['name']} модели указывают на "
                        f"смену направления примерно на {direction_change:.0f}°."
                    ),
                    "explanation": (
                        f"Изменение выше продуктового порога "
                        f"{settings.wind_direction_change_attention_deg:g}°."
                    ),
                    "values": {"direction_change_deg": direction_change},
                }
            )
        if len(models) == 1:
            items.append(
                {
                    **base,
                    "severity": "info",
                    "reason_code": "WIND_SINGLE_MODEL_ONLY",
                    "title": "Сильный порыв показывает одна модель",
                    "description": (
                        f"Только {models[0]} показывает порыв выше выбранного порога "
                        f"в районе {point['point']['name']}."
                    ),
                    "explanation": "Порог превышает только 1 из 3 моделей.",
                    "values": {"confirming_models": 1},
                }
            )
    if point_data:
        strongest = max(
            point_data,
            key=lambda point: point["wind_analysis"]["maximum_gust"].get("maximum") or 0,
        )
        gust = strongest["wind_analysis"]["maximum_gust"]
        items.append(
            {
                "category": "wind",
                "severity": "info",
                "reason_code": "WIND_REGIONAL_MAXIMUM",
                "title": "Максимальные порывы среди контрольных точек",
                "description": (
                    f"Самые сильные порывы ожидаются в районе "
                    f"{strongest['point']['name']} — до {gust.get('maximum'):.1f} м/с."
                ),
                "explanation": ("Точка имеет максимальный модельный порыв в выбранной выборке."),
                "period_start": period_start,
                "period_end": period_end,
                "point_id": strongest["point"]["id"],
                "point_name": strongest["point"]["name"],
                "models": list(gust.get("model_values", {})),
                "values": {"gust_ms": gust.get("maximum")},
            }
        )
    return rank(items)
