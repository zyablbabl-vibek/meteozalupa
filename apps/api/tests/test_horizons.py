from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.services.horizons import current_local_date, filter_dates, horizon_dates, select_date


def test_current_date_uses_yakutsk_timezone():
    assert current_local_date(datetime(2026, 7, 30, 16, 30, tzinfo=UTC)) == date(2026, 7, 31)


@pytest.mark.parametrize(
    ("horizon", "expected"),
    [("today", 1), ("3d", 3), ("7d", 7)],
)
def test_horizon_has_exact_calendar_days(horizon, expected):
    dates = horizon_dates(horizon, date(2026, 7, 30))
    assert len(dates) == expected
    assert dates[-1] == date(2026, 7, 30) + timedelta(days=expected - 1)


def test_horizon_crosses_month_boundary():
    assert horizon_dates("3d", date(2026, 7, 31)) == [
        date(2026, 7, 31),
        date(2026, 8, 1),
        date(2026, 8, 2),
    ]


def test_horizon_crosses_year_boundary():
    assert horizon_dates("7d", date(2026, 12, 29))[-1] == date(2027, 1, 4)


def test_date_outside_horizon_is_rejected():
    with pytest.raises(ValueError, match="вне горизонта"):
        select_date("3d", date(2026, 8, 5), date(2026, 7, 30))


def test_filtering_reuses_one_seven_day_dataset():
    class Record:
        def __init__(self, day):
            self.forecast_time_local = datetime.combine(
                day, datetime.min.time(), ZoneInfo("Asia/Yakutsk")
            )

    records = [Record(day) for day in horizon_dates("7d", date(2026, 7, 30))]
    assert len(filter_dates(records, horizon_dates("today", date(2026, 7, 30)))) == 1
    assert len(filter_dates(records, horizon_dates("3d", date(2026, 7, 30)))) == 3
    assert len(filter_dates(records, horizon_dates("7d", date(2026, 7, 30)))) == 7
