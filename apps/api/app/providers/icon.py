from app.config.models import MODELS
from app.providers.base import OpenMeteoProvider


class IconProvider(OpenMeteoProvider):
    config = MODELS["icon"]
