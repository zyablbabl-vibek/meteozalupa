from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DataStatus = Literal["verified", "partially_verified", "demo"]
PointType = Literal["city", "settlement", "weather_station", "grid", "island", "coastal"]


class MapCenter(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RegionDefinition(BaseModel):
    id: str
    name: str
    short_name: str
    name_prepositional: str
    name_genitive: str
    federal_district: str
    primary_timezone: str
    default_point_id: str
    map_center: MapCenter
    map_zoom: float
    data_status: DataStatus


class ForecastPoint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    region_id: str
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str
    point_type: PointType
    is_regional_center: bool
    weight: float = Field(gt=0)
    source: str | None = None
    source_url: str | None = None
    source_id: str | None = None
    verified_at: date | None = None


class RegionMetadata(BaseModel):
    id: str
    name: str
    short_name: str
    name_prepositional: str
    name_genitive: str
    federal_district: str
    primary_timezone: str
    has_multiple_timezones: bool
    default_point_id: str
    map_center_latitude: float
    map_center_longitude: float
    map_zoom: float
    data_status: DataStatus
    point_count: int
    geojson_available: bool

