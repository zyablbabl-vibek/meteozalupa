from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    data_mode: Literal["mock", "live"] = "live"
    forecast_cache_ttl_seconds: int = 10800
    database_url: str = "sqlite:///./data/weather.db"
    log_level: str = "INFO"
    regions_data_dir: Path = ROOT / "data" / "regions"
    regions_registry_file: Path = ROOT / "data" / "regions" / "regions.json"
    regions_geojson_dir: Path = ROOT / "data" / "geo" / "regions"
    open_meteo_batch_size: int = 25
    open_meteo_max_concurrency: int = 3
    precipitation_event_threshold_mm: float = 0.1
    precip_daily_attention_mm: float = 10
    precip_daily_notable_mm: float = 25
    precip_hourly_attention_mm: float = 3
    precip_hourly_notable_mm: float = 8
    precip_duration_attention_hours: int = 6
    precip_model_range_attention_mm: float = 10
    precip_start_time_disagreement_hours: int = 4
    wind_speed_attention_ms: float = 8
    wind_speed_notable_ms: float = 12
    wind_gust_attention_ms: float = 15
    wind_gust_notable_ms: float = 22
    wind_duration_attention_hours: int = 6
    wind_model_range_attention_ms: float = 5
    wind_gust_range_attention_ms: float = 8
    wind_direction_disagreement_deg: float = 90
    wind_direction_change_attention_deg: float = 90

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")


settings = Settings()
