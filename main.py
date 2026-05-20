"""
GreenPack EPR Compliance Service
A FastAPI backend for EPR (Extended Producer Responsibility) compliance
for plastic packaging producers in India.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from routers import submit, summary, ask

app = FastAPI(
    title="GreenPack EPR Compliance Service",
    description="Backend service for EPR plastic declaration, reconciliation, and compliance Q&A",
    version="1.0.0",
)

app.include_router(submit.router)
app.include_router(summary.router)
app.include_router(ask.router)


@app.get("/")
def root():
    return {
        "service": "GreenPack EPR Compliance Service",
        "version": "1.0.0",
        "endpoints": [
            "POST /submit",
            "GET /summary/{producer_id}/{month}",
            "POST /ask",
        ],
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
