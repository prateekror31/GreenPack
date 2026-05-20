"""
tests/test_endpoints.py — Basic tests for all three endpoints.

Run with: pytest tests/ -v
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

# Override API key for tests (summary/ask will use stub if not set)
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Endpoint 1: POST /submit
# ---------------------------------------------------------------------------

def test_submit_valid():
    response = client.post(
        "/submit",
        json={
            "producer_id": "TEST-001",
            "month": "2026-04",
            "declared_quantities_kg": {
                "rigid_plastic": 1000,
                "flexible_plastic": 500,
                "multilayer_plastic": 250,
            },
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["producer_id"] == "TEST-001"
    assert data["month"] == "2026-04"
    assert "record_id" in data
    assert "submitted_at" in data


def test_submit_negative_weight():
    response = client.post(
        "/submit",
        json={
            "producer_id": "TEST-001",
            "month": "2026-04",
            "declared_quantities_kg": {
                "rigid_plastic": -100,
                "flexible_plastic": 500,
                "multilayer_plastic": 250,
            },
        },
    )
    assert response.status_code == 422  # Pydantic validation error


def test_submit_invalid_month_format():
    response = client.post(
        "/submit",
        json={
            "producer_id": "TEST-001",
            "month": "04-2026",  # wrong format
            "declared_quantities_kg": {
                "rigid_plastic": 1000,
                "flexible_plastic": 500,
                "multilayer_plastic": 250,
            },
        },
    )
    assert response.status_code == 422


def test_submit_missing_producer_id():
    response = client.post(
        "/submit",
        json={
            "month": "2026-04",
            "declared_quantities_kg": {
                "rigid_plastic": 1000,
                "flexible_plastic": 500,
                "multilayer_plastic": 250,
            },
        },
    )
    assert response.status_code == 422


def test_submit_invalid_month_value():
    response = client.post(
        "/submit",
        json={
            "producer_id": "TEST-001",
            "month": "2026-13",  # month 13 doesn't exist
            "declared_quantities_kg": {
                "rigid_plastic": 1000,
                "flexible_plastic": 500,
                "multilayer_plastic": 250,
            },
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Endpoint 2: GET /summary — basic 404 test (LLM not called in test)
# ---------------------------------------------------------------------------

def test_summary_not_found():
    response = client.get("/summary/NONEXISTENT-999/2026-01")
    assert response.status_code == 404
    assert "No declaration found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Endpoint 3: POST /ask — basic validation
# ---------------------------------------------------------------------------

def test_ask_missing_question():
    response = client.post("/ask", json={})
    assert response.status_code == 422


def test_ask_too_short_question():
    response = client.post("/ask", json={"question": "hi"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "endpoints" in data
    assert len(data["endpoints"]) == 3
