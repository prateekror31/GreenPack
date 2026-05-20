"""
Endpoint 3 · POST /ask

RAG pipeline over EPR / plastic compliance documents.
Uses sentence-transformers for embeddings and cosine similarity for retrieval.
LLM (Claude) generates the final answer with citations.
"""

import json
import os
from pathlib import Path
from typing import List, Tuple

from openai import OpenAI
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models import AskRequest

router = APIRouter()

CORPUS_DIR = Path(__file__).parent.parent / "rag_corpus"
CACHE_FILE = Path(__file__).parent.parent / "data" / "rag_index.json"

# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class Citation(BaseModel):
    document: str
    section: str
    snippet: str


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: List[Citation]


# ---------------------------------------------------------------------------
# RAG helpers
# ---------------------------------------------------------------------------

_index: List[dict] | None = None  # lazy-loaded


def _chunk_document(doc_id: str, title: str, text: str, chunk_size: int = 400) -> List[dict]:
    """Split a document into overlapping chunks with metadata."""
    words = text.split()
    chunks = []
    step = chunk_size - 80  # 80-word overlap
    for i in range(0, max(len(words) - 1, 1), step):
        chunk_words = words[i: i + chunk_size]
        chunk_text = " ".join(chunk_words)
        # Derive a section heading from the first sentence / first ~8 words
        section_hint = " ".join(chunk_words[:8]) + "..."
        chunks.append(
            {
                "doc_id": doc_id,
                "title": title,
                "section": section_hint,
                "text": chunk_text,
                "chunk_index": len(chunks),
            }
        )
        if i + chunk_size >= len(words):
            break
    return chunks


def _load_corpus() -> List[dict]:
    """Load all .txt files from rag_corpus/ and chunk them."""
    chunks = []
    for txt_file in sorted(CORPUS_DIR.glob("*.txt")):
        title = txt_file.stem.replace("_", " ").title()
        text = txt_file.read_text(encoding="utf-8")
        doc_chunks = _chunk_document(txt_file.stem, title, text)
        chunks.extend(doc_chunks)
    return chunks


def _get_embedder():
    """Lazy-import sentence-transformers to avoid slow startup."""
    from sentence_transformers import SentenceTransformer  # type: ignore
    return SentenceTransformer("all-MiniLM-L6-v2")


def _build_or_load_index() -> List[dict]:
    global _index
    if _index is not None:
        return _index

    corpus_chunks = _load_corpus()
    if not corpus_chunks:
        raise HTTPException(
            status_code=500,
            detail="RAG corpus is empty. Add .txt files to the rag_corpus/ directory.",
        )

    # Check if we have a cached embedding index
    if CACHE_FILE.exists():
        cached = json.loads(CACHE_FILE.read_text())
        # Validate cache matches corpus (simple length check)
        if len(cached) == len(corpus_chunks):
            _index = cached
            return _index

    # Build embeddings
    embedder = _get_embedder()
    texts = [c["text"] for c in corpus_chunks]
    embeddings = embedder.encode(texts, show_progress_bar=False).tolist()

    for chunk, emb in zip(corpus_chunks, embeddings):
        chunk["embedding"] = emb

    CACHE_FILE.write_text(json.dumps(corpus_chunks))
    _index = corpus_chunks
    return _index


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def _retrieve(question: str, top_k: int = 4) -> List[dict]:
    index = _build_or_load_index()
    embedder = _get_embedder()
    q_emb = embedder.encode([question], show_progress_bar=False)[0].tolist()

    scored = [
        (chunk, _cosine_similarity(q_emb, chunk["embedding"]))
        for chunk in index
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:top_k]]


def _build_context_block(chunks: List[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[SOURCE {i}]\n"
            f"Document: {c['title']} (id: {c['doc_id']})\n"
            f"Section: {c['section']}\n"
            f"Text: {c['text']}\n"
        )
    return "\n".join(parts)


def _generate_answer(question: str, chunks: List[dict]) -> Tuple[str, List[Citation]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set.",
        )

    client = OpenAI(api_key=api_key)
    context = _build_context_block(chunks)

    system_prompt = """You are a compliance assistant for GreenPack Industries, 
an Indian plastic packaging producer. You answer questions about EPR 
(Extended Producer Responsibility) rules strictly from the provided documents.

Rules:
1. Answer ONLY from the provided SOURCE documents. 
2. At the end of your answer, output a JSON block (fenced with ```json ... ```) 
   containing a list of citations used. Each citation has:
   - "doc_id": the document id
   - "title": the document title  
   - "section": the section hint
   - "snippet": a 1-2 sentence excerpt that supports your answer
3. If the question CANNOT be answered from the documents, reply with exactly:
   I do not know based on the provided documents.
   and an empty citations list.
4. Do NOT hallucinate or add information not in the sources."""

    user_prompt = f"""Context documents:
{context}

Question: {question}

Answer (followed by ```json citations block```):]"""

    message = client.chat.completions.create(
    model="gpt-4o-mini",
    max_tokens=700,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    )
    full_response = message.choices[0].message.content.strip()

    # Parse answer and citations
    citations: List[Citation] = []
    answer_text = full_response

    if "```json" in full_response:
        parts = full_response.split("```json", 1)
        answer_text = parts[0].strip()
        json_part = parts[1].split("```")[0].strip()
        try:
            raw_citations = json.loads(json_part)
            for rc in raw_citations:
                citations.append(
                    Citation(
                        document=rc.get("title", rc.get("doc_id", "Unknown")),
                        section=rc.get("section", ""),
                        snippet=rc.get("snippet", ""),
                    )
                )
        except json.JSONDecodeError:
            pass  # Return answer without citations if parsing fails

    return answer_text, citations


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest) -> AskResponse:
    """
    Answer a plain-English question about EPR / plastic compliance rules
    using a RAG pipeline over the corpus in rag_corpus/.

    Returns the answer with citations. If the question cannot be answered
    from the corpus, returns 'I do not know based on the provided documents'.
    """
    # Retrieve relevant chunks
    relevant_chunks = _retrieve(req.question, top_k=4)

    # Generate answer
    answer, citations = _generate_answer(req.question, relevant_chunks)

    return AskResponse(
        question=req.question,
        answer=answer,
        citations=citations,
    )
