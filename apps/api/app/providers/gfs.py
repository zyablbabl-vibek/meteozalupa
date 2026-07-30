from app.config.models import MODELS
from app.providers.base import OpenMeteoProvider


class GfsProvider(OpenMeteoProvider):
    config = MODELS["gfs"]
