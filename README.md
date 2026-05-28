# GreenPack EPR Compliance Service

A FastAPI-based backend service for managing **Extended Producer Responsibility (EPR)** compliance workflows for plastic packaging producers in India.

This project was developed as a screening assignment and demonstrates:
- FastAPI backend development
- REST API design
- Retrieval-Augmented Generation (RAG)
- OpenAI-powered narrative generation
- Semantic search using embeddings
- Deterministic reconciliation logic
- Lightweight vector retrieval architecture

---

# Features

- Submit monthly plastic declarations
- Reconcile declarations against ERP procurement data
- AI-generated compliance narratives
- RAG-powered compliance Q&A system
- Semantic document retrieval using embeddings
- Swagger/OpenAPI documentation
- Local JSON-based persistence
- Lightweight vector similarity search using NumPy

---

# Tech Stack

| Component | Technology |
|---|---|
| Backend Framework | FastAPI |
| Server | Uvicorn |
| Validation | Pydantic |
| LLM | OpenAI GPT-4o Mini |
| Embeddings | sentence-transformers |
| Vector Search | NumPy cosine similarity |
| Storage | JSON |
| Language | Python 3.11 |

---

# Project Structure

```bash
greenpack-epr-service/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── routers/
│   │   ├── submit.py
│   │   ├── summary.py
│   │   └── ask.py
│
├── data/
│   ├── erp_feed.csv
│   ├── declarations.json
│   └── rag_index.json
│
├── rag_corpus/
│   ├── cpcb_epr_guidelines_2022.txt
│   ├── plastic_waste_management_rules_2022.txt
│   ├── greenpack_reconciliation_handbook.txt
│   ├── epr_certificate_trading_2023.txt
│   └── epr_enforcement_penalties.txt
│
├── requirements.txt
├── demo.sh
├── .env
├── .gitignore
└── README.md
```

---

# Setup Instructions

## 1. Clone Repository

```bash
git clone <your-github-repo-url>
cd greenpack-epr-service
```

---

## 2. Create Virtual Environment

```bash
py -3.11 -m venv venv
```

Activate environment:

### Windows PowerShell

```powershell
.\venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key
```

---

# Run the FastAPI Server

```bash
uvicorn app.main:app --reload
```

Server runs at:

```txt
http://127.0.0.1:8000
```

Swagger Docs:

```txt
http://127.0.0.1:8000/docs
```

---

# API Endpoints

## POST `/submit`

Submit monthly EPR plastic declaration.

### Request

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

---

## GET `/summary/{producer_id}/{month}`

Returns reconciliation analysis and AI-generated compliance summary.

### Example

```txt
GET /summary/GREENPACK-001/2026-04
```

---

## POST `/ask`

Ask compliance-related questions using the RAG pipeline.

### Request

```json
{
  "question": "What is the EPR target for flexible plastic?"
}
```

---

# RAG Pipeline

This project uses a lightweight Retrieval-Augmented Generation (RAG) architecture.

## Flow

```txt
User Question
      ↓
Document Retrieval
      ↓
Embedding Similarity Search
      ↓
Relevant Context Extraction
      ↓
OpenAI Response Generation
```

## Embedding Model

```txt
all-MiniLM-L6-v2
```

Used for:
- semantic search
- chunk similarity
- lightweight vector retrieval

---

# Design Decisions

## Why FastAPI?

- Fast performance
- Automatic Swagger docs
- Simple async architecture
- Excellent validation support

---

## Why JSON Storage?

Chosen for simplicity and portability during screening evaluation.

In production:
- SQLite
- PostgreSQL
- SQLAlchemy ORM

would be preferred.

---

## Why NumPy Vector Search?

For a small document corpus:
- fast
- lightweight
- no external vector DB required

Production alternative:
- Pinecone
- ChromaDB
- Weaviate

---

# AI Usage Strategy

The LLM is intentionally used only for:
- narrative generation
- natural language responses

All compliance calculations and reconciliation logic are deterministic and computed before the LLM call to avoid hallucinations.

---

# Running Tests

```bash
pip install pytest httpx
pytest tests/
```

---

# Future Improvements

- Async OpenAI calls
- Persistent vector database
- Docker deployment
- Authentication & authorization
- PostgreSQL integration
- Background task queue
- Production-grade logging & monitoring

--- --- ---- ---- ----- ---- ---- --- 

## Stack Choices, AI Disclosure & Trade-off

### Stack Choices
| Layer | Choice | Reason |
|---|---|---|
| **Framework** | FastAPI | Auto-generates Swagger docs, native Pydantic support, fast to build |
| **LLM** | OpenAI GPT-4o Mini | Cost-effective, strong instruction following for structured narrative generation |
| **Embeddings** | `all-MiniLM-L6-v2` (sentence-transformers) | Runs fully locally, zero API cost, cached on disk after first run |
| **Storage** | JSON file on disk | Zero dependencies, human-readable, trivially swappable to SQLite |
| **Vector Store** | NumPy cosine similarity | No overhead for 5 documents; a real vector DB would be overengineering here |
| **Validation** | Pydantic v2 | Deterministic, no LLM needed — exactly the right tool for input validation |

### AI Assistant Disclosure
This project was built with the assistance of **Claude (claude.ai)** as an AI coding assistant.
It was used for:
- Initial scaffolding of the RAG pipeline retrieval logic
- Pydantic validator patterns
- README structure and documentation

All business logic (reconciliation math, tolerance flagging, endpoint design) 
was written and reviewed manually. The AI output was understood, tested, and 
intentionally modified — not blindly copy-pasted.

### One Trade-off I Made
**Simplicity over scalability in the storage and vector layer.**

I chose a JSON file for storage and NumPy cosine similarity for retrieval 
instead of SQLite + ChromaDB. This made the project trivially easy to run 
locally with zero setup — no database to install, no vector store to configure. 
The trade-off is that it won't scale beyond a few hundred records or documents.

With another day, I would replace the JSON store with **SQLite via SQLAlchemy** 
and the NumPy retrieval with **ChromaDB** — both are drop-in changes since the 
storage logic is isolated behind two functions (`store_declaration`, 
`get_declaration`) and the RAG retrieval is self-contained in `ask.py`.

# Author

Prateek Kumar

- Python Developer
- AI/ML Enthusiast
- FastAPI & Data Analytics Learner
