import pytest

from explainer.config import Settings, get_settings
from explainer.db import Database


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path, api_token="a" * 32, tenant_keys='{"other":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}'
    ).prepare()


@pytest.fixture
def db(settings):
    return Database(settings.data_dir)


@pytest.fixture
def client(settings, monkeypatch):
    from fastapi.testclient import TestClient
    from explainer.api import app

    monkeypatch.setattr("explainer.api.get_settings", lambda: settings)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def headers():
    return {"Authorization": "Bearer " + "a" * 32}
