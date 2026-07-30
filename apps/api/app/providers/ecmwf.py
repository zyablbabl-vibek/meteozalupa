from app.config.models import MODELS
from app.providers.base import OpenMeteoProvider


class EcmwfProvider(OpenMeteoProvider):
    config = MODELS["ecmwf"]
