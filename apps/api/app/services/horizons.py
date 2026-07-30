from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

Horizon = Literal["today", "3d", "7d"]
HORIZON_DAYS: dict[Horizon, int] = {"today": 1, "3d": 3, "7d": 7}
LOCAL_TZ = ZoneInfo("Asia/Yakutsk")


def current_local_date(now: datetime | None = None) -> date:
    moment = now or datetime.now(LOCAL_TZ)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=LOCAL_TZ)
    return moment.astimezone(LOCAL_TZ).date()


def horizon_dates(horizon: Horizon, today: date | None = None) -> list[date]:
    start = today or current_local_date()
    return [start + timedelta(days=offset) for offset in range(HORIZON_DAYS[horizon])]


def select_date(horizon: Horizon, requested: date | None, today: date | None = None) -> date:
    available = horizon_dates(horizon, today)
    selected = requested or available[0]
    if selected not in available:
        raise ValueError(
            f"Дата {selected.isoformat()} находится вне горизонта {horizon}: "
            f"{available[0].isoformat()}–{available[-1].isoformat()}"
        )
    return selected


def filter_dates(records: list, dates: list[date]) -> list:
    allowed = set(dates)
    return [record for record in records if record.forecast_time_local.date() in allowed]
