"""
models.py — Pydantic schemas and simple JSON-file storage layer.

Storage choice: JSON file on disk.
Rationale: Zero dependencies, trivially inspectable, more than enough for a
demo/screening task. A production system would use PostgreSQL + SQLAlchemy.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
import re

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DECLARATIONS_FILE = DATA_DIR / "declarations.json"
ERP_FEED_FILE = Path(__file__).parent / "data" / "erp_feed.csv"

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

PLASTIC_CATEGORIES = {"rigid_plastic", "flexible_plastic", "multilayer_plastic"}


class DeclaredQuantities(BaseModel):
    rigid_plastic: float = Field(..., ge=0, description="Rigid plastic in kg")
    flexible_plastic: float = Field(..., ge=0, description="Flexible plastic in kg")
    multilayer_plastic: float = Field(..., ge=0, description="Multilayer plastic in kg")


class SubmitRequest(BaseModel):
    producer_id: str = Field(..., min_length=1)
    month: str = Field(..., description="Format: YYYY-MM")
    declared_quantities_kg: DeclaredQuantities

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: str) -> str:
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", v):
            raise ValueError("month must be in YYYY-MM format, e.g. 2026-04")
        return v

    @field_validator("producer_id")
    @classmethod
    def validate_producer_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("producer_id must not be blank")
        return v


class DeclarationRecord(BaseModel):
    record_id: str
    producer_id: str
    month: str
    declared_quantities_kg: DeclaredQuantities
    submitted_at: str  # ISO-8601


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)


# ---------------------------------------------------------------------------
# Storage helpers (JSON file, keyed by producer_id + month)
# ---------------------------------------------------------------------------

def _load_store() -> Dict:
    if DECLARATIONS_FILE.exists():
        return json.loads(DECLARATIONS_FILE.read_text())
    return {}


def _save_store(store: Dict) -> None:
    DECLARATIONS_FILE.write_text(json.dumps(store, indent=2))


def store_declaration(req: SubmitRequest) -> DeclarationRecord:
    store = _load_store()
    key = f"{req.producer_id}::{req.month}"
    record = DeclarationRecord(
        record_id=str(uuid.uuid4()),
        producer_id=req.producer_id,
        month=req.month,
        declared_quantities_kg=req.declared_quantities_kg,
        submitted_at=datetime.now(timezone.utc).isoformat(),
    )
    store[key] = record.model_dump()
    _save_store(store)
    return record


def get_declaration(producer_id: str, month: str) -> Optional[DeclarationRecord]:
    store = _load_store()
    key = f"{producer_id}::{month}"
    raw = store.get(key)
    if raw is None:
        return None
    return DeclarationRecord(**raw)
