from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    key: str
    label: str
    endpoint: str
    identifier: str


MODELS = {
    "ecmwf": ModelConfig(
        "ecmwf", "ECMWF IFS", "https://api.open-meteo.com/v1/ecmwf", "ecmwf_ifs025"
    ),
    "gfs": ModelConfig("gfs", "NOAA GFS", "https://api.open-meteo.com/v1/gfs", "gfs_global"),
    "icon": ModelConfig(
        "icon", "DWD ICON", "https://api.open-meteo.com/v1/dwd-icon", "icon_global"
    ),
}

METRICS = (
    "temperature_2m",
    "relative_humidity_2m",
    "pressure_msl",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
)

AGREEMENT_THRESHOLDS = {
    "temperature_2m": (2.0, 5.0),
    "relative_humidity_2m": (10.0, 25.0),
    "pressure_msl": (3.0, 8.0),
    "precipitation": (1.0, 5.0),
    "cloud_cover": (15.0, 35.0),
    "wind_speed_10m": (2.0, 5.0),
    "wind_direction_10m": (30.0, 90.0),
    "wind_gusts_10m": (3.0, 7.0),
}
