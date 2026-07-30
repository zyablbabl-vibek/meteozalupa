import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import Date, DateTime, String, Text, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.config.settings import settings
from app.schemas.forecast import ForecastRecord


class Base(DeclarativeBase):
    pass


class ForecastCache(Base):
    __tablename__ = "forecast_cache"
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    model: Mapped[str] = mapped_column(String(40), index=True)
    point_id: Mapped[str] = mapped_column(String(80), index=True)
    forecast_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    record_json: Mapped[str] = mapped_column(Text)


class RawResponse(Base):
    __tablename__ = "raw_responses"
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    model: Mapped[str] = mapped_column(String(40))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[str] = mapped_column(Text)


db_path = settings.database_url.removeprefix("sqlite:///")
if settings.database_url.startswith("sqlite:///"):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)


def load_fresh(period_start: date, ttl_seconds: int) -> list[ForecastRecord]:
    cutoff = datetime.now(UTC) - timedelta(seconds=ttl_seconds)
    with Session(engine) as session:
        rows = session.scalars(
            select(ForecastCache).where(
                ForecastCache.day == period_start, ForecastCache.fetched_at >= cutoff
            )
        ).all()
        return [ForecastRecord.model_validate_json(row.record_json) for row in rows]


def save(period_start: date, records: list[ForecastRecord], raw: dict[str, list[dict]]) -> None:
    with Session(engine) as session:
        session.execute(delete(ForecastCache).where(ForecastCache.day == period_start))
        session.execute(delete(RawResponse).where(RawResponse.day == period_start))
        session.add_all(
            ForecastCache(
                day=period_start,
                model=r.model,
                point_id=r.point_id,
                forecast_time=r.forecast_time_utc,
                fetched_at=r.fetched_at,
                record_json=r.model_dump_json(),
            )
            for r in records
        )
        now = datetime.now(UTC)
        session.add_all(
            RawResponse(
                day=period_start,
                model=model,
                fetched_at=now,
                payload_json=json.dumps(
                    {
                        "period_start": period_start.isoformat(),
                        "period_end": max(
                            (r.forecast_time_local.date() for r in records),
                            default=period_start,
                        ).isoformat(),
                        "timezone": "Asia/Yakutsk",
                        "responses": payload,
                    }
                ),
            )
            for model, payload in raw.items()
        )
        session.commit()
