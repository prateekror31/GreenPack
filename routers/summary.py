"""
Endpoint 2 · GET /summary/{producer_id}/{month}

Reads the stored declaration, reads the mock ERP feed, reconciles,
then uses Claude to generate a plain-English narrative summary.
"""

import csv
import os
from pathlib import Path
from typing import Dict, List

from openai import OpenAI
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models import get_declaration, ERP_FEED_FILE

router = APIRouter()

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CategoryReconciliation(BaseModel):
    category: str
    declared_kg: float
    procured_kg: float
    difference_kg: float
    difference_pct: float
    flagged: bool  # True if abs(diff%) > 5 %


class SummaryResponse(BaseModel):
    producer_id: str
    month: str
    reconciliation: List[CategoryReconciliation]
    narrative: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_erp_feed(producer_id: str, month: str) -> Dict[str, float]:
    """
    Parse the mock ERP CSV and return {category: procured_kg} for the
    given producer + month.
    """
    if not ERP_FEED_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail=f"ERP feed file not found at {ERP_FEED_FILE}. "
                   "Please ensure data/erp_feed.csv exists.",
        )

    result: Dict[str, float] = {}
    with open(ERP_FEED_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["producer_id"].strip() == producer_id and row["month"].strip() == month:
                result[row["category"].strip()] = float(row["procured_kg"])
    return result


def _reconcile(
    declared: Dict[str, float], procured: Dict[str, float]
) -> List[CategoryReconciliation]:
    categories = set(declared) | set(procured)
    results = []
    for cat in sorted(categories):
        dec = declared.get(cat, 0.0)
        proc = procured.get(cat, 0.0)
        diff_kg = dec - proc
        # Avoid division by zero; if procured is 0 and declared > 0, that's a 100 % discrepancy
        diff_pct = (diff_kg / proc * 100) if proc != 0 else (100.0 if dec != 0 else 0.0)
        results.append(
            CategoryReconciliation(
                category=cat,
                declared_kg=dec,
                procured_kg=proc,
                difference_kg=round(diff_kg, 2),
                difference_pct=round(diff_pct, 2),
                flagged=abs(diff_pct) > 5.0,
            )
        )
    return results


def _build_reconciliation_text(items: List[CategoryReconciliation]) -> str:
    lines = []
    for r in items:
        status = "FLAGGED" if r.flagged else "OK"
        lines.append(
            f"  - {r.category}: declared={r.declared_kg} kg, "
            f"procured={r.procured_kg} kg, "
            f"diff={r.difference_kg} kg ({r.difference_pct:+.1f}%) [{status}]"
        )
    return "\n".join(lines)


def _generate_narrative(
    producer_id: str,
    month: str,
    items: List[CategoryReconciliation],
) -> str:
    """
    Call Claude to produce a 3-5 sentence plain-English summary.
    The LLM's job is NARRATIVE only — all analysis is already done.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return (
            "[LLM narrative unavailable — set OPENAI_API_KEY env variable. "
            "Reconciliation data above is complete.]"
        )

    client = OpenAI(api_key=api_key)

    reconciliation_text = _build_reconciliation_text(items)
    flagged = [r for r in items if r.flagged]
    ok = [r for r in items if not r.flagged]

    prompt = f"""You are a compliance assistant for an Indian plastic packaging company.
Below is the EPR (Extended Producer Responsibility) reconciliation result for producer 
'{producer_id}' for month '{month}'. The analysis is already complete — your job is to 
write a 3-5 sentence plain-English summary for a compliance officer.

Reconciliation data:
{reconciliation_text}

Instructions:
- Mention which categories are flagged (difference > 5%) and which are within tolerance.
- Explain what the discrepancy means in practical terms.
- Recommend a specific action (e.g. re-check ERP data, revise declaration, consult compliance team).
- Do NOT add new analysis or numbers not in the data above.
- Write in professional but plain English, no bullet points, flowing prose only.
- 3 to 5 sentences maximum.

Write the narrative now:"""

    message = client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=300,
    messages=[{"role": "user", "content": prompt}],
    )
    return message.choices[0].message.content.strip()
    


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get("/summary/{producer_id}/{month}", response_model=SummaryResponse)
def get_summary(producer_id: str, month: str) -> SummaryResponse:
    """
    Reconcile the stored declaration against the mock ERP feed and return
    a structured result plus an LLM-generated narrative.
    """
    # 1. Fetch stored declaration
    declaration = get_declaration(producer_id, month)
    if declaration is None:
        raise HTTPException(
            status_code=404,
            detail=f"No declaration found for producer '{producer_id}' month '{month}'. "
                   "Submit via POST /submit first.",
        )

    # 2. Load ERP feed
    procured = _load_erp_feed(producer_id, month)
    if not procured:
        raise HTTPException(
            status_code=404,
            detail=f"No ERP data found for producer '{producer_id}' month '{month}'.",
        )

    # 3. Deterministic reconciliation
    declared_dict = declaration.declared_quantities_kg.model_dump()
    reconciliation = _reconcile(declared_dict, procured)

    # 4. LLM narrative (structured generation — NOT free-form chat)
    narrative = _generate_narrative(producer_id, month, reconciliation)

    return SummaryResponse(
        producer_id=producer_id,
        month=month,
        reconciliation=reconciliation,
        narrative=narrative,
    )
