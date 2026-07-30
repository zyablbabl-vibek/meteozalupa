from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    data_mode: Literal["mock", "live"] = "mock"
    forecast_cache_ttl_seconds: int = 10800
    database_url: str = "sqlite:///./data/weather.db"
    log_level: str = "INFO"
    points_file: Path = ROOT / "data" / "amur_points.json"

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")


settings = Settings()
