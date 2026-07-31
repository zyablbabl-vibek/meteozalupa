import pytest

from app.config.settings import settings


@pytest.fixture(autouse=True)
def use_offline_data_in_tests(monkeypatch):
    monkeypatch.setattr(settings, "data_mode", "mock")
