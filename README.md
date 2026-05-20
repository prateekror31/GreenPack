# GreenPack EPR Compliance Service

A Python/FastAPI backend for EPR (Extended Producer Responsibility) compliance for plastic packaging producers in India — built as the screening task for Innotechwise / Futuryntix.

---

## Quick Start

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd greenpack-epr-service
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set your API key

```bash
set OPENAI_API_KEY=sk-ant-...        # Windows CMD
```

### 3. Run the server

```bash
uvicorn main:app --reload
# Server starts at http://localhost:8000
# Interactive docs: http://localhost:8000/docs
```

### 4. Run the demo script

```bash
bash demo.sh
```

---

## API Endpoints

### `POST /submit`
Submit a monthly plastic declaration.

**Request:**
```json
{
  "producer_id": "GREENPACK-001",
  "month": "2026-04",
  "declared_quantities_kg": {
    "rigid_plastic": 12000,
    "flexible_plastic": 8500,
    "multilayer_plastic": 3200
  }
}
```

**Response:** The stored declaration record with `record_id` and `submitted_at`.

> **Design note:** This endpoint uses **no LLM**. Validation is a deterministic problem — Pydantic handles it. Knowing when *not* to reach for an LLM is intentional.

---

### `GET /summary/{producer_id}/{month}`
Reconcile the stored declaration against ERP data and return a structured result + LLM narrative.

**Example:** `GET /summary/GREENPACK-001/2026-04`

**Response:**
```json
{
  "producer_id": "GREENPACK-001",
  "month": "2026-04",
  "reconciliation": [
    {
      "category": "flexible_plastic",
      "declared_kg": 8500,
      "procured_kg": 9100,
      "difference_kg": -600,
      "difference_pct": -6.59,
      "flagged": true
    },
    ...
  ],
  "narrative": "GreenPack's April 2026 declaration shows two categories within tolerance..."
}
```

**Design note:** The LLM is used only for *narrative generation*, not analysis. All numbers and flags are computed deterministically before the LLM is called. This is structured generation, not free-form chat.

---

### `POST /ask`
Ask a plain-English question about EPR / plastic compliance rules.

**Request:**
```json
{ "question": "What is the EPR collection target for flexible plastic?" }
```

**Response:**
```json
{
  "question": "...",
  "answer": "The EPR collection target for flexible plastic is 30% ...",
  "citations": [
    {
      "document": "Cpcb Epr Guidelines 2022",
      "section": "SECTION 5: EPR Targets and Obligations...",
      "snippet": "Flexible Plastic: 30% of total plastic packaging placed on the market"
    }
  ]
}
```

If the question cannot be answered from the corpus:
```json
{ "answer": "I do not know based on the provided documents", "citations": [] }
```

---

## Architecture & Design Choices

### ### LLM: OpenAI GPT-4o Mini
**Why:** Cost-effective and fast for structured generation tasks. The `/summary` endpoint requires the LLM to narrate only — not analyze — so tight instruction following is critical. GPT-4o Mini consistently respects the "no extra numbers, no hallucination" constraint while being significantly cheaper than GPT-4o for high-volume compliance workflows. Alternative considered: Claude Sonnet — works equally well, but OpenAI's API was chosen for this implementation.

### Embedding Model: `all-MiniLM-L6-v2` (sentence-transformers)
**Why:** Runs entirely locally (no API cost, no network latency), produces strong semantic embeddings for short-to-medium documents, and is the de facto standard for small-scale RAG. For a production system with thousands of documents, I'd move to a hosted embedding API (Cohere, OpenAI) for scale. Embeddings are cached in `data/rag_index.json` so the model only loads once.

### Storage: JSON file on disk
**Why:** Zero dependencies, trivially inspectable with a text editor, and more than sufficient for a demo/screening context. The `declarations.json` file is self-documenting. If this were a production service, I'd replace this with **SQLite via SQLAlchemy** (one-line change — the storage helpers in `models.py` are deliberately isolated behind two functions, `store_declaration` and `get_declaration`).

### Vector Store: In-memory cosine similarity (NumPy)
**Why:** For 5 documents and ~30 chunks, a full vector database (Chroma, Pinecone) would be overengineering. NumPy cosine similarity runs in microseconds at this scale. The chunk embeddings are cached on disk so startup is fast after the first run. For a production RAG system with thousands of documents, I'd switch to **ChromaDB** (local, persistent) or **Pinecone** (managed, scalable).

### AI Coding Assistant Used
**Claude (claude.ai):** Used for initial scaffolding of the RAG pipeline retrieval logic and for the Pydantic model validator patterns. The reconciliation logic and FastAPI router structure were written manually.

---

## RAG Corpus — Sources

| File | Description | Type |
|------|-------------|------|
| `cpcb_epr_guidelines_2022.txt` | CPCB EPR registration, categories, monthly declaration requirements, EPR targets | Mock policy document (based on public CPCB rules) |
| `plastic_waste_management_rules_2022.txt` | PWM Rules 2022 — single-use plastic bans, thickness requirements, EPR credit system | Mock summary (based on MoEFCC notifications) |
| `greenpack_reconciliation_handbook.txt` | GreenPack internal reconciliation procedure and tolerance policy | Mock internal document |
| `epr_certificate_trading_2023.txt` | EPR certificate marketplace, pricing, purchasing process | Mock CPCB circular |
| `epr_enforcement_penalties.txt` | Environmental Compensation rates, Show Cause Notices, cancellation process | Mock advisory note |

**Note:** These are mock policy documents created for demonstration purposes, grounded in publicly available information about India's EPR framework (CPCB website, MoEFCC notifications, Plastic Waste Management Rules 2016/2022). They should not be used as legal advice.

**Real public sources consulted:**
- https://eprplastic.cpcb.gov.in
- https://moef.gov.in/en/division/environment-labs-division/hazardous-substance-management/plastic-waste-management/
- https://en.wikipedia.org/wiki/Extended_producer_responsibility

---

## Project Structure

```
greenpack-epr-service/
├── main.py                  # FastAPI app, router registration
├── models.py                # Pydantic schemas + JSON storage helpers
├── requirements.txt
├── demo.sh                  # End-to-end demo curl script
├── routers/
│   ├── submit.py            # POST /submit
│   ├── summary.py           # GET /summary/{producer_id}/{month}
│   └── ask.py               # POST /ask (RAG pipeline)
├── data/
│   ├── erp_feed.csv         # Mock ERP procurement data
│   ├── declarations.json    # Auto-created by /submit
│   └── rag_index.json       # Auto-created embedding cache
└── rag_corpus/
    ├── cpcb_epr_guidelines_2022.txt
    ├── plastic_waste_management_rules_2022.txt
    ├── greenpack_reconciliation_handbook.txt
    ├── epr_certificate_trading_2023.txt
    └── epr_enforcement_penalties.txt
```

---

## One Thing I'd Do Differently With Another Day

I'd add **async support** throughout. Currently, the LLM calls in `summary.py` and `ask.py` are synchronous, which blocks the FastAPI event loop under concurrent load. With another day, I'd switch the Anthropic client to `AsyncAnthropic`, the embedding calls to a thread pool (`asyncio.run_in_executor`), and the file I/O to `aiofiles`. This would make the service production-ready for concurrent users without requiring a full infrastructure change.

---

## Running Tests

```bash
pip install pytest httpx
pytest tests/
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT |
