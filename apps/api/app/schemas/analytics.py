from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ModelValue(BaseModel):
    model: str
    value: float | None
    unit: str


class MetricComparison(BaseModel):
    count: int
    mean: float | None
    median: float | None
    minimum: float | None
    minimum_source: str | None
    maximum: float | None
    maximum_source: str | None
    range: float | None
    standard_deviation: float | None
    model_values: list[ModelValue]
    agreement: str | None
    is_partial: bool


class WeatherInsight(BaseModel):
    category: Literal["precipitation", "wind"]
    severity: Literal["info", "attention", "notable"]
    reason_code: str
    title: str
    description: str
    explanation: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    point_id: str | None = None
    point_name: str | None = None
    models: list[str] = Field(default_factory=list)
    values: dict[str, float | str | None] = Field(default_factory=dict)


class PrecipitationDailySummary(BaseModel):
    daily_total: MetricComparison
    hourly_peak: MetricComparison
    peak_time: datetime | None
    event_start: datetime | None
    event_end: datetime | None
    duration_hours: float | None
    confirming_models: int


class WindDailySummary(BaseModel):
    mean_speed: MetricComparison
    maximum_speed: MetricComparison
    maximum_gust: MetricComparison
    maximum_gust_time: datetime | None
    circular_mean_direction_deg: float | None
    direction_label: str | None
    maximum_direction_disagreement_deg: float | None
    strong_wind_start: datetime | None
    strong_wind_end: datetime | None
    strong_wind_duration_hours: float | None
