import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    create_engine,
    delete,
    inspect,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.config.settings import settings
from app.regions.registry import list_regions, load_points
from app.schemas.forecast import ForecastRecord


class Base(DeclarativeBase):
    pass


class ForecastCache(Base):
    __tablename__ = "forecast_cache"
    __table_args__ = (
        Index("ix_forecast_region_local_date_v2", "region_id", "local_date"),
        Index("ix_forecast_region_point_time", "region_id", "point_id", "forecast_time"),
        Index("ix_forecast_region_model_fetched", "region_id", "model", "fetched_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[str] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(16), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    local_date: Mapped[date | None] = mapped_column(Date, index=True)
    model: Mapped[str] = mapped_column(String(40), index=True)
    point_id: Mapped[str] = mapped_column(String(80), index=True)
    forecast_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    record_json: Mapped[str] = mapped_column(Text)


class RawResponse(Base):
    __tablename__ = "raw_responses"
    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[str] = mapped_column(String(80), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    model: Mapped[str] = mapped_column(String(40))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[str] = mapped_column(Text)


class RegionRow(Base):
    __tablename__ = "regions"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    primary_timezone: Mapped[str] = mapped_column(String(80))
    data_status: Mapped[str] = mapped_column(String(32))


class ForecastPointRow(Base):
    __tablename__ = "forecast_points"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    region_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("regions.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(80))
    point_type: Mapped[str] = mapped_column(String(32))
    is_regional_center: Mapped[bool] = mapped_column(Boolean)
    weight: Mapped[float] = mapped_column(Float)


database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

db_path = database_url.removeprefix("sqlite:///")
if database_url.startswith("sqlite:///"):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite:///") else {}
engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
Base.metadata.create_all(engine)


def _migrate_legacy_cache() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        for table_name in ("forecast_cache", "raw_responses"):
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if "region_id" not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} ADD COLUMN region_id "
                        "VARCHAR(80) NOT NULL DEFAULT 'amur-oblast'"
                    )
                )
            if table_name == "forecast_cache" and "local_date" not in columns:
                connection.execute(text("ALTER TABLE forecast_cache ADD COLUMN local_date DATE"))
                connection.execute(
                    text("UPDATE forecast_cache SET local_date = day WHERE local_date IS NULL")
                )
            if table_name == "forecast_cache" and "source" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE forecast_cache ADD COLUMN source "
                        "VARCHAR(16) NOT NULL DEFAULT 'mock'"
                    )
                )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_forecast_region_local_date_v2 "
                "ON forecast_cache (region_id, local_date)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_forecast_region_point_time "
                "ON forecast_cache (region_id, point_id, forecast_time)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_forecast_region_model_fetched "
                "ON forecast_cache (region_id, model, fetched_at)"
            )
        )


def _sync_region_catalog() -> None:
    with Session(engine) as session:
        for region in list_regions():
            session.merge(
                RegionRow(
                    id=region.id,
                    name=region.name,
                    primary_timezone=region.primary_timezone,
                    data_status=region.data_status,
                )
            )
            for point in load_points(region.id):
                session.merge(
                    ForecastPointRow(
                        id=point.id,
                        region_id=point.region_id,
                        name=point.name,
                        latitude=point.latitude,
                        longitude=point.longitude,
                        timezone=point.timezone,
                        point_type=point.point_type,
                        is_regional_center=point.is_regional_center,
                        weight=point.weight,
                    )
                )
        session.commit()


_migrate_legacy_cache()
_sync_region_catalog()


def storage_backend() -> str:
    return "postgresql" if database_url.startswith("postgresql+") else "sqlite"


def load_cached(
    region_id: str, period_start: date, period_end: date, source: str
) -> list[ForecastRecord]:
    with Session(engine) as session:
        rows = session.scalars(
            select(ForecastCache).where(
                ForecastCache.region_id == region_id,
                ForecastCache.source == source,
                ForecastCache.local_date >= period_start,
                ForecastCache.local_date <= period_end,
            )
        ).all()
        records = []
        for row in rows:
            try:
                records.append(ForecastRecord.model_validate_json(row.record_json))
            except ValueError:
                # Legacy records predate region/timezone fields and are refreshed lazily.
                continue
        return records


def prune_past(region_id: str, today: date, retention_days: int = 0) -> int:
    cutoff = today - timedelta(days=max(0, retention_days))
    with Session(engine) as session:
        forecast_result = session.execute(
            delete(ForecastCache).where(
                ForecastCache.region_id == region_id,
                ForecastCache.local_date < cutoff,
            )
        )
        session.execute(
            delete(RawResponse).where(
                RawResponse.region_id == region_id,
                RawResponse.day < cutoff,
            )
        )
        session.commit()
        return int(getattr(forecast_result, "rowcount", 0) or 0)


def save(
    region_id: str,
    period_start: date,
    records: list[ForecastRecord],
    raw: dict[str, list[dict]],
    primary_timezone: str,
    source: str,
) -> None:
    if not records:
        return
    with Session(engine) as session:
        for model in {record.model for record in records}:
            model_records = [record for record in records if record.model == model]
            point_ids = {record.point_id for record in model_records}
            model_start = min(record.local_date for record in model_records)
            model_end = max(record.local_date for record in model_records)
            session.execute(
                delete(ForecastCache).where(
                    ForecastCache.region_id == region_id,
                    ForecastCache.source == source,
                    ForecastCache.model == model,
                    ForecastCache.point_id.in_(point_ids),
                    ForecastCache.local_date >= model_start,
                    ForecastCache.local_date <= model_end,
                )
            )
        if settings.store_raw_responses:
            session.execute(
                delete(RawResponse).where(
                    RawResponse.region_id == region_id,
                    RawResponse.day == period_start,
                    RawResponse.model.in_(raw),
                )
            )
        session.add_all(
            ForecastCache(
                region_id=region_id,
                source=source,
                day=period_start,
                local_date=r.local_date,
                model=r.model,
                point_id=r.point_id,
                forecast_time=r.forecast_time_utc,
                fetched_at=r.fetched_at,
                record_json=r.model_dump_json(),
            )
            for r in records
        )
        if settings.store_raw_responses:
            now = datetime.now(UTC)
            session.add_all(
                RawResponse(
                    region_id=region_id,
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
                            "region_id": region_id,
                            "primary_timezone": primary_timezone,
                            "source": source,
                            "responses": payload,
                        }
                    ),
                )
                for model, payload in raw.items()
            )
        session.commit()


def prune_all_regions() -> None:
    for region in list_regions():
        today = datetime.now(ZoneInfo(region.primary_timezone)).date()
        prune_past(region.id, today, settings.forecast_retention_past_days)


prune_all_regions()
