import pytest
from fastapi.testclient import TestClient

from main import app
from utils import callback_store


@pytest.fixture(autouse=True)
def clear_store():
    callback_store.clear()
    yield
    callback_store.clear()


@pytest.fixture
def client():
    return TestClient(app)
