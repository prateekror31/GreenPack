#!/usr/bin/env bash
# demo.sh — Demonstrates all three endpoints in sequence.
# Usage: bash demo.sh [BASE_URL]
# Defaults to http://localhost:8000

BASE="${1:-http://localhost:8000}"

echo "========================================"
echo "  GreenPack EPR Service — Live Demo"
echo "========================================"
echo ""

# ── Endpoint 1: Submit declaration ────────────────────────────────────────
echo "1️⃣  POST /submit — Submit monthly plastic declaration"
echo "---"
curl -s -X POST "$BASE/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "producer_id": "GREENPACK-001",
    "month": "2026-04",
    "declared_quantities_kg": {
      "rigid_plastic": 12000,
      "flexible_plastic": 8500,
      "multilayer_plastic": 3200
    }
  }' | python3 -m json.tool
echo ""

# ── Endpoint 2: Reconciliation summary ────────────────────────────────────
echo "2️⃣  GET /summary/GREENPACK-001/2026-04 — Reconcile & summarize"
echo "---"
curl -s "$BASE/summary/GREENPACK-001/2026-04" | python3 -m json.tool
echo ""

# ── Endpoint 3: Ask an EPR question ───────────────────────────────────────
echo "3️⃣  POST /ask — Ask a compliance question (RAG)"
echo "---"
curl -s -X POST "$BASE/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the EPR collection target for flexible plastic in India?"}' \
  | python3 -m json.tool
echo ""

echo "4️⃣  POST /ask — Question outside the corpus (should return 'I do not know')"
echo "---"
curl -s -X POST "$BASE/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the capital of France?"}' \
  | python3 -m json.tool
echo ""

echo "✅  Demo complete."
