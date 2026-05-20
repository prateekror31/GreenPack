"""
Endpoint 1 · POST /submit

Accepts GreenPack's monthly plastic declaration.
Validates deterministically (no LLM), stores, and returns the record.
"""

from fastapi import APIRouter
from models import SubmitRequest, DeclarationRecord, store_declaration

router = APIRouter()


@router.post("/submit", response_model=DeclarationRecord, status_code=201)
def submit_declaration(req: SubmitRequest) -> DeclarationRecord:
    """
    Submit a monthly plastic declaration.

    - Validates payload deterministically (Pydantic).
    - Stores to JSON file with generated record_id and timestamp.
    - Returns the stored record.
    - **Does NOT call the LLM** — validation is a deterministic problem.
    """
    record = store_declaration(req)
    return record
