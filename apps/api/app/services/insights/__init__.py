from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.services.forecast import period_summary, point_summaries
from app.services.horizons import filter_dates
from app.services.insights.precipitation import precipitation_insights
from app.services.insights.ranking import rank
from app.services.insights.wind import wind_insights

DISCLAIMER = (
    "Автоматический анализ прогнозных моделей. "
    "Не является официальным метеорологическим предупреждением."
)


def build_insights(
    records: list, dates: list, selected_date, primary_timezone: str = "Asia/Yakutsk"
) -> dict:
    timezone = ZoneInfo(primary_timezone)
    start = datetime.combine(dates[0], time.min, timezone)
    end = datetime.combine(dates[-1], time(23, 59), timezone)
    selected_points = point_summaries(filter_dates(records, [selected_date]))
    precipitation = precipitation_insights(selected_points, start, end)
    wind = wind_insights(selected_points, start, end)
    if len(dates) > 1:
        summary = period_summary(records, dates)
        wettest = summary.get("precipitation")
        if wettest:
            stats = wettest["statistics"]
            precipitation.append(
                {
                    "category": "precipitation",
                    "severity": "info",
                    "reason_code": "PRECIP_MULTI_DAY_ACCUMULATION",
                    "title": "Накопленные осадки за выбранный период",
                    "description": (
                        f"Максимальная средняя накопленная сумма ожидается в районе "
                        f"{wettest['point']['name']} — {stats['mean']:.1f} мм."
                    ),
                    "explanation": (
                        "Почасовые значения сначала суммированы отдельно по каждой "
                        "модели и каждому дню, затем накоплены за период."
                    ),
                    "period_start": start,
                    "period_end": end,
                    "point_id": wettest["point"]["id"],
                    "point_name": wettest["point"]["name"],
                    "models": list(wettest["models"]),
                    "values": {"period_mean_mm": stats["mean"]},
                }
            )
        gust = summary["wind"]["maximum_gust"]
        if gust:
            wind.append(
                {
                    "category": "wind",
                    "severity": "info",
                    "reason_code": "WIND_MULTI_DAY_EVENT",
                    "title": "Максимальный порыв за выбранный период",
                    "description": (
                        f"Максимальный порыв ожидается в районе {gust['point_name']} — "
                        f"{gust['value']:.1f} м/с по модели {gust['model']}."
                    ),
                    "explanation": (
                        "Выбран максимальный исходный прогноз среди моделей, "
                        "контрольных точек и часов периода."
                    ),
                    "period_start": start,
                    "period_end": end,
                    "point_id": gust["point_id"],
                    "point_name": gust["point_name"],
                    "models": [gust["model"]],
                    "values": {"gust_ms": gust["value"]},
                }
            )
    precipitation = rank(precipitation)
    wind = rank(wind)
    return {
        "disclaimer": DISCLAIMER,
        "precipitation": {"items": precipitation, "total": len(precipitation)},
        "wind": {"items": wind, "total": len(wind)},
    }


__all__ = ["build_insights"]
