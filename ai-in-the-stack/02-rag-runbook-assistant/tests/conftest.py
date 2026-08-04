"""Pytest fixtures for the RAG runbook assistant."""

import os

# Settings load at import time — set before app modules are imported.
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

from app.main import app

API_HEADERS = {"X-API-Key": "test-api-key"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return API_HEADERS.copy()
